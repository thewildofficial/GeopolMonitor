import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class BriefingConfiguration:
    """Configuration for briefing generation."""
    def __init__(self,
                max_flash_items: int = 10,           # Maximum number of flash items to include
                flash_sentiment_threshold: float = 0.65, # Threshold for flash sentiment
                refresh_interval_seconds: int = 3600, # How often to refresh briefing
                summary_item_limit: int = 25,        # Max items in summary section
                context_item_limit: int = 50,        # Max items in context section
                hotspot_threshold: int = 10,         # Number of articles to qualify as hotspot
                summarization_temperature: float = 0.7,  # Temperature for AI summarization
                summary_max_tokens: int = 500):        # Max tokens for summaries
        self.max_flash_items = max_flash_items
        self.flash_sentiment_threshold = flash_sentiment_threshold
        self.refresh_interval_seconds = refresh_interval_seconds
        self.summary_item_limit = summary_item_limit
        self.context_item_limit = context_item_limit
        self.hotspot_threshold = hotspot_threshold
        self.summarization_temperature = summarization_temperature
        self.summary_max_tokens = summary_max_tokens

class BriefingGenerator:
    """Core class for generating daily briefings based on news articles."""
    
    def __init__(self, config: Optional[BriefingConfiguration] = None):
        """Initialize the briefing generator with configuration."""
        self.config = config or BriefingConfiguration()
        self.last_briefing = None
        self.last_generation_time = None
        self.last_refresh_time = None
        
    async def generate_daily_briefing(self, 
                                    start_time: Optional[datetime] = None, 
                                    end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate a complete daily briefing based on available news.
        
        Args:
            start_time: Optional start time for the briefing window
            end_time: Optional end time for the briefing window
            
        Returns:
            Dict containing the complete briefing with all tiers
        """
        generation_start = time.time()
        
        # Set default time range if not provided (last 24 hours)
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(hours=self.config.default_timespan_hours)
            
        logger.info(f"Generating daily briefing for {start_time.isoformat()} to {end_time.isoformat()}")
            
        try:
            # Collect news articles within the specified time range
            news_collection = await self._fetch_news_articles(start_time, end_time)
            if not news_collection:
                logger.warning("No news articles found in the specified time range")
                return self._create_empty_briefing(start_time, end_time)
                
            # Classify news by priority
            news_by_tier = self._classify_news_by_priority(news_collection)
            
            # Identify regional hotspots
            regional_hotspots = self.identify_regional_hotspots(news_collection)
            
            # Generate summaries for each tier
            flash_tier = await self._generate_flash_tier(news_by_tier.get('flash', []))
            summary_tier = await self._generate_summary_tier(news_by_tier.get('summary', []), regional_hotspots)
            context_tier = await self._generate_context_tier(news_by_tier.get('context', []))
            
            # Create executive summary
            executive_summary = await self.create_executive_summary(
                flash_tier.get('items', []), 
                regional_hotspots,
                start_time,
                end_time
            )
            
            # Calculate changes from previous briefing
            changes = None
            if self.last_briefing:
                changes = self.detect_significant_shifts(self.last_briefing, {
                    'flash': flash_tier,
                    'summary': summary_tier,
                    'context': context_tier,
                    'regional_hotspots': regional_hotspots
                })
                
            # Assemble full briefing
            briefing = {
                'metadata': {
                    'generated_at': datetime.now(timezone.utc),
                    'start_time': start_time,
                    'end_time': end_time,
                    'total_articles': len(news_collection),
                    'regional_hotspots': [r['name'] for r in regional_hotspots[:5]]
                },
                'executive_summary': executive_summary,
                'flash': flash_tier,
                'summary': summary_tier,
                'context': context_tier,
                'changes': changes
            }
            
            # Store as last briefing
            self.last_briefing = briefing
            self.last_generation_time = datetime.now(timezone.utc)
            
            # Track generation time
            generation_time = time.time() - generation_start
            logger.info(f"Daily briefing generated in {generation_time:.2f}s with {len(news_collection)} articles")
            
            return briefing, generation_time, len(flash_tier.get('items', [])), regional_hotspots[:5]
            
        except Exception as e:
            logger.error(f"Error generating daily briefing: {str(e)}", exc_info=True)
            return self._create_empty_briefing(start_time, end_time), 0, 0, []
    
    async def refresh_briefing(self, current_briefing: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh an existing briefing with new data.
        
        This is more efficient than regenerating a complete briefing when only
        incremental updates are needed.
        
        Args:
            current_briefing: The current briefing to refresh
            
        Returns:
            Dict containing the updated briefing
        """
        refresh_start = time.time()
        flash_alerts_added = 0
        
        try:
            # Extract time range from current briefing
            metadata = current_briefing.get('metadata', {})
            start_time = metadata.get('start_time')
            end_time = datetime.now(timezone.utc)  # Always use current time as end
            
            # Fetch only new articles since last update
            last_update = metadata.get('generated_at') or self.last_refresh_time
            if not last_update:
                # If no last update, just regenerate the whole briefing
                return await self.generate_daily_briefing(start_time, end_time)
                
            # Get new articles since last update
            new_articles = await self._fetch_news_articles(last_update, end_time)
            if not new_articles:
                # No new articles, just update the timestamp
                current_briefing['metadata']['refreshed_at'] = datetime.now(timezone.utc)
                self.last_refresh_time = datetime.now(timezone.utc)
                return current_briefing, 0, 0, []
                
            # Classify new articles
            new_by_tier = self._classify_news_by_priority(new_articles)
            
            # Update flash tier (highest priority)
            if new_by_tier.get('flash'):
                flash_tier = current_briefing.get('flash', {})
                flash_items = flash_tier.get('items', [])
                
                # Add new flash items
                for item in new_by_tier.get('flash', []):
                    # Check if this is truly a new item (avoid duplicates)
                    if not any(i.get('link') == item.get('link') for i in flash_items):
                        flash_items.insert(0, item)  # Add at the beginning
                        flash_alerts_added += 1
                        
                # Trim to max size
                if len(flash_items) > self.config.max_flash_items:
                    flash_items = flash_items[:self.config.max_flash_items]
                    
                flash_tier['items'] = flash_items
                current_briefing['flash'] = flash_tier
            
            # Update summary and context tiers
            # (For refresh, we prioritize speed and focus mainly on flash updates)
            # A full regeneration would be needed periodically for complete updates
            
            # Update regional hotspots if we have enough new articles
            current_hotspots = metadata.get('regional_hotspots', [])
            if len(new_articles) >= 10:  # Only recalculate if significant new data
                # Get all articles within the window (would need to fetch from DB)
                all_articles = await self._fetch_news_articles(start_time, end_time)
                new_hotspots = self.identify_regional_hotspots(all_articles)
                current_briefing['metadata']['regional_hotspots'] = [r['name'] for r in new_hotspots[:5]]
            
            # Update metadata
            current_briefing['metadata']['refreshed_at'] = datetime.now(timezone.utc)
            current_briefing['metadata']['total_articles'] += len(new_articles)
            current_briefing['metadata']['end_time'] = end_time
            
            self.last_refresh_time = datetime.now(timezone.utc)
            
            # Track refresh time
            refresh_time = time.time() - refresh_start
            logger.info(f"Briefing refreshed in {refresh_time:.2f}s with {len(new_articles)} new articles")
            
            return current_briefing, refresh_time, flash_alerts_added, current_briefing['metadata']['regional_hotspots']
            
        except Exception as e:
            logger.error(f"Error refreshing briefing: {str(e)}", exc_info=True)
            return current_briefing, 0, 0, []
    
    def _create_empty_briefing(self, start_time, end_time) -> Dict[str, Any]:
        """Create an empty briefing when no articles are found."""
        return {
            'metadata': {
                'generated_at': datetime.now(timezone.utc),
                'start_time': start_time,
                'end_time': end_time,
                'total_articles': 0,
                'regional_hotspots': []
            },
            'executive_summary': {
                'text': 'No news articles available for the specified time period.',
                'key_points': []
            },
            'flash': {'items': []},
            'summary': {'items': [], 'regions': []},
            'context': {'items': [], 'categories': []}
        }
        
    async def _fetch_news_articles(self, start_time, end_time) -> List[Dict[str, Any]]:
        """Fetch news articles from the database within the given time range.
        
        In a real implementation, this would query the database. For now,
        we'll implement a placeholder that would need to be connected to
        your actual data source.
        """
        # Implementation would depend on your database model
        # Placeholder for now, would connect to your actual news repository
        from ...database.models import get_news_in_timespan
        
        try:
            return get_news_in_timespan(start_time, end_time)
        except Exception as e:
            logger.error(f"Error fetching news articles: {str(e)}")
            # If the import fails (module doesn't exist yet), return empty list
            return []
    
    def _classify_news_by_priority(self, news_collection: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify news items into tiers based on priority, sentiment, and other factors."""
        classified_news = {
            'flash': [],    # Highest priority, critical updates
            'summary': [],  # Medium priority, important developments
            'context': []   # Lower priority, background information
        }
        
        for article in news_collection:
            tier = self.classify_news_priority(article)
            classified_news[tier].append(article)
            
        # Apply limits for each tier
        classified_news['flash'] = classified_news['flash'][:self.config.max_flash_items]
        classified_news['summary'] = classified_news['summary'][:self.config.summary_item_limit]
        classified_news['context'] = classified_news['context'][:self.config.context_item_limit]
            
        return classified_news
    
    def classify_news_priority(self, news_item: Dict[str, Any], sentiment_threshold: float = None) -> str:
        """Determine the priority tier for a news item.
        
        Args:
            news_item: The news item to classify
            sentiment_threshold: Optional override for sentiment threshold
            
        Returns:
            str: 'flash', 'summary', or 'context'
        """
        # Use provided threshold or config default
        sentiment_threshold = sentiment_threshold or self.config.flash_sentiment_threshold
        
        # Extract features used for classification
        sentiment_score = abs(news_item.get('sentiment_score', 0.0))
        tags = news_item.get('tags', [])
        
        # Check for critical keywords in tags
        critical_tags = {'conflict', 'war', 'crisis', 'emergency', 'attack', 'disaster', 'breaking'}
        has_critical_tags = any(tag.get('name', '').lower() in critical_tags for tag in tags)
        
        # Check for specific regions of interest
        priority_regions = {'ukraine', 'russia', 'israel', 'gaza', 'china', 'taiwan'}
        has_priority_region = any(
            tag.get('name', '').lower() in priority_regions 
            for tag in tags if tag.get('category') == 'geography'
        )
        
        # Determine priority based on multiple factors
        # FLASH: Critical events with high sentiment scores or critical tags
        if (sentiment_score >= sentiment_threshold or has_critical_tags) and has_priority_region:
            return 'flash'
            
        # SUMMARY: Important events but not critical
        elif has_priority_region or sentiment_score >= (sentiment_threshold * 0.7):
            return 'summary'
            
        # CONTEXT: Everything else
        else:
            return 'context'
    
    def identify_regional_hotspots(self, 
                                news_collection: List[Dict[str, Any]], 
                                activity_threshold: int = None) -> List[Dict[str, Any]]:
        """Identify regions with high news activity.
        
        Args:
            news_collection: Collection of news items to analyze
            activity_threshold: Minimum articles to consider a region a hotspot
            
        Returns:
            List of dictionaries with region info and activity metrics
        """
        threshold = activity_threshold or self.config.hotspot_threshold
        
        # Count articles by region
        region_counts = {}
        region_sentiment = {}
        region_articles = {}
        
        for article in news_collection:
            for tag in article.get('tags', []):
                if tag.get('category') == 'geography':
                    region_name = tag.get('name', '').lower()
                    if region_name:
                        region_counts[region_name] = region_counts.get(region_name, 0) + 1
                        
                        # Track sentiment
                        sentiment = article.get('sentiment_score', 0)
                        if region_name not in region_sentiment:
                            region_sentiment[region_name] = []
                        region_sentiment[region_name].append(sentiment)
                        
                        # Track articles
                        if region_name not in region_articles:
                            region_articles[region_name] = []
                        region_articles[region_name].append(article)
        
        # Calculate average sentiment and create hotspot list
        hotspots = []
        for region, count in region_counts.items():
            if count >= threshold:
                avg_sentiment = sum(region_sentiment.get(region, [0])) / len(region_sentiment.get(region, [1]))
                
                hotspots.append({
                    'name': region,
                    'count': count,
                    'avg_sentiment': avg_sentiment,
                    'top_articles': region_articles.get(region, [])[:3]  # Include top 3 articles
                })
        
        # Sort by count (most active first)
        return sorted(hotspots, key=lambda x: x['count'], reverse=True)
    
    async def create_executive_summary(self, 
                                    flash_items: List[Dict[str, Any]], 
                                    regions_affected: List[Dict[str, Any]],
                                    start_time: datetime,
                                    end_time: datetime) -> Dict[str, Any]:
        """Generate an executive summary of the most important developments.
        
        Args:
            flash_items: List of flash news items
            regions_affected: List of affected regions
            start_time: Start time of briefing window
            end_time: End time of briefing window
            
        Returns:
            Dictionary with summary text and key points
        """
        # Extract key information
        top_stories = flash_items[:3]  # Top 3 flash stories
        top_regions = regions_affected[:3]  # Top 3 regions
        
        # Format time range for the summary
        time_range = f"{start_time.strftime('%b %d, %Y')} to {end_time.strftime('%b %d, %Y')}"
        if start_time.date() == end_time.date():
            time_range = f"{end_time.strftime('%b %d, %Y')}"
            
        # Generate summary text
        regions_text = ", ".join([r['name'].title() for r in top_regions]) if top_regions else "No significant regional activity"
        
        summary_text = f"Daily Briefing for {time_range}. "
        if flash_items:
            summary_text += f"Critical developments in {regions_text}. "
        else:
            summary_text += "No critical developments reported. "
            
        if top_regions:
            top_region = top_regions[0]['name'].title()
            top_count = top_regions[0]['count']
            summary_text += f"{top_region} shows the highest activity with {top_count} related articles. "
        
        # Extract key points from flash items
        key_points = []
        for item in top_stories:
            key_points.append({
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'source': item.get('source', {}).get('name', 'Unknown'),
                'timestamp': item.get('timestamp', '')
            })
            
        return {
            'text': summary_text.strip(),
            'key_points': key_points,
            'regions_highlighted': [r['name'] for r in top_regions]
        }
    
    async def _generate_flash_tier(self, flash_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate the FLASH tier content with critical updates."""
        return {
            'count': len(flash_items),
            'items': flash_items
        }
    
    async def _generate_summary_tier(self, 
                                    summary_items: List[Dict[str, Any]], 
                                    regional_hotspots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate the SUMMARY tier with important developments organized by region."""
        # Group items by region
        items_by_region = {}
        
        for item in summary_items:
            # Extract the primary region from tags
            primary_region = None
            for tag in item.get('tags', []):
                if tag.get('category') == 'geography':
                    primary_region = tag.get('name', '').lower()
                    break
                    
            if primary_region:
                if primary_region not in items_by_region:
                    items_by_region[primary_region] = []
                items_by_region[primary_region].append(item)
        
        # Create region sections
        regions = []
        for hotspot in regional_hotspots:
            region_name = hotspot['name']
            if region_name in items_by_region:
                regions.append({
                    'name': region_name,
                    'count': len(items_by_region[region_name]),
                    'avg_sentiment': hotspot.get('avg_sentiment', 0),
                    'items': items_by_region[region_name][:5]  # Top 5 items per region
                })
        
        # Add remaining regions not in hotspots
        for region, items in items_by_region.items():
            if not any(r['name'] == region for r in regions):
                regions.append({
                    'name': region,
                    'count': len(items),
                    'avg_sentiment': 0,
                    'items': items[:3]  # Top 3 for non-hotspot regions
                })
        
        # Sort regions by count
        regions.sort(key=lambda r: r['count'], reverse=True)
        
        return {
            'count': len(summary_items),
            'items': summary_items,
            'regions': regions
        }
    
    async def _generate_context_tier(self, context_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate the CONTEXT tier with background and supporting information."""
        # Group by category
        items_by_category = {}
        
        for item in context_items:
            # Find primary category
            primary_category = 'general'  # Default
            for tag in item.get('tags', []):
                if tag.get('category') not in ('geography', 'source'):
                    primary_category = tag.get('name', '').lower()
                    break
                    
            if primary_category not in items_by_category:
                items_by_category[primary_category] = []
            items_by_category[primary_category].append(item)
        
        # Create category sections
        categories = []
        for category_name, items in items_by_category.items():
            categories.append({
                'name': category_name,
                'count': len(items),
                'items': items[:7]  # Top 7 items per category
            })
            
        # Sort categories by count
        categories.sort(key=lambda c: c['count'], reverse=True)
        
        return {
            'count': len(context_items),
            'items': context_items,
            'categories': categories
        }
    
    def detect_significant_shifts(self, previous_briefing: Dict[str, Any], current_briefing: Dict[str, Any]) -> Dict[str, Any]:
        """Detect significant changes between two briefings.
        
        Analyzes changes in regional hotspots, sentiment trends, and coverage
        to highlight important shifts between briefing periods.
        
        Args:
            previous_briefing: Earlier briefing data
            current_briefing: Current briefing data
            
        Returns:
            Dict with analysis of changes
        """
        changes = {
            'new_regions': [],
            'increasing_coverage': [],
            'decreasing_coverage': [],
            'sentiment_shifts': []
        }
        
        # Compare regional hotspots
        prev_regions = set([r['name'] for r in previous_briefing.get('regional_hotspots', [])])
        curr_regions = set([r['name'] for r in current_briefing.get('regional_hotspots', [])])
        
        # Identify new regions in the spotlight
        changes['new_regions'] = list(curr_regions - prev_regions)
        
        # For each common region, compare activity and sentiment
        common_regions = prev_regions.intersection(curr_regions)
        for region in common_regions:
            prev_region_data = next((r for r in previous_briefing.get('regional_hotspots', []) 
                                  if r['name'] == region), None)
            curr_region_data = next((r for r in current_briefing.get('regional_hotspots', []) 
                                  if r['name'] == region), None)
            
            if prev_region_data and curr_region_data:
                # Check for significant change in coverage
                prev_count = prev_region_data['count']
                curr_count = curr_region_data['count'] 
                change_pct = ((curr_count - prev_count) / prev_count * 100) if prev_count else 100
                
                if change_pct >= 30:
                    changes['increasing_coverage'].append({
                        'region': region,
                        'change': f"+{change_pct:.1f}%",
                        'previous': prev_count,
                        'current': curr_count
                    })
                elif change_pct <= -30:
                    changes['decreasing_coverage'].append({
                        'region': region,
                        'change': f"{change_pct:.1f}%",
                        'previous': prev_count,
                        'current': curr_count
                    })
                
                # Check for significant sentiment shifts
                prev_sentiment = prev_region_data.get('avg_sentiment', 0)
                curr_sentiment = curr_region_data.get('avg_sentiment', 0)
                sentiment_shift = curr_sentiment - prev_sentiment
                
                if abs(sentiment_shift) >= 0.3:  # Significant sentiment change
                    changes['sentiment_shifts'].append({
                        'region': region,
                        'shift': sentiment_shift,
                        'direction': 'positive' if sentiment_shift > 0 else 'negative',
                        'previous': prev_sentiment,
                        'current': curr_sentiment
                    })
        
        return changes
    
    def calculate_change_metrics(self, previous_period: List[Dict[str, Any]], current_period: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate comparative metrics between two time periods.
        
        Args:
            previous_period: News articles from the previous period
            current_period: News articles from the current period
            
        Returns:
            Dict with change metrics and percentages
        """
        if not previous_period:
            return {
                'volume_change': 100.0,  # 100% increase from 0
                'sentiment_change': 0.0,
                'has_sufficient_data': False
            }
        
        # Calculate volume change
        volume_change = ((len(current_period) - len(previous_period)) / len(previous_period)) * 100
        
        # Calculate average sentiment for both periods
        prev_sentiment = sum(a.get('sentiment_score', 0) for a in previous_period) / len(previous_period)
        curr_sentiment = sum(a.get('sentiment_score', 0) for a in current_period) / len(current_period)
        sentiment_change = curr_sentiment - prev_sentiment
        
        # Calculate region coverage changes
        prev_regions = {}
        curr_regions = {}
        
        for article in previous_period:
            for tag in article.get('tags', []):
                if tag.get('category') == 'geography':
                    region = tag.get('name', '').lower()
                    prev_regions[region] = prev_regions.get(region, 0) + 1
                    
        for article in current_period:
            for tag in article.get('tags', []):
                if tag.get('category') == 'geography':
                    region = tag.get('name', '').lower()
                    curr_regions[region] = curr_regions.get(region, 0) + 1
        
        # Find regions with the largest change
        region_changes = []
        for region in set(list(prev_regions.keys()) + list(curr_regions.keys())):
            prev_count = prev_regions.get(region, 0)
            curr_count = curr_regions.get(region, 0)
            
            if prev_count > 0:
                change_pct = ((curr_count - prev_count) / prev_count) * 100
                region_changes.append((region, change_pct))
        
        # Sort by absolute change percentage
        region_changes.sort(key=lambda x: abs(x[1]), reverse=True)
        
        top_changing_regions = []
        for region, change in region_changes[:3]:  # Top 3 changes
            top_changing_regions.append({
                'region': region,
                'change_pct': change,
                'previous': prev_regions.get(region, 0),
                'current': curr_regions.get(region, 0)
            })
        
        return {
            'volume_change': volume_change,
            'sentiment_change': sentiment_change,
            'top_changing_regions': top_changing_regions,
            'has_sufficient_data': True
        }