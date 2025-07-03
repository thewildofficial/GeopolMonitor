import { writable, derived, type Readable } from 'svelte/store';
import type { WebSocketState, WebSocketMessage, TelegramMessage } from '$lib/types';

// Mock data for testing the professional design
const mockMessages: TelegramMessage[] = [
  {
    id: 'msg_001',
    channel: 'GeopoliticsToday',
    content: 'BREAKING: Military convoy movements observed near disputed border region. Multiple intelligence sources reporting increased activity in the last 6 hours. Situation developing.',
    timestamp: new Date(Date.now() - 180000), // 3 minutes ago
    location: { 
      country: 'Ukraine', 
      region: 'Eastern Europe',
      coordinates: [50.4501, 30.5234]
    },
    relevanceScore: 94,
    threatLevel: 'HIGH',
    entities: ['Military', 'Border Security', 'Intelligence', 'Convoy'],
    sentiment: { 
      score: -0.8, 
      confidence: 0.92, 
      label: 'negative' 
    },
    metadata: {
      originalId: 'tg_789456',
      channelType: 'public',
      mediaType: 'text',
      processingTime: new Date()
    }
  },
  {
    id: 'msg_002',
    channel: 'DiplomaticWatch',
    content: 'Positive developments in trade negotiations. Both parties expressing optimism following today\'s diplomatic breakthrough. Economic cooperation agreements expected to be finalized within 48 hours.',
    timestamp: new Date(Date.now() - 420000), // 7 minutes ago
    location: { 
      country: 'Singapore', 
      region: 'Southeast Asia',
      coordinates: [1.3521, 103.8198]
    },
    relevanceScore: 78,
    threatLevel: 'LOW',
    entities: ['Trade', 'Diplomacy', 'Economics', 'Cooperation'],
    sentiment: { 
      score: 0.7, 
      confidence: 0.88, 
      label: 'positive' 
    },
    metadata: {
      originalId: 'tg_789457',
      channelType: 'public',
      mediaType: 'text',
      processingTime: new Date()
    }
  },
  {
    id: 'msg_003',
    channel: 'SecurityAnalyst',
    content: 'Cybersecurity incident reported at major infrastructure facility. Initial assessment suggests coordinated attack. Emergency response protocols activated. Investigation ongoing.',
    timestamp: new Date(Date.now() - 600000), // 10 minutes ago
    location: { 
      country: 'Estonia', 
      region: 'Northern Europe',
      coordinates: [59.4370, 24.7536]
    },
    relevanceScore: 87,
    threatLevel: 'HIGH',
    entities: ['Cybersecurity', 'Infrastructure', 'Attack', 'Emergency'],
    sentiment: { 
      score: -0.6, 
      confidence: 0.85, 
      label: 'negative' 
    },
    metadata: {
      originalId: 'tg_789458',
      channelType: 'private',
      mediaType: 'text',
      processingTime: new Date()
    }
  },
  {
    id: 'msg_004',
    channel: 'EconomicIndicators',
    content: 'Markets showing resilience following yesterday\'s policy announcements. Energy sector particularly strong with renewable investments up 23%. Analysts cautiously optimistic about Q4 outlook.',
    timestamp: new Date(Date.now() - 900000), // 15 minutes ago
    location: { 
      country: 'Germany', 
      region: 'Central Europe',
      coordinates: [52.5200, 13.4050]
    },
    relevanceScore: 65,
    threatLevel: 'LOW',
    entities: ['Markets', 'Energy', 'Investment', 'Policy'],
    sentiment: { 
      score: 0.5, 
      confidence: 0.82, 
      label: 'positive' 
    },
    metadata: {
      originalId: 'tg_789459',
      channelType: 'public',
      mediaType: 'text',
      processingTime: new Date()
    }
  },
  {
    id: 'msg_005',
    channel: 'IntelBriefings',
    content: 'Unconfirmed reports of unusual aircraft activity over international waters. Multiple radar contacts detected. Regional air forces on heightened alert status. Verification pending.',
    timestamp: new Date(Date.now() - 1200000), // 20 minutes ago
    location: { 
      country: 'International Waters', 
      region: 'South China Sea',
      coordinates: [16.0000, 112.0000]
    },
    relevanceScore: 91,
    threatLevel: 'MEDIUM',
    entities: ['Aircraft', 'Military', 'International Waters', 'Alert'],
    sentiment: { 
      score: -0.4, 
      confidence: 0.79, 
      label: 'negative' 
    },
    metadata: {
      originalId: 'tg_789460',
      channelType: 'private',
      mediaType: 'text',
      processingTime: new Date()
    }
  }
];

const initialState: WebSocketState = {
  connected: false,
  messages: mockMessages,
  error: null,
  reconnectAttempts: 0
};

function createWebSocketStore() {
  const { subscribe, set, update } = writable<WebSocketState>(initialState);

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  return {
    subscribe,
    connect: () => {
      console.log('🔴 WebSocket connecting...');
      
      // Show mock data immediately for demo
      update(state => ({ 
        ...state, 
        connected: false,  // Keep as false since we're not actually connecting
        error: null,
        messages: mockMessages 
      }));

      // For demo purposes, don't actually try to connect to WebSocket
      // but simulate periodic message updates
      const messageInterval = setInterval(() => {
        const newMessage: TelegramMessage = {
          id: `msg_${Date.now()}`,
          channel: ['GeopoliticsToday', 'SecurityAnalyst', 'DiplomaticWatch'][Math.floor(Math.random() * 3)],
          content: `Simulated real-time intelligence update at ${new Date().toLocaleTimeString()}. System operational and monitoring global communications.`,
          timestamp: new Date(),
          location: {
            country: ['Ukraine', 'Estonia', 'Singapore'][Math.floor(Math.random() * 3)],
            region: ['Eastern Europe', 'Northern Europe', 'Southeast Asia'][Math.floor(Math.random() * 3)],
            coordinates: [Math.random() * 180 - 90, Math.random() * 360 - 180]
          },
          relevanceScore: Math.floor(Math.random() * 40) + 60, // 60-99
          threatLevel: ['LOW', 'MEDIUM', 'HIGH'][Math.floor(Math.random() * 3)] as 'LOW' | 'MEDIUM' | 'HIGH',
          entities: ['Intelligence', 'Monitor', 'System', 'Update'],
          sentiment: {
            score: (Math.random() - 0.5) * 2, // -1 to 1
            confidence: Math.random() * 0.3 + 0.7, // 0.7 to 1
            label: ['positive', 'neutral', 'negative'][Math.floor(Math.random() * 3)] as 'positive' | 'neutral' | 'negative'
          },
          metadata: {
            originalId: `tg_${Date.now()}`,
            channelType: 'public',
            mediaType: 'text',
            processingTime: new Date()
          }
        };

        update(state => ({
          ...state,
          messages: [newMessage, ...state.messages].slice(0, 50) // Keep last 50 messages
        }));
      }, 30000); // New message every 30 seconds

      // Store interval for cleanup
      return () => {
        clearInterval(messageInterval);
      };
    },
    disconnect: () => {
      if (ws) {
        ws.close();
        ws = null;
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      update(state => ({ 
        ...state, 
        connected: false,
        reconnectAttempts: 0
      }));
    },
    send: (message: any) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    }
  };
}

export const webSocketStore = createWebSocketStore();

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

// Export websocketStore for compatibility
export const websocketStore = wsManager;

// Auto-connect in browser environment
if (typeof window !== 'undefined') {
  wsManager.connect();
} 