import { writable, derived, type Readable } from 'svelte/store';
import type { WebSocketState, WebSocketMessage, TelegramMessage } from '$lib/types';

// WebSocket connection state
export const websocketState = writable<WebSocketState>({
  connected: false,
  reconnecting: false,
  connectionQuality: 'poor',
  latency: 0,
  lastHeartbeat: new Date()
});

// Raw WebSocket messages
export const rawMessages = writable<WebSocketMessage[]>([]);

// Telegram messages (derived from raw messages)
export const telegramMessages = derived(
  rawMessages,
  ($rawMessages) => $rawMessages
    .filter(msg => msg.type === 'telegram_message')
    .map(msg => msg.data as TelegramMessage)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
);

// Connection quality indicator
export const connectionQuality: Readable<string> = derived(
  websocketState,
  ($state) => {
    if (!$state.connected) return 'disconnected';
    if ($state.reconnecting) return 'reconnecting';
    
    const { latency } = $state;
    if (latency < 100) return 'excellent';
    if (latency < 300) return 'good';
    if (latency < 1000) return 'fair';
    return 'poor';
  }
);

// WebSocket manager class
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: number | null = null;

  connect(url: string = 'ws://localhost:8000/ws') {
    try {
      this.ws = new WebSocket(url);
      this.setupEventListeners();
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      this.handleReconnect();
    }
  }

  private setupEventListeners() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      websocketState.update(state => ({
        ...state,
        connected: true,
        reconnecting: false,
        lastHeartbeat: new Date()
      }));
      
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        
        // Update last heartbeat
        websocketState.update(state => ({
          ...state,
          lastHeartbeat: new Date()
        }));

        // Add message to store
        rawMessages.update(messages => [message, ...messages].slice(0, 1000)); // Keep last 1000 messages
        
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      websocketState.update(state => ({
        ...state,
        connected: false
      }));
      
      this.stopHeartbeat();
      
      if (event.code !== 1000) { // Not a normal closure
        this.handleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      websocketState.update(state => ({
        ...state,
        connected: false,
        connectionQuality: 'poor'
      }));
    };
  }

  private handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    websocketState.update(state => ({
      ...state,
      reconnecting: true
    }));

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      this.connect();
    }, delay);
  }

  private startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const start = Date.now();
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: start }));
        
        // Measure latency (simplified)
        setTimeout(() => {
          const latency = Date.now() - start;
          websocketState.update(state => ({
            ...state,
            latency,
            connectionQuality: latency < 100 ? 'excellent' : latency < 300 ? 'good' : latency < 1000 ? 'fair' : 'poor'
          }));
        }, 100);
      }
    }, 30000); // Every 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    this.stopHeartbeat();
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message not sent:', message);
    }
  }
}

// Export singleton instance
export const wsManager = new WebSocketManager();

// Auto-connect in browser environment
if (typeof window !== 'undefined') {
  wsManager.connect();
} 