/**
 * RefreshManager.js
 * Handles the automatic refreshing of briefing data
 */

class RefreshManager {
  constructor(options = {}) {
    // Refresh interval in milliseconds (default: 60 seconds)
    this.refreshInterval = options.refreshInterval || 60000;
    
    // Callback functions
    this.onRefreshStart = options.onRefreshStart || function() {};
    this.onRefreshComplete = options.onRefreshComplete || function() {};
    
    // Internal state
    this.refreshTimer = null;
    this.isRefreshing = false;
    this.lastRefreshTime = null;
    this.refreshCount = 0;
    this.consecutiveFailures = 0;
    this.maxConsecutiveFailures = 3;
    
    // Auto refresh enabled by default, can be disabled by user
    this.autoRefreshEnabled = true;
    
    // Initialize
    this.init();
  }
  
  /**
   * Initialize the refresh manager
   */
  init() {
    // Try to load user preference from localStorage
    try {
      const savedPref = localStorage.getItem('briefingAutoRefresh');
      if (savedPref !== null) {
        this.autoRefreshEnabled = savedPref === 'true';
      }
    } catch (error) {
      console.error('Error loading auto-refresh preference:', error);
    }
    
    // Listen for visibility changes to pause/resume refreshing when tab is inactive
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    
    // Update UI to reflect current state
    this.updateAutoRefreshUI();
  }
  
  /**
   * Update UI elements based on auto-refresh state
   */
  updateAutoRefreshUI() {
    const autoRefreshToggle = document.getElementById('autoRefreshToggle');
    if (autoRefreshToggle) {
      autoRefreshToggle.checked = this.autoRefreshEnabled;
    }
    
    const autoRefreshStatus = document.getElementById('autoRefreshStatus');
    if (autoRefreshStatus) {
      autoRefreshStatus.textContent = this.autoRefreshEnabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled';
    }
  }
  
  /**
   * Start the auto-refresh timer
   */
  startAutoRefresh() {
    // Clear any existing timer
    this.stopAutoRefresh();
    
    // Only start if auto-refresh is enabled
    if (!this.autoRefreshEnabled) return;
    
    // Start the refresh timer
    this.refreshTimer = setInterval(() => {
      this.refresh();
    }, this.refreshInterval);
    
    // Update last refresh time if not set
    if (!this.lastRefreshTime) {
      this.lastRefreshTime = new Date();
    }
    
    console.log(`Auto-refresh started with interval of ${this.refreshInterval / 1000} seconds`);
  }
  
  /**
   * Stop the auto-refresh timer
   */
  stopAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
  
  /**
   * Toggle auto-refresh on/off
   * @returns {boolean} The new auto-refresh state
   */
  toggleAutoRefresh() {
    this.autoRefreshEnabled = !this.autoRefreshEnabled;
    
    // Update UI
    this.updateAutoRefreshUI();
    
    // Start or stop the timer
    if (this.autoRefreshEnabled) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
    
    // Save preference
    try {
      localStorage.setItem('briefingAutoRefresh', this.autoRefreshEnabled.toString());
    } catch (error) {
      console.error('Error saving auto-refresh preference:', error);
    }
    
    return this.autoRefreshEnabled;
  }
  
  /**
   * Handle page visibility changes
   * Pause refreshing when page is hidden, resume when visible
   * @param {Event} event - The visibility change event
   */
  handleVisibilityChange(event) {
    if (document.hidden) {
      // Page is hidden, pause the refresh timer
      this.stopAutoRefresh();
      console.log('Auto-refresh paused (page hidden)');
    } else {
      // Page is visible again, resume refresh timer if enabled
      if (this.autoRefreshEnabled) {
        this.startAutoRefresh();
        console.log('Auto-refresh resumed (page visible)');
      }
    }
  }
  
  /**
   * Perform a refresh operation
   * @returns {Promise<boolean>} Whether the refresh was successful
   */
  async refresh() {
    // Prevent concurrent refreshes
    if (this.isRefreshing) {
      console.log('Refresh already in progress, skipping');
      return false;
    }
    
    try {
      this.isRefreshing = true;
      this.onRefreshStart();
      
      // Fetch the latest briefing data
      const response = await fetch('/api/briefing/current');
      
      if (!response.ok) {
        throw new Error(`Refresh failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status !== 'success') {
        throw new Error('Refresh failed: API returned error status');
      }
      
      // Success!
      this.lastRefreshTime = new Date();
      this.refreshCount++;
      this.consecutiveFailures = 0;
      
      // Call the completion callback with the new data
      this.onRefreshComplete(true, data.data);
      
      console.log(`Refresh #${this.refreshCount} completed successfully`);
      return true;
    } catch (error) {
      this.consecutiveFailures++;
      console.error('Error during refresh:', error);
      
      // Call the completion callback with failure
      this.onRefreshComplete(false);
      
      // If too many consecutive failures, disable auto-refresh
      if (this.consecutiveFailures >= this.maxConsecutiveFailures) {
        console.warn(`Auto-refresh disabled after ${this.maxConsecutiveFailures} consecutive failures`);
        this.autoRefreshEnabled = false;
        this.updateAutoRefreshUI();
        this.stopAutoRefresh();
        
        // Show a notification to the user
        this.showRefreshFailureNotification();
      }
      
      return false;
    } finally {
      this.isRefreshing = false;
    }
  }
  
  /**
   * Set a new refresh interval
   * @param {number} intervalMs - The new interval in milliseconds
   */
  setRefreshInterval(intervalMs) {
    if (intervalMs < 10000) {
      console.warn('Refresh interval too short, minimum is 10 seconds');
      intervalMs = 10000;
    }
    
    this.refreshInterval = intervalMs;
    
    // Restart the timer if it was running
    if (this.refreshTimer) {
      this.startAutoRefresh();
    }
    
    console.log(`Refresh interval set to ${intervalMs / 1000} seconds`);
  }
  
  /**
   * Get the time remaining until the next refresh
   * @returns {number} Milliseconds until next refresh, or 0 if not active
   */
  getTimeUntilNextRefresh() {
    if (!this.autoRefreshEnabled || !this.refreshTimer || !this.lastRefreshTime) {
      return 0;
    }
    
    const now = new Date();
    const elapsed = now - this.lastRefreshTime;
    const remaining = Math.max(0, this.refreshInterval - elapsed);
    return remaining;
  }
  
  /**
   * Format the time until next refresh as a human-readable string
   * @returns {string} Time remaining string (e.g., "45s")
   */
  formatNextRefreshTime() {
    const ms = this.getTimeUntilNextRefresh();
    if (ms === 0) return 'N/A';
    
    const seconds = Math.ceil(ms / 1000);
    return `${seconds}s`;
  }
  
  /**
   * Display a notification about refresh failures
   */
  showRefreshFailureNotification() {
    // Check if the browser supports notifications
    if ('Notification' in window) {
      // Check if permission is already granted
      if (Notification.permission === 'granted') {
        new Notification('Auto-refresh Disabled', {
          body: 'Auto-refresh has been disabled due to consecutive connection failures.'
        });
      }
      // Otherwise, request permission
      else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            new Notification('Auto-refresh Disabled', {
              body: 'Auto-refresh has been disabled due to consecutive connection failures.'
            });
          }
        });
      }
    }
    
    // Also add an in-page notification if there's a notification container
    const notificationContainer = document.getElementById('notificationContainer');
    if (notificationContainer) {
      const notification = document.createElement('div');
      notification.classList.add('notification', 'error');
      notification.innerHTML = `
        <div class="notification-header">
          <span class="notification-title">Auto-refresh Disabled</span>
          <button class="notification-close">×</button>
        </div>
        <div class="notification-body">
          Auto-refresh has been disabled due to consecutive connection failures.
        </div>
      `;
      
      // Add close button functionality
      notification.querySelector('.notification-close').addEventListener('click', () => {
        notification.remove();
      });
      
      // Auto-remove after 10 seconds
      setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 500);
      }, 10000);
      
      notificationContainer.appendChild(notification);
    }
  }
}