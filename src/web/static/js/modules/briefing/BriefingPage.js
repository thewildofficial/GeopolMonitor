/**
 * BriefingPage.js
 * Main controller for the Daily Briefing page functionality
 */

class BriefingPage {
  constructor() {
    // State
    this.briefingData = null;
    this.currentView = 'list'; // 'list' or 'tiles'
    this.isLoading = true;
    
    // References to other modules
    this.tierManager = null;
    this.refreshManager = null;
    this.briefingSocket = null;
    this.analyticsPanel = null;
    this.miniMap = null;
    
    // DOM Elements
    this.elements = {
      container: document.getElementById('briefingContainer'),
      executiveSummary: document.getElementById('executiveSummary'),
      keyPoints: document.getElementById('keyPoints'),
      flashItems: document.getElementById('flashItems'),
      summaryItems: document.getElementById('summaryItems'),
      contextItems: document.getElementById('contextItems'),
      flashCount: document.getElementById('flashCount'),
      summaryCount: document.getElementById('summaryCount'),
      contextCount: document.getElementById('contextCount'),
      timeWindow: document.getElementById('timeWindow'),
      lastUpdatedText: document.getElementById('lastUpdatedText'),
      manualRefreshButton: document.getElementById('manualRefreshButton'),
      tilesViewButton: document.getElementById('tilesViewButton'),
      listViewButton: document.getElementById('listViewButton'),
      regionTabs: document.getElementById('regionTabs'),
      categoryTabs: document.getElementById('categoryTabs')
    };
    
    // Templates
    this.templates = {
      newsItem: document.getElementById('newsItemTemplate'),
      flashItem: document.getElementById('flashItemTemplate'),
      regionTab: document.getElementById('regionTabTemplate'),
      categoryTab: document.getElementById('categoryTabTemplate'),
      keyPoint: document.getElementById('keyPointTemplate'),
      hotspotItem: document.getElementById('hotspotItemTemplate')
    };
    
    // Initialize the page
    this.init();
  }
  
  /**
   * Initialize the briefing page
   */
  init() {
    this.setupEventListeners();
    this.initModules();
    this.fetchBriefingData();
  }
  
  /**
   * Initialize related modules
   */
  initModules() {
    // Initialize the WebSocket connection for real-time updates
    this.briefingSocket = new BriefingSocket(this.handleSocketUpdate.bind(this));
    
    // Initialize the TierManager for handling tier interactions
    this.tierManager = new TierManager({
      flashContainer: document.getElementById('flashTierContainer'),
      summaryContainer: document.getElementById('summaryTierContainer'),
      contextContainer: document.getElementById('contextTierContainer')
    });
    
    // Initialize the RefreshManager for handling auto-updates
    this.refreshManager = new RefreshManager({
      refreshInterval: 60000, // 1 minute
      onRefreshStart: this.handleRefreshStart.bind(this),
      onRefreshComplete: this.handleRefreshComplete.bind(this)
    });
    
    // Initialize the AnalyticsPanel for data visualizations
    this.analyticsPanel = new AnalyticsPanel({
      coverageChart: 'coverageChart',
      sentimentChart: 'sentimentChart',
      hotspotList: document.getElementById('hotspotList')
    });
    
    // Initialize the MiniMap for geographical visualization
    this.miniMap = new MiniMap('miniMap', {
      height: 240,
      zoomLevel: 1.5
    });
  }
  
  /**
   * Set up event listeners for user interactions
   */
  setupEventListeners() {
    // View toggle buttons
    this.elements.tilesViewButton.addEventListener('click', () => this.switchView('tiles'));
    this.elements.listViewButton.addEventListener('click', () => this.switchView('list'));
    
    // Manual refresh button
    this.elements.manualRefreshButton.addEventListener('click', () => this.refreshBriefing());
    
    // Collapse/expand tier headers using event delegation
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('tier-toggle') || e.target.closest('.tier-toggle')) {
        const button = e.target.classList.contains('tier-toggle') ? e.target : e.target.closest('.tier-toggle');
        const targetId = button.dataset.target;
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
          this.toggleTierVisibility(targetElement, button);
        }
      }
    });
  }
  
  /**
   * Toggle the visibility of a tier section
   * @param {HTMLElement} targetElement - The element to toggle
   * @param {HTMLElement} button - The button that was clicked
   */
  toggleTierVisibility(targetElement, button) {
    const isCollapsed = targetElement.classList.contains('collapsed');
    
    if (isCollapsed) {
      targetElement.classList.remove('collapsed');
      targetElement.style.maxHeight = targetElement.scrollHeight + 'px';
      button.classList.remove('collapsed');
    } else {
      targetElement.classList.add('collapsed');
      targetElement.style.maxHeight = '0px';
      button.classList.add('collapsed');
    }
  }
  
  /**
   * Switch between list and tiles view
   * @param {string} viewType - The view type ('list' or 'tiles')
   */
  switchView(viewType) {
    if (this.currentView === viewType) return;
    
    this.currentView = viewType;
    
    // Update button states
    this.elements.tilesViewButton.classList.toggle('active', viewType === 'tiles');
    this.elements.listViewButton.classList.toggle('active', viewType === 'list');
    
    // Update view classes
    [this.elements.flashItems, this.elements.summaryItems, this.elements.contextItems].forEach(container => {
      container.classList.remove('list-view', 'tiles-view');
      container.classList.add(`${viewType}-view`);
    });
  }
  
  /**
   * Format a timestamp in a human-readable format
   * @param {string|Date} timestamp - The timestamp to format
   * @returns {string} The formatted timestamp
   */
  formatTimestamp(timestamp) {
    if (!timestamp) return 'unknown';
    
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    return date.toLocaleDateString(undefined, options);
  }
  
  /**
   * Fetch the current briefing data from the API
   */
  async fetchBriefingData() {
    try {
      this.showLoading(true);
      
      const response = await fetch('/api/briefing/current');
      const data = await response.json();
      
      if (data.status === 'success') {
        this.briefingData = data.data;
        this.renderBriefing();
      } else {
        this.showEmptyState('No briefing data available');
      }
    } catch (error) {
      console.error('Error fetching briefing data:', error);
      this.showErrorState('Failed to load briefing data');
    } finally {
      this.showLoading(false);
    }
  }
  
  /**
   * Refresh the briefing data
   */
  async refreshBriefing() {
    // Visual feedback for refresh button
    this.elements.manualRefreshButton.classList.add('spinning');
    await this.fetchBriefingData();
    this.elements.manualRefreshButton.classList.remove('spinning');
  }
  
  /**
   * Render the briefing data on the page
   */
  renderBriefing() {
    if (!this.briefingData) return;
    
    // Update the time window
    this.renderTimeWindow();
    
    // Render last updated timestamp
    this.updateLastUpdatedText();
    
    // Render executive summary
    this.renderExecutiveSummary();
    
    // Render flash tier
    this.renderFlashTier();
    
    // Render summary tier
    this.renderSummaryTier();
    
    // Render context tier
    this.renderContextTier();
    
    // Update analytics panel
    this.updateAnalytics();
    
    // Start auto-refresh
    this.refreshManager.startAutoRefresh();
  }
  
  /**
   * Render the time window indicator
   */
  renderTimeWindow() {
    const metadata = this.briefingData.metadata || {};
    const startTime = metadata.start_time ? new Date(metadata.start_time) : null;
    const endTime = metadata.end_time ? new Date(metadata.end_time) : null;
    
    if (startTime && endTime) {
      const startFormatted = startTime.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      const endFormatted = endTime.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      
      this.elements.timeWindow.textContent = `${startFormatted} - ${endFormatted}`;
    } else {
      this.elements.timeWindow.textContent = 'Last 24 hours';
    }
  }
  
  /**
   * Update the "last updated" text
   */
  updateLastUpdatedText() {
    const metadata = this.briefingData.metadata || {};
    const refreshedAt = metadata.refreshed_at || metadata.generated_at;
    
    if (refreshedAt) {
      const formattedTime = this.formatTimestamp(refreshedAt);
      this.elements.lastUpdatedText.textContent = `Last updated: ${formattedTime}`;
    } else {
      this.elements.lastUpdatedText.textContent = 'Last updated: unknown';
    }
  }
  
  /**
   * Render the executive summary section
   */
  renderExecutiveSummary() {
    const summary = this.briefingData.executive_summary || {};
    
    // Render main summary text
    if (summary.text) {
      this.elements.executiveSummary.textContent = summary.text;
    } else {
      this.elements.executiveSummary.innerHTML = '<em>No executive summary available for the current time period.</em>';
    }
    
    // Render key points
    this.elements.keyPoints.innerHTML = '';
    if (summary.key_points && summary.key_points.length > 0) {
      summary.key_points.forEach(point => {
        const keyPointElement = this.createKeyPointElement(point);
        this.elements.keyPoints.appendChild(keyPointElement);
      });
    }
  }
  
  /**
   * Create a key point element from a template
   * @param {string} pointText - The text for the key point
   * @returns {HTMLElement} The key point element
   */
  createKeyPointElement(pointText) {
    const template = this.templates.keyPoint;
    const keyPoint = template.content.cloneNode(true);
    
    keyPoint.querySelector('.key-point-text').textContent = pointText;
    
    return keyPoint;
  }
  
  /**
   * Render the flash tier section
   */
  renderFlashTier() {
    const flash = this.briefingData.flash || { items: [] };
    const items = flash.items || [];
    
    // Update count
    this.elements.flashCount.textContent = items.length;
    
    // Clear existing content
    this.elements.flashItems.innerHTML = '';
    
    if (items.length === 0) {
      this.showEmptyState('No flash alerts at this time', this.elements.flashItems);
      return;
    }
    
    // Render each flash item
    items.forEach(item => {
      const flashElement = this.createFlashElement(item);
      this.elements.flashItems.appendChild(flashElement);
    });
  }
  
  /**
   * Create a flash item element from a template
   * @param {Object} item - The flash item data
   * @returns {HTMLElement} The flash item element
   */
  createFlashElement(item) {
    const template = this.templates.flashItem;
    const flash = template.content.cloneNode(true);
    
    flash.querySelector('.flash-title').textContent = item.title || 'Untitled Alert';
    flash.querySelector('.flash-description').textContent = item.description || item.content || '';
    
    // Set timestamp
    const timeElement = flash.querySelector('.flash-time');
    if (item.timestamp) {
      timeElement.textContent = this.formatTimestamp(item.timestamp);
    } else {
      timeElement.textContent = '';
    }
    
    // Add priority indicator text
    const priorityElement = flash.querySelector('.priority-indicator');
    priorityElement.textContent = 'FLASH';
    
    // Add tags
    const tagsContainer = flash.querySelector('.flash-tags');
    if (item.tags && item.tags.length > 0) {
      item.tags.forEach(tag => {
        const tagElement = document.createElement('span');
        tagElement.classList.add('tag');
        tagElement.textContent = tag.name;
        if (tag.category) {
          tagElement.dataset.category = tag.category;
        }
        tagsContainer.appendChild(tagElement);
      });
    }
    
    // Add link handling
    const flashItem = flash.querySelector('.flash-item');
    if (item.link) {
      flashItem.addEventListener('click', () => {
        window.open(item.link, '_blank');
      });
    }
    
    return flash;
  }
  
  /**
   * Render the summary tier section
   */
  renderSummaryTier() {
    const summary = this.briefingData.summary || { items: [], regions: [] };
    const items = summary.items || [];
    const regions = summary.regions || [];
    
    // Update count
    this.elements.summaryCount.textContent = items.length;
    
    // Clear existing content
    this.elements.summaryItems.innerHTML = '';
    this.elements.regionTabs.innerHTML = '';
    
    if (items.length === 0) {
      this.showEmptyState('No summary items available', this.elements.summaryItems);
      return;
    }
    
    // Render region tabs
    if (regions.length > 0) {
      // Add "All" tab
      const allTab = document.createElement('button');
      allTab.classList.add('region-tab', 'active');
      allTab.dataset.region = 'all';
      allTab.innerHTML = `<span class="region-name">All</span><span class="region-count">${items.length}</span>`;
      allTab.addEventListener('click', () => this.filterByRegion('all'));
      this.elements.regionTabs.appendChild(allTab);
      
      // Add region-specific tabs
      regions.forEach(region => {
        const regionElement = this.createRegionTabElement(region);
        this.elements.regionTabs.appendChild(regionElement);
      });
    }
    
    // Render all summary items
    items.forEach(item => {
      const newsElement = this.createNewsElement(item);
      this.elements.summaryItems.appendChild(newsElement);
    });
  }
  
  /**
   * Create a region tab element
   * @param {Object} region - The region data
   * @returns {HTMLElement} The region tab element
   */
  createRegionTabElement(region) {
    const template = this.templates.regionTab;
    const regionTab = template.content.cloneNode(true);
    
    const tabElement = regionTab.querySelector('.region-tab');
    tabElement.dataset.region = region.name.toLowerCase();
    
    regionTab.querySelector('.region-name').textContent = region.name;
    regionTab.querySelector('.region-count').textContent = region.count || 0;
    
    // Add event listener
    tabElement.addEventListener('click', (e) => {
      this.filterByRegion(region.name.toLowerCase());
      
      // Set active state
      const tabs = this.elements.regionTabs.querySelectorAll('.region-tab');
      tabs.forEach(tab => tab.classList.remove('active'));
      e.currentTarget.classList.add('active');
    });
    
    return regionTab;
  }
  
  /**
   * Filter summary items by region
   * @param {string} regionName - The region name to filter by (or 'all' for all items)
   */
  filterByRegion(regionName) {
    const items = this.elements.summaryItems.querySelectorAll('.news-item');
    
    if (regionName === 'all') {
      // Show all items
      items.forEach(item => item.style.display = '');
    } else {
      // Filter items
      items.forEach(item => {
        const itemRegion = item.dataset.region ? item.dataset.region.toLowerCase() : '';
        item.style.display = (itemRegion === regionName.toLowerCase()) ? '' : 'none';
      });
    }
  }
  
  /**
   * Render the context tier section
   */
  renderContextTier() {
    const context = this.briefingData.context || { items: [], categories: [] };
    const items = context.items || [];
    const categories = context.categories || [];
    
    // Update count
    this.elements.contextCount.textContent = items.length;
    
    // Clear existing content
    this.elements.contextItems.innerHTML = '';
    this.elements.categoryTabs.innerHTML = '';
    
    if (items.length === 0) {
      this.showEmptyState('No context items available', this.elements.contextItems);
      return;
    }
    
    // Render category tabs
    if (categories.length > 0) {
      // Add "All" tab
      const allTab = document.createElement('button');
      allTab.classList.add('category-tab', 'active');
      allTab.dataset.category = 'all';
      allTab.innerHTML = `<span class="category-name">All</span><span class="category-count">${items.length}</span>`;
      allTab.addEventListener('click', () => this.filterByCategory('all'));
      this.elements.categoryTabs.appendChild(allTab);
      
      // Add category-specific tabs
      categories.forEach(category => {
        const categoryElement = this.createCategoryTabElement(category);
        this.elements.categoryTabs.appendChild(categoryElement);
      });
    }
    
    // Render all context items
    items.forEach(item => {
      const newsElement = this.createNewsElement(item);
      this.elements.contextItems.appendChild(newsElement);
    });
  }
  
  /**
   * Create a category tab element
   * @param {Object} category - The category data
   * @returns {HTMLElement} The category tab element
   */
  createCategoryTabElement(category) {
    const template = this.templates.categoryTab;
    const categoryTab = template.content.cloneNode(true);
    
    const tabElement = categoryTab.querySelector('.category-tab');
    tabElement.dataset.category = category.name.toLowerCase();
    
    categoryTab.querySelector('.category-name').textContent = category.name;
    categoryTab.querySelector('.category-count').textContent = category.count || 0;
    
    // Add event listener
    tabElement.addEventListener('click', (e) => {
      this.filterByCategory(category.name.toLowerCase());
      
      // Set active state
      const tabs = this.elements.categoryTabs.querySelectorAll('.category-tab');
      tabs.forEach(tab => tab.classList.remove('active'));
      e.currentTarget.classList.add('active');
    });
    
    return categoryTab;
  }
  
  /**
   * Filter context items by category
   * @param {string} categoryName - The category name to filter by (or 'all' for all items)
   */
  filterByCategory(categoryName) {
    const items = this.elements.contextItems.querySelectorAll('.news-item');
    
    if (categoryName === 'all') {
      // Show all items
      items.forEach(item => item.style.display = '');
    } else {
      // Filter items
      items.forEach(item => {
        const itemCategory = item.dataset.category ? item.dataset.category.toLowerCase() : '';
        item.style.display = (itemCategory === categoryName.toLowerCase()) ? '' : 'none';
      });
    }
  }
  
  /**
   * Create a news item element from a template
   * @param {Object} item - The news item data
   * @returns {HTMLElement} The news item element
   */
  createNewsElement(item) {
    const template = this.templates.newsItem;
    const news = template.content.cloneNode(true);
    
    // Set title and description
    news.querySelector('.news-title').textContent = item.title || 'Untitled';
    news.querySelector('.description').textContent = item.description || item.content || '';
    
    // Set image if available
    const imageElement = news.querySelector('.news-image');
    if (item.image_url) {
      imageElement.src = item.image_url;
      imageElement.alt = item.title || 'News image';
    } else {
      imageElement.src = '/static/assets/placeholder-image.jpg';
      imageElement.alt = 'No image available';
    }
    
    // Set timestamp
    const timeElement = news.querySelector('.time');
    if (item.timestamp) {
      timeElement.textContent = this.formatTimestamp(item.timestamp);
    } else {
      timeElement.textContent = '';
    }
    
    // Add tags
    const tagsContainer = news.querySelector('.tags');
    if (item.tags && item.tags.length > 0) {
      item.tags.forEach(tag => {
        const tagElement = document.createElement('span');
        tagElement.classList.add('tag');
        tagElement.textContent = tag.name;
        if (tag.category) {
          tagElement.dataset.category = tag.category;
          
          // Add region data attribute for filtering
          if (tag.category === 'geography') {
            news.querySelector('.news-item').dataset.region = tag.name.toLowerCase();
          }
          
          // Add category data attribute for filtering
          if (tag.category === 'topic') {
            news.querySelector('.news-item').dataset.category = tag.name.toLowerCase();
          }
        }
        tagsContainer.appendChild(tagElement);
      });
    }
    
    // Add link handling
    const newsItem = news.querySelector('.news-item');
    if (item.link) {
      newsItem.addEventListener('click', () => {
        window.open(item.link, '_blank');
      });
    }
    
    return news;
  }
  
  /**
   * Update the analytics panel with the current data
   */
  updateAnalytics() {
    if (!this.analyticsPanel) return;
    
    const metadata = this.briefingData.metadata || {};
    const flash = this.briefingData.flash || { items: [] };
    const summary = this.briefingData.summary || { items: [] };
    const context = this.briefingData.context || { items: [] };
    
    // Update hotspots
    if (metadata.regional_hotspots && metadata.regional_hotspots.length > 0) {
      this.analyticsPanel.updateHotspots(metadata.regional_hotspots);
    }
    
    // Update coverage chart
    const coverageData = {
      totalArticles: metadata.total_articles || 0,
      flash: flash.items.length,
      summary: summary.items.length,
      context: context.items.length
    };
    this.analyticsPanel.updateCoverageChart(coverageData);
    
    // Update sentiment chart (would need sentiment data from the API)
    // This is a placeholder implementation
    const sentimentData = {
      positive: summary.items.filter(item => (item.sentiment_score || 0) > 0.33).length,
      neutral: summary.items.filter(item => (item.sentiment_score || 0) <= 0.33 && (item.sentiment_score || 0) >= -0.33).length,
      negative: summary.items.filter(item => (item.sentiment_score || 0) < -0.33).length
    };
    this.analyticsPanel.updateSentimentChart(sentimentData);
    
    // Update mini map
    if (this.miniMap && summary.regions) {
      this.miniMap.updateRegions(summary.regions);
    }
  }
  
  /**
   * Handle WebSocket update notifications
   * @param {Object} updateData - The update data from the WebSocket
   */
  handleSocketUpdate(updateData) {
    console.log('Received WebSocket update:', updateData);
    
    if (updateData.type === 'briefing_updated') {
      // Show notification
      this.showNotification('Briefing Updated', 'The briefing has been updated with new information.');
      
      // Refresh data
      this.refreshBriefing();
    } else if (updateData.type === 'new_flash_alert') {
      // Show notification
      this.showNotification('New Flash Alert', updateData.title || 'A new critical update is available.');
      
      // Add the new alert to the flash tier
      if (updateData.alert && this.briefingData && this.briefingData.flash) {
        this.briefingData.flash.items.unshift(updateData.alert);
        const flashElement = this.createFlashElement(updateData.alert);
        flashElement.querySelector('.flash-item').classList.add('new');
        this.elements.flashItems.insertBefore(flashElement, this.elements.flashItems.firstChild);
        this.elements.flashCount.textContent = this.briefingData.flash.items.length;
      }
    }
  }
  
  /**
   * Show a notification to the user
   * @param {string} title - The notification title
   * @param {string} message - The notification message
   */
  showNotification(title, message) {
    // Check if the browser supports notifications
    if ('Notification' in window) {
      // Check if permission is already granted
      if (Notification.permission === 'granted') {
        new Notification(title, { body: message });
      }
      // Otherwise, request permission
      else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            new Notification(title, { body: message });
          }
        });
      }
    }
    
    // Also log to console
    console.log(`${title}: ${message}`);
  }
  
  /**
   * Handle the start of a refresh operation
   */
  handleRefreshStart() {
    this.elements.manualRefreshButton.classList.add('spinning');
  }
  
  /**
   * Handle the completion of a refresh operation
   */
  handleRefreshComplete(success) {
    this.elements.manualRefreshButton.classList.remove('spinning');
    this.updateLastUpdatedText();
  }
  
  /**
   * Show an empty state message
   * @param {string} message - The message to display
   * @param {HTMLElement} container - The container to show the message in (optional)
   */
  showEmptyState(message, container = null) {
    const emptyState = document.createElement('div');
    emptyState.classList.add('empty-state');
    emptyState.innerHTML = `
      <i class="fas fa-inbox"></i>
      <p>${message}</p>
    `;
    
    if (container) {
      container.innerHTML = '';
      container.appendChild(emptyState);
    } else {
      this.elements.flashItems.innerHTML = '';
      this.elements.summaryItems.innerHTML = '';
      this.elements.contextItems.innerHTML = '';
      this.elements.flashItems.appendChild(emptyState.cloneNode(true));
      this.elements.summaryItems.appendChild(emptyState.cloneNode(true));
      this.elements.contextItems.appendChild(emptyState.cloneNode(true));
    }
  }
  
  /**
   * Show an error state message
   * @param {string} message - The error message to display
   */
  showErrorState(message) {
    const errorState = document.createElement('div');
    errorState.classList.add('empty-state', 'error-state');
    errorState.innerHTML = `
      <i class="fas fa-exclamation-triangle"></i>
      <p>${message}</p>
    `;
    
    this.elements.executiveSummary.innerHTML = '';
    this.elements.executiveSummary.appendChild(errorState);
    
    this.showEmptyState('Error loading content');
  }
  
  /**
   * Show or hide the loading state
   * @param {boolean} show - Whether to show the loading state
   */
  showLoading(show) {
    this.isLoading = show;
    
    if (show) {
      [this.elements.flashItems, this.elements.summaryItems, this.elements.contextItems].forEach(container => {
        const loadingState = document.createElement('div');
        loadingState.classList.add('loading-state');
        loadingState.innerHTML = '<div class="loader"></div>';
        
        container.innerHTML = '';
        container.appendChild(loadingState);
      });
    }
  }
}

// Initialize the briefing page when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.briefingPage = new BriefingPage();
});