/**
 * BriefingSocket.js
 * Handles WebSocket connection for real-time briefing updates
 */

class BriefingSocket {
  constructor(updateHandler) {
    // The handler function for updates
    this.updateHandler = updateHandler || function() {};
    
    // WebSocket connection
    this.socket = null;
    
    // Connection status
    this.isConnected = false;
    
    // Reconnection settings
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 2000; // Start with 2 seconds
    this.reconnectTimer = null;
    
    // Initialize WebSocket connection
    this.init();
  }
  
  /**
   * Initialize the WebSocket connection
   */
  init() {
    try {
      // Determine protocol (ws or wss) based on current page protocol
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/briefing`;
      
      console.log(`Connecting to WebSocket at ${wsUrl}`);
      
      this.socket = new WebSocket(wsUrl);
      
      // Set up event handlers
      this.socket.onopen = this.handleOpen.bind(this);
      this.socket.onclose = this.handleClose.bind(this);
      this.socket.onmessage = this.handleMessage.bind(this);
      this.socket.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('Error initializing WebSocket:', error);
      this.scheduleReconnect();
    }
  }
  
  /**
   * Handle WebSocket connection open
   * @param {Event} event - The open event
   */
  handleOpen(event) {
    console.log('WebSocket connection established');
    this.isConnected = true;
    this.reconnectAttempts = 0; // Reset reconnect counter on successful connection
    
    // Send subscription message
    this.subscribe();
  }
  
  /**
   * Handle WebSocket connection close
   * @param {CloseEvent} event - The close event
   */
  handleClose(event) {
    console.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
    this.isConnected = false;
    
    // Attempt to reconnect if the connection was closed unexpectedly
    if (event.code !== 1000) { // 1000 is normal closure
      this.scheduleReconnect();
    }
  }
  
  /**
   * Handle incoming WebSocket messages
   * @param {MessageEvent} event - The message event
   */
  handleMessage(event) {
    try {
      const data = JSON.parse(event.data);
      console.log('Received WebSocket message:', data);
      
      // Process different message types
      if (data.type === 'briefing_updated' || data.type === 'new_flash_alert') {
        this.updateHandler(data);
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
    }
  }
  
  /**
   * Handle WebSocket errors
   * @param {Event} event - The error event
   */
  handleError(event) {
    console.error('WebSocket error:', event);
  }
  
  /**
   * Schedule a reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      
      // Use exponential backoff for reconnection attempts
      const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
      console.log(`Scheduling WebSocket reconnection attempt ${this.reconnectAttempts} in ${delay}ms`);
      
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = setTimeout(() => {
        console.log(`Attempting WebSocket reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.init();
      }, delay);
    } else {
      console.error(`Failed to reconnect after ${this.maxReconnectAttempts} attempts`);
    }
  }
  
  /**
   * Subscribe to briefing updates
   */
  subscribe() {
    if (!this.isConnected) return;
    
    const subscribeMessage = {
      action: 'subscribe',
      channel: 'briefing_updates'
    };
    
    this.socket.send(JSON.stringify(subscribeMessage));
    console.log('Subscribed to briefing updates');
  }
  
  /**
   * Send a message through the WebSocket
   * @param {Object} data - The data to send
   * @returns {boolean} Whether the message was sent
   */
  sendMessage(data) {
    if (!this.isConnected) {
      console.warn('Cannot send message: WebSocket not connected');
      return false;
    }
    
    try {
      this.socket.send(JSON.stringify(data));
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }
  
  /**
   * Manually close the WebSocket connection
   */
  close() {
    if (this.socket) {
      this.socket.close(1000, 'Manual close');
    }
    
    clearTimeout(this.reconnectTimer);
    this.isConnected = false;
  }
}