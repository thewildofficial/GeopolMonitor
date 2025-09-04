/**
 * AnalyticsPanel.js
 * Handles data visualizations and analytics for the briefing page
 */

class AnalyticsPanel {
  constructor(options = {}) {
    // DOM element IDs
    this.chartIds = {
      coverage: options.coverageChart || 'coverageChart',
      sentiment: options.sentimentChart || 'sentimentChart'
    };
    
    // DOM elements
    this.elements = {
      hotspotList: options.hotspotList || null
    };
    
    // Chart instances
    this.charts = {
      coverage: null,
      sentiment: null
    };
    
    // Data state
    this.data = {
      coverage: null,
      sentiment: null,
      hotspots: []
    };
    
    // Initialize the panel
    this.init();
  }
  
  /**
   * Initialize the analytics panel
   */
  init() {
    this.setupCharts();
  }
  
  /**
   * Set up the charts
   */
  setupCharts() {
    // Make sure Chart.js is available
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js is not loaded, analytics visualizations will not be available');
      return;
    }
    
    // Set up coverage chart
    const coverageCtx = document.getElementById(this.chartIds.coverage)?.getContext('2d');
    if (coverageCtx) {
      this.charts.coverage = new Chart(coverageCtx, {
        type: 'doughnut',
        data: {
          labels: ['Flash', 'Summary', 'Context'],
          datasets: [{
            data: [0, 0, 0],
            backgroundColor: ['#FF6B6B', '#48DBB4', '#4D96FF'],
            borderWidth: 0,
            hoverOffset: 5
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 20,
                usePointStyle: true
              }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.raw || 0;
                  const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                  const percentage = Math.round((value / total) * 100);
                  return `${label}: ${value} (${percentage}%)`;
                }
              }
            }
          },
          cutout: '70%'
        }
      });
    }
    
    // Set up sentiment chart
    const sentimentCtx = document.getElementById(this.chartIds.sentiment)?.getContext('2d');
    if (sentimentCtx) {
      this.charts.sentiment = new Chart(sentimentCtx, {
        type: 'bar',
        data: {
          labels: ['Positive', 'Neutral', 'Negative'],
          datasets: [{
            data: [0, 0, 0],
            backgroundColor: ['#48DBB4', '#FFDE7D', '#FF6B6B'],
            borderWidth: 0,
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const value = context.raw || 0;
                  const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                  const percentage = Math.round((value / total) * 100);
                  return `${value} articles (${percentage}%)`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                precision: 0
              }
            }
          }
        }
      });
    }
  }
  
  /**
   * Update the coverage chart with new data
   * @param {Object} data - The coverage data object
   */
  updateCoverageChart(data) {
    this.data.coverage = data;
    
    if (!this.charts.coverage) return;
    
    const { flash, summary, context } = data;
    
    // Update chart data
    this.charts.coverage.data.datasets[0].data = [flash, summary, context];
    this.charts.coverage.update();
    
    // Update center text if the element exists
    const centerTextElement = document.getElementById('coverageCenterText');
    if (centerTextElement) {
      const totalArticles = data.totalArticles || (flash + summary + context);
      centerTextElement.textContent = totalArticles;
    }
  }
  
  /**
   * Update the sentiment chart with new data
   * @param {Object} data - The sentiment data object
   */
  updateSentimentChart(data) {
    this.data.sentiment = data;
    
    if (!this.charts.sentiment) return;
    
    const { positive, neutral, negative } = data;
    
    // Update chart data
    this.charts.sentiment.data.datasets[0].data = [positive, neutral, negative];
    this.charts.sentiment.update();
  }
  
  /**
   * Update the hotspots list with new data
   * @param {Array} hotspots - Array of hotspot objects
   */
  updateHotspots(hotspots) {
    this.data.hotspots = hotspots;
    
    if (!this.elements.hotspotList) return;
    
    // Clear the current list
    this.elements.hotspotList.innerHTML = '';
    
    if (!hotspots || hotspots.length === 0) {
      const emptyState = document.createElement('div');
      emptyState.classList.add('empty-state', 'small');
      emptyState.textContent = 'No regional hotspots detected';
      this.elements.hotspotList.appendChild(emptyState);
      return;
    }
    
    // Sort hotspots by activity level (descending)
    const sortedHotspots = [...hotspots].sort((a, b) => {
      return (b.activity_level || 0) - (a.activity_level || 0);
    });
    
    // Render each hotspot
    sortedHotspots.forEach(hotspot => {
      const hotspotElement = this.createHotspotElement(hotspot);
      this.elements.hotspotList.appendChild(hotspotElement);
    });
  }
  
  /**
   * Create a hotspot element
   * @param {Object} hotspot - The hotspot data
   * @returns {HTMLElement} The hotspot element
   */
  createHotspotElement(hotspot) {
    const element = document.createElement('div');
    element.classList.add('hotspot-item');
    
    // Add attributes for filtering
    if (hotspot.region) {
      element.dataset.region = hotspot.region.toLowerCase();
    }
    
    // Calculate activity level as a percentage for the bar
    const activityLevel = hotspot.activity_level || 0;
    const activityPercentage = Math.min(100, Math.max(5, activityLevel * 10)); // Scale to reasonable percentage
    
    // Set color based on activity level
    let activityColor = '#48DBB4'; // Low (green)
    if (activityLevel > 7) {
      activityColor = '#FF6B6B'; // High (red)
    } else if (activityLevel > 4) {
      activityColor = '#FFDE7D'; // Medium (yellow)
    }
    
    // Create the HTML structure
    element.innerHTML = `
      <div class="hotspot-header">
        <span class="hotspot-name">${hotspot.region || 'Unknown'}</span>
        <span class="hotspot-count">${hotspot.article_count || 0}</span>
      </div>
      <div class="activity-bar-container">
        <div class="activity-bar" style="width: ${activityPercentage}%; background-color: ${activityColor}"></div>
      </div>
      <div class="hotspot-trend">
        ${this.getTrendIcon(hotspot.trend)} 
        <span class="trend-label">${this.formatTrend(hotspot.trend)}</span>
      </div>
    `;
    
    // Add click event to filter by this region
    element.addEventListener('click', () => {
      this.filterByRegion(hotspot.region);
    });
    
    return element;
  }
  
  /**
   * Filter briefing items by region
   * @param {string} region - The region to filter by
   */
  filterByRegion(region) {
    if (!region) return;
    
    // Find the region tab and click it
    const regionTab = document.querySelector(`.region-tab[data-region="${region.toLowerCase()}"]`);
    if (regionTab) {
      regionTab.click();
    }
  }
  
  /**
   * Get a trend icon based on the trend value
   * @param {number} trend - The trend value (-1 = decreasing, 0 = stable, 1 = increasing)
   * @returns {string} HTML for the trend icon
   */
  getTrendIcon(trend) {
    if (!trend && trend !== 0) return '';
    
    if (trend > 0) {
      return '<i class="fas fa-arrow-up trend-up"></i>';
    } else if (trend < 0) {
      return '<i class="fas fa-arrow-down trend-down"></i>';
    } else {
      return '<i class="fas fa-minus trend-stable"></i>';
    }
  }
  
  /**
   * Format a trend value as a string
   * @param {number} trend - The trend value
   * @returns {string} The formatted trend
   */
  formatTrend(trend) {
    if (!trend && trend !== 0) return 'Unknown';
    
    if (trend > 0) {
      return 'Increasing';
    } else if (trend < 0) {
      return 'Decreasing';
    } else {
      return 'Stable';
    }
  }
  
  /**
   * Update all visualizations with new data
   * @param {Object} data - The briefing data
   */
  updateAll(data) {
    const metadata = data.metadata || {};
    
    // Update coverage chart
    const coverageData = {
      totalArticles: metadata.total_articles || 0,
      flash: (data.flash?.items || []).length,
      summary: (data.summary?.items || []).length,
      context: (data.context?.items || []).length
    };
    this.updateCoverageChart(coverageData);
    
    // Update sentiment chart
    // This is a placeholder implementation that classifies based on sentiment score
    // You may need to adjust based on your actual data format
    const sentimentData = {
      positive: (data.summary?.items || []).filter(item => (item.sentiment_score || 0) > 0.33).length,
      neutral: (data.summary?.items || []).filter(item => 
        (item.sentiment_score || 0) <= 0.33 && (item.sentiment_score || 0) >= -0.33
      ).length,
      negative: (data.summary?.items || []).filter(item => (item.sentiment_score || 0) < -0.33).length
    };
    this.updateSentimentChart(sentimentData);
    
    // Update hotspots
    if (metadata.regional_hotspots) {
      this.updateHotspots(metadata.regional_hotspots);
    }
  }
}