/**
 * AutoUpdateService.js
 * Handles automatic updating of briefing data at regular intervals
 */

class AutoUpdateService {
  constructor(options = {}) {
    // Configuration
    this.options = {
      updateIntervalMs: options.updateIntervalMs || 60000, // Default 1 minute
      flashUpdateIntervalMs: options.flashUpdateIntervalMs || 30000, // Default 30 seconds for flash updates
      retryIntervalMs: options.retryIntervalMs || 15000, // Default retry interval if update fails
      maxRetries: options.maxRetries || 3, // Maximum retries before giving up
      apiEndpoint: options.apiEndpoint || '/api/briefing/current',
      flashEndpoint: options.flashEndpoint || '/api/briefing/flash',
      onUpdate: options.onUpdate || null, // Callback when update happens
      onFlashUpdate: options.onFlashUpdate || null, // Callback for flash-only updates
      onError: options.onError || null, // Error callback
      onStatusChange: options.onStatusChange || null // Status change callback
    };
    
    // State
    this.state = {
      isRunning: false,
      lastUpdateTime: null,
      lastFlashUpdateTime: null,
      updateTimer: null,
      flashUpdateTimer: null,
      retryCount: 0,
      lastEtag: null,
      lastModified: null,
      updateInProgress: false,
      flashUpdateInProgress: false,
      connectionLost: false
    };
    
    // Bind methods
    this.checkForUpdates = this.checkForUpdates.bind(this);
    this.checkForFlashUpdates = this.checkForFlashUpdates.bind(this);
    this.handleNetworkStatusChange = this.handleNetworkStatusChange.bind(this);
  }
  
  /**
   * Start the automatic update service
   */
  start() {
    if (this.state.isRunning) return;
    
    // Set state to running
    this.state.isRunning = true;
    this.updateStatusIndicator('idle');
    
    // Clear any existing timers
    this.clearTimers();
    
    // Start main update cycle
    this.initializeUpdateCycle();
    
    // Set up network status monitoring
    window.addEventListener('online', this.handleNetworkStatusChange);
    window.addEventListener('offline', this.handleNetworkStatusChange);
    
    // Log
    console.log('AutoUpdateService: Started with interval', 
      this.options.updateIntervalMs / 1000, 'seconds');
  }
  
  /**
   * Stop the automatic update service
   */
  stop() {
    if (!this.state.isRunning) return;
    
    // Clear timers
    this.clearTimers();
    
    // Update state
    this.state.isRunning = false;
    this.updateStatusIndicator('stopped');
    
    // Remove network listeners
    window.removeEventListener('online', this.handleNetworkStatusChange);
    window.removeEventListener('offline', this.handleNetworkStatusChange);
    
    // Log
    console.log('AutoUpdateService: Stopped');
  }
  
  /**
   * Initialize the update cycle
   */
  initializeUpdateCycle() {
    // Immediate first check
    this.checkForUpdates();
    
    // Start flash update cycle separately
    this.state.flashUpdateTimer = setInterval(
      this.checkForFlashUpdates,
      this.options.flashUpdateIntervalMs
    );
    
    // Schedule regular updates
    this.state.updateTimer = setInterval(
      this.checkForUpdates,
      this.options.updateIntervalMs
    );
  }
  
  /**
   * Clear all active timers
   */
  clearTimers() {
    if (this.state.updateTimer) {
      clearInterval(this.state.updateTimer);
      this.state.updateTimer = null;
    }
    
    if (this.state.flashUpdateTimer) {
      clearInterval(this.state.flashUpdateTimer);
      this.state.flashUpdateTimer = null;
    }
    
    if (this.state.retryTimer) {
      clearTimeout(this.state.retryTimer);
      this.state.retryTimer = null;
    }
  }
  
  /**
   * Check for briefing updates from the server
   */
  async checkForUpdates() {
    // Skip if update is already in progress or service is stopped
    if (this.state.updateInProgress || !this.state.isRunning) return;
    
    try {
      this.state.updateInProgress = true;
      this.updateStatusIndicator('updating');
      
      // Prepare headers for conditional request
      const headers = new Headers();
      if (this.state.lastEtag) {
        headers.append('If-None-Match', this.state.lastEtag);
      }
      if (this.state.lastModified) {
        headers.append('If-Modified-Since', this.state.lastModified);
      }
      
      // Make the request
      const response = await fetch(this.options.apiEndpoint, {
        method: 'GET',
        headers: headers,
        cache: 'no-cache'
      });
      
      // Handle the response
      if (response.status === 304) {
        // No changes, update last check time
        this.state.lastUpdateTime = new Date();
        this.updateStatusIndicator('idle');
        this.state.retryCount = 0;
        this.state.connectionLost = false;
      } else if (response.ok) {
        // Store ETag and Last-Modified for future requests
        const etag = response.headers.get('ETag');
        const lastModified = response.headers.get('Last-Modified');
        
        if (etag) this.state.lastEtag = etag;
        if (lastModified) this.state.lastModified = lastModified;
        
        // Get the updated briefing data
        const newData = await response.json();
        
        // Process the update
        this.handleBriefingUpdate(newData);
        
        // Reset retry counter
        this.state.retryCount = 0;
        this.state.connectionLost = false;
      } else {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      this.handleUpdateError(error);
    } finally {
      this.state.updateInProgress = false;
    }
  }
  
  /**
   * Check specifically for flash updates that need immediate attention
   */
  async checkForFlashUpdates() {
    // Skip if update is already in progress or service is stopped
    if (this.state.flashUpdateInProgress || !this.state.isRunning) return;
    
    try {
      this.state.flashUpdateInProgress = true;
      
      // Make the request
      const response = await fetch(this.options.flashEndpoint, {
        method: 'GET',
        cache: 'no-cache'
      });
      
      // Handle the response
      if (response.ok) {
        const flashData = await response.json();
        
        // Check if there are new flash updates
        if (flashData && flashData.items && flashData.items.length > 0) {
          this.handleFlashUpdate(flashData);
        }
        
        // Update timing
        this.state.lastFlashUpdateTime = new Date();
      }
    } catch (error) {
      console.warn('Flash update check failed:', error);
      // We don't retry for flash updates - they'll be tried again on next cycle
    } finally {
      this.state.flashUpdateInProgress = false;
    }
  }
  
  /**
   * Handle successful briefing update
   * @param {Object} newData - The updated briefing data
   */
  handleBriefingUpdate(newData) {
    // Update timestamp
    this.state.lastUpdateTime = new Date();
    this.updateStatusIndicator('updated');
    
    // Find changed sections by comparing with old data
    const changedSections = this.detectChangedSections(newData);
    
    // Call the update callback if provided
    if (typeof this.options.onUpdate === 'function') {
      this.options.onUpdate(newData, changedSections);
    }
    
    // Update last refresh indicator
    this.updateLastRefreshIndicator(this.state.lastUpdateTime);
    
    // Log
    console.log('AutoUpdateService: Briefing updated at', 
      this.formatTimestamp(this.state.lastUpdateTime));
  }
  
  /**
   * Handle flash updates
   * @param {Object} flashData - The flash update data
   */
  handleFlashUpdate(flashData) {
    // Only process if we have flash items and they're new
    if (!flashData || !flashData.items || !flashData.items.length) {
      return;
    }
    
    // Call the flash update callback if provided
    if (typeof this.options.onFlashUpdate === 'function') {
      this.options.onFlashUpdate(flashData);
    }
    
    // Log
    console.log('AutoUpdateService: Flash update received with', 
      flashData.items.length, 'items');
  }
  
  /**
   * Handle update errors
   * @param {Error} error - The error that occurred
   */
  handleUpdateError(error) {
    // Update status
    this.updateStatusIndicator('error');
    
    // Increment retry counter
    this.state.retryCount++;
    
    // Log error
    console.error('AutoUpdateService: Update failed -', error.message);
    
    // Call error callback if provided
    if (typeof this.options.onError === 'function') {
      this.options.onError(error);
    }
    
    // Check if maximum retries exceeded
    if (this.state.retryCount >= this.options.maxRetries) {
      // After max retries, continue with normal schedule but mark as having connection issues
      this.state.connectionLost = true;
      this.state.retryCount = 0;
      this.updateStatusIndicator('connection-lost');
    } else {
      // Schedule retry with backoff
      const retryDelay = this.options.retryIntervalMs * Math.pow(2, this.state.retryCount - 1);
      console.log(`AutoUpdateService: Will retry in ${retryDelay/1000} seconds (attempt ${this.state.retryCount})`);
      
      this.state.retryTimer = setTimeout(() => {
        this.checkForUpdates();
      }, retryDelay);
    }
  }
  
  /**
   * Handle network status changes
   */
  handleNetworkStatusChange() {
    if (navigator.onLine) {
      // Back online, try to update immediately
      if (this.state.connectionLost) {
        console.log('AutoUpdateService: Network connection restored, updating...');
        this.state.connectionLost = false;
        this.checkForUpdates();
      }
    } else {
      // Offline
      console.log('AutoUpdateService: Network connection lost');
      this.state.connectionLost = true;
      this.updateStatusIndicator('offline');
    }
  }
  
  /**
   * Detect which sections have changed compared to previous data
   * @param {Object} newData - The new briefing data
   * @returns {Object} Object with changed section flags
   */
  detectChangedSections(newData) {
    const changes = {
      flash: false,
      summary: false,
      context: false,
      metadata: false
    };
    
    // This is a simplistic implementation - in production you'd want to:
    // 1. Store the previous data for comparison
    // 2. Do a deep comparison of sections
    // 3. Track specific item IDs that changed
    
    // For now, just mark all sections as changed
    return {
      flash: true,
      summary: true,
      context: true,
      metadata: true
    };
  }
  
  /**
   * Update the visual indicator of when the last refresh occurred
   * @param {Date} timestamp - The timestamp of the last update
   */
  updateLastRefreshIndicator(timestamp) {
    const indicator = document.querySelector('.last-update-time');
    if (indicator) {
      indicator.textContent = this.formatTimestamp(timestamp);
      
      // Add 'pulse' animation class
      indicator.classList.add('pulse-update');
      
      // Remove animation class after animation completes
      setTimeout(() => {
        indicator.classList.remove('pulse-update');
      }, 1000);
    }
  }
  
  /**
   * Update the status indicator UI element
   * @param {string} status - The new status
   */
  updateStatusIndicator(status) {
    // Update UI indicator
    const indicator = document.querySelector('.update-status-indicator');
    if (indicator) {
      // Remove all status classes
      indicator.classList.remove(
        'status-idle', 
        'status-updating', 
        'status-updated',
        'status-error',
        'status-offline',
        'status-connection-lost'
      );
      
      // Add appropriate class
      indicator.classList.add(`status-${status}`);
    }
    
    // Call status change callback if provided
    if (typeof this.options.onStatusChange === 'function') {
      this.options.onStatusChange(status);
    }
  }
  
  /**
   * Format a timestamp into a human-readable string
   * @param {Date} timestamp - The timestamp to format
   * @returns {string} Formatted time string
   */
  formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    
    const now = new Date();
    const diffMs = now - timestamp;
    const diffSec = Math.floor(diffMs / 1000);
    
    if (diffSec < 60) {
      return 'Just now';
    } else if (diffSec < 3600) {
      const mins = Math.floor(diffSec / 60);
      return `${mins}m ago`;
    } else if (diffSec < 86400) {
      const hours = Math.floor(diffSec / 3600);
      return `${hours}h ago`;
    } else {
      // For > 1 day, show actual date/time
      return timestamp.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }
  
  /**
   * Force an immediate update
   */
  forceUpdate() {
    // Reset state to ensure update happens
    this.state.lastEtag = null;
    this.state.lastModified = null;
    
    // Trigger update
    this.checkForUpdates();
  }
  
  /**
   * Get the current update service state
   * @returns {Object} Current state
   */
  getState() {
    return {
      ...this.state,
      updateIntervalMs: this.options.updateIntervalMs,
      flashUpdateIntervalMs: this.options.flashUpdateIntervalMs
    };
  }
}

// Export the class
window.BriefingAutoUpdateService = AutoUpdateService;