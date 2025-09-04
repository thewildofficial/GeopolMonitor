// Core Intelligence Platform Types
export interface TelegramMessage {
  id: string;
  channel: string;
  content: string;
  timestamp: Date;
  location?: GeographicLocation;
  relevanceScore: number;
  threatLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  entities: string[];
  sentiment: SentimentAnalysis;
  metadata: MessageMetadata;
}

export interface GeographicLocation {
  country: string;
  region?: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface SentimentAnalysis {
  score: number; // -1 to 1
  confidence: number; // 0 to 1
  label: 'positive' | 'negative' | 'neutral';
}

export interface MessageMetadata {
  originalId: string;
  channelType: 'public' | 'private';
  forwardedFrom?: string;
  mediaType?: 'text' | 'image' | 'video' | 'document';
  processingTime: Date;
}

// WebSocket Connection Types
export interface WebSocketState {
  connected: boolean;
  reconnecting: boolean;
  connectionQuality: 'excellent' | 'good' | 'fair' | 'poor';
  latency: number;
  lastHeartbeat: Date;
}

export interface WebSocketMessage {
  type: 'telegram_message' | 'system_update' | 'heartbeat' | 'error';
  data: any;
  timestamp: Date;
}

// Map and Visualization Types
export interface MapEventMarker {
  id: string;
  location: GeographicLocation;
  eventType: 'conflict' | 'political' | 'economic' | 'social';
  intensity: number;
  relatedMessages: string[];
  timestamp: Date;
}

export interface CountryData {
  code: string;
  name: string;
  messageCount: number;
  averageRelevance: number;
  threatLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  lastActivity: Date;
}

// Search and Filtering Types
export interface SearchQuery {
  text: string;
  filters: {
    dateRange: {
      start: Date;
      end: Date;
    };
    relevanceThreshold: number;
    threatLevels: ('HIGH' | 'MEDIUM' | 'LOW')[];
    countries: string[];
    channels: string[];
  };
}

export interface SearchResult {
  messages: TelegramMessage[];
  totalCount: number;
  facets: {
    countries: { [key: string]: number };
    channels: { [key: string]: number };
    threatLevels: { [key: string]: number };
  };
}

// UI Component Types
export interface FilterState {
  relevanceThreshold: number;
  threatLevels: Set<string>;
  countries: Set<string>;
  channels: Set<string>;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}

export interface NotificationMessage {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  urgent: boolean;
}

// Analytics and Sentiment Types
export interface SentimentTrend {
  timestamp: Date;
  averageSentiment: number;
  messageCount: number;
  country?: string;
  region?: string;
}

export interface ThreatAlert {
  id: string;
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  affectedRegions: string[];
  confidence: number;
  timestamp: Date;
  relatedMessages: string[];
} 