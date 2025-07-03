import { c as create_ssr_component, b as createEventDispatcher, e as escape, d as each, a as subscribe, f as add_attribute, v as validate_component } from "../../../chunks/ssr.js";
import { d as derived, w as writable } from "../../../chunks/index.js";
const mockMessages = [
  {
    id: "msg_001",
    channel: "GeopoliticsToday",
    content: "BREAKING: Military convoy movements observed near disputed border region. Multiple intelligence sources reporting increased activity in the last 6 hours. Situation developing.",
    timestamp: new Date(Date.now() - 18e4),
    // 3 minutes ago
    location: {
      country: "Ukraine",
      region: "Eastern Europe",
      coordinates: [50.4501, 30.5234]
    },
    relevanceScore: 94,
    threatLevel: "HIGH",
    entities: ["Military", "Border Security", "Intelligence", "Convoy"],
    sentiment: {
      score: -0.8,
      confidence: 0.92,
      label: "negative"
    },
    metadata: {
      originalId: "tg_789456",
      channelType: "public",
      mediaType: "text",
      processingTime: /* @__PURE__ */ new Date()
    }
  },
  {
    id: "msg_002",
    channel: "DiplomaticWatch",
    content: "Positive developments in trade negotiations. Both parties expressing optimism following today's diplomatic breakthrough. Economic cooperation agreements expected to be finalized within 48 hours.",
    timestamp: new Date(Date.now() - 42e4),
    // 7 minutes ago
    location: {
      country: "Singapore",
      region: "Southeast Asia",
      coordinates: [1.3521, 103.8198]
    },
    relevanceScore: 78,
    threatLevel: "LOW",
    entities: ["Trade", "Diplomacy", "Economics", "Cooperation"],
    sentiment: {
      score: 0.7,
      confidence: 0.88,
      label: "positive"
    },
    metadata: {
      originalId: "tg_789457",
      channelType: "public",
      mediaType: "text",
      processingTime: /* @__PURE__ */ new Date()
    }
  },
  {
    id: "msg_003",
    channel: "SecurityAnalyst",
    content: "Cybersecurity incident reported at major infrastructure facility. Initial assessment suggests coordinated attack. Emergency response protocols activated. Investigation ongoing.",
    timestamp: new Date(Date.now() - 6e5),
    // 10 minutes ago
    location: {
      country: "Estonia",
      region: "Northern Europe",
      coordinates: [59.437, 24.7536]
    },
    relevanceScore: 87,
    threatLevel: "HIGH",
    entities: ["Cybersecurity", "Infrastructure", "Attack", "Emergency"],
    sentiment: {
      score: -0.6,
      confidence: 0.85,
      label: "negative"
    },
    metadata: {
      originalId: "tg_789458",
      channelType: "private",
      mediaType: "text",
      processingTime: /* @__PURE__ */ new Date()
    }
  },
  {
    id: "msg_004",
    channel: "EconomicIndicators",
    content: "Markets showing resilience following yesterday's policy announcements. Energy sector particularly strong with renewable investments up 23%. Analysts cautiously optimistic about Q4 outlook.",
    timestamp: new Date(Date.now() - 9e5),
    // 15 minutes ago
    location: {
      country: "Germany",
      region: "Central Europe",
      coordinates: [52.52, 13.405]
    },
    relevanceScore: 65,
    threatLevel: "LOW",
    entities: ["Markets", "Energy", "Investment", "Policy"],
    sentiment: {
      score: 0.5,
      confidence: 0.82,
      label: "positive"
    },
    metadata: {
      originalId: "tg_789459",
      channelType: "public",
      mediaType: "text",
      processingTime: /* @__PURE__ */ new Date()
    }
  },
  {
    id: "msg_005",
    channel: "IntelBriefings",
    content: "Unconfirmed reports of unusual aircraft activity over international waters. Multiple radar contacts detected. Regional air forces on heightened alert status. Verification pending.",
    timestamp: new Date(Date.now() - 12e5),
    // 20 minutes ago
    location: {
      country: "International Waters",
      region: "South China Sea",
      coordinates: [16, 112]
    },
    relevanceScore: 91,
    threatLevel: "MEDIUM",
    entities: ["Aircraft", "Military", "International Waters", "Alert"],
    sentiment: {
      score: -0.4,
      confidence: 0.79,
      label: "negative"
    },
    metadata: {
      originalId: "tg_789460",
      channelType: "private",
      mediaType: "text",
      processingTime: /* @__PURE__ */ new Date()
    }
  }
];
const initialState = {
  connected: false,
  messages: mockMessages,
  error: null,
  reconnectAttempts: 0
};
function createWebSocketStore() {
  const { subscribe: subscribe2, set, update } = writable(initialState);
  return {
    subscribe: subscribe2,
    connect: () => {
      update((state) => ({
        ...state,
        connected: true,
        error: null,
        messages: mockMessages
      }));
      const messageInterval = setInterval(() => {
        const newMessage = {
          id: `msg_${Date.now()}`,
          channel: ["GeopoliticsToday", "SecurityAnalyst", "DiplomaticWatch"][Math.floor(Math.random() * 3)],
          content: `Simulated real-time intelligence update at ${(/* @__PURE__ */ new Date()).toLocaleTimeString()}. System operational and monitoring global communications.`,
          timestamp: /* @__PURE__ */ new Date(),
          location: {
            country: ["Ukraine", "Estonia", "Singapore"][Math.floor(Math.random() * 3)],
            region: ["Eastern Europe", "Northern Europe", "Southeast Asia"][Math.floor(Math.random() * 3)],
            coordinates: [Math.random() * 180 - 90, Math.random() * 360 - 180]
          },
          relevanceScore: Math.floor(Math.random() * 40) + 60,
          // 60-99
          threatLevel: ["LOW", "MEDIUM", "HIGH"][Math.floor(Math.random() * 3)],
          entities: ["Intelligence", "Monitor", "System", "Update"],
          sentiment: {
            score: (Math.random() - 0.5) * 2,
            // -1 to 1
            confidence: Math.random() * 0.3 + 0.7,
            // 0.7 to 1
            label: ["positive", "neutral", "negative"][Math.floor(Math.random() * 3)]
          },
          metadata: {
            originalId: `tg_${Date.now()}`,
            channelType: "public",
            mediaType: "text",
            processingTime: /* @__PURE__ */ new Date()
          }
        };
        update((state) => ({
          ...state,
          messages: [newMessage, ...state.messages].slice(0, 50)
          // Keep last 50 messages
        }));
      }, 3e4);
      return () => {
        clearInterval(messageInterval);
      };
    },
    disconnect: () => {
      update((state) => ({
        ...state,
        connected: false,
        reconnectAttempts: 0
      }));
    },
    send: (message) => {
    }
  };
}
const webSocketStore = createWebSocketStore();
const websocketState = writable({
  connected: false,
  reconnecting: false,
  connectionQuality: "poor",
  latency: 0,
  lastHeartbeat: /* @__PURE__ */ new Date()
});
const rawMessages = writable([]);
const telegramMessages = derived(
  rawMessages,
  ($rawMessages) => $rawMessages.filter((msg) => msg.type === "telegram_message").map((msg) => msg.data).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
);
derived(
  websocketState,
  ($state) => {
    if (!$state.connected) return "disconnected";
    if ($state.reconnecting) return "reconnecting";
    const { latency } = $state;
    if (latency < 100) return "excellent";
    if (latency < 300) return "good";
    if (latency < 1e3) return "fair";
    return "poor";
  }
);
class WebSocketManager {
  constructor() {
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1e3;
    this.heartbeatInterval = null;
  }
  connect(url = "ws://localhost:8000/ws") {
    try {
      this.ws = new WebSocket(url);
      this.setupEventListeners();
    } catch (error) {
      console.error("WebSocket connection failed:", error);
      this.handleReconnect();
    }
  }
  setupEventListeners() {
    if (!this.ws) return;
    this.ws.onopen = () => {
      console.log("✅ WebSocket connected");
      websocketState.update((state) => ({
        ...state,
        connected: true,
        reconnecting: false,
        lastHeartbeat: /* @__PURE__ */ new Date()
      }));
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        websocketState.update((state) => ({
          ...state,
          lastHeartbeat: /* @__PURE__ */ new Date()
        }));
        rawMessages.update((messages) => [message, ...messages].slice(0, 1e3));
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };
    this.ws.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      websocketState.update((state) => ({
        ...state,
        connected: false
      }));
      this.stopHeartbeat();
      if (event.code !== 1e3) {
        this.handleReconnect();
      }
    };
    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      websocketState.update((state) => ({
        ...state,
        connected: false,
        connectionQuality: "poor"
      }));
    };
  }
  handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error("Max reconnection attempts reached");
      return;
    }
    websocketState.update((state) => ({
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
  startHeartbeat() {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        const start = Date.now();
        this.ws.send(JSON.stringify({ type: "ping", timestamp: start }));
        setTimeout(() => {
          const latency = Date.now() - start;
          websocketState.update((state) => ({
            ...state,
            latency,
            connectionQuality: latency < 100 ? "excellent" : latency < 300 ? "good" : latency < 1e3 ? "fair" : "poor"
          }));
        }, 100);
      }
    }, 3e4);
  }
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }
  disconnect() {
    if (this.ws) {
      this.ws.close(1e3, "Manual disconnect");
      this.ws = null;
    }
    this.stopHeartbeat();
  }
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn("WebSocket not connected, message not sent:", message);
    }
  }
}
const wsManager = new WebSocketManager();
if (typeof window !== "undefined") {
  wsManager.connect();
}
const filterState = writable({
  relevanceThreshold: 0.5,
  threatLevels: /* @__PURE__ */ new Set(["HIGH", "MEDIUM", "LOW"]),
  countries: /* @__PURE__ */ new Set(),
  channels: /* @__PURE__ */ new Set(),
  dateRange: {
    start: null,
    end: null
  }
});
const searchQuery = writable("");
const filteredMessages = derived(
  [telegramMessages, filterState, searchQuery],
  ([$messages, $filters, $search]) => {
    let filtered = $messages;
    filtered = filtered.filter((msg) => msg.relevanceScore >= $filters.relevanceThreshold);
    if ($filters.threatLevels.size > 0) {
      filtered = filtered.filter((msg) => $filters.threatLevels.has(msg.threatLevel));
    }
    if ($filters.countries.size > 0) {
      filtered = filtered.filter(
        (msg) => msg.location && $filters.countries.has(msg.location.country)
      );
    }
    if ($filters.channels.size > 0) {
      filtered = filtered.filter((msg) => $filters.channels.has(msg.channel));
    }
    if ($filters.dateRange.start || $filters.dateRange.end) {
      filtered = filtered.filter((msg) => {
        const msgDate = new Date(msg.timestamp);
        const inRange = (!$filters.dateRange.start || msgDate >= $filters.dateRange.start) && (!$filters.dateRange.end || msgDate <= $filters.dateRange.end);
        return inRange;
      });
    }
    if ($search.trim()) {
      const searchLower = $search.toLowerCase();
      filtered = filtered.filter(
        (msg) => msg.content.toLowerCase().includes(searchLower) || msg.channel.toLowerCase().includes(searchLower) || msg.entities.some((entity) => entity.toLowerCase().includes(searchLower))
      );
    }
    return filtered;
  }
);
derived(
  filteredMessages,
  ($filtered) => {
    const total = $filtered.length;
    const highThreat = $filtered.filter((msg) => msg.threatLevel === "HIGH").length;
    const mediumThreat = $filtered.filter((msg) => msg.threatLevel === "MEDIUM").length;
    const lowThreat = $filtered.filter((msg) => msg.threatLevel === "LOW").length;
    const countryCounts = {};
    $filtered.forEach((msg) => {
      if (msg.location?.country) {
        countryCounts[msg.location.country] = (countryCounts[msg.location.country] || 0) + 1;
      }
    });
    const channelCounts = {};
    $filtered.forEach((msg) => {
      channelCounts[msg.channel] = (channelCounts[msg.channel] || 0) + 1;
    });
    const avgSentiment = total > 0 ? $filtered.reduce((sum, msg) => sum + msg.sentiment.score, 0) / total : 0;
    const avgRelevance = total > 0 ? $filtered.reduce((sum, msg) => sum + msg.relevanceScore, 0) / total : 0;
    return {
      total,
      threatBreakdown: {
        high: highThreat,
        medium: mediumThreat,
        low: lowThreat
      },
      countryCounts,
      channelCounts,
      avgSentiment,
      avgRelevance,
      // Recent activity (last hour)
      recentActivity: $filtered.filter(
        (msg) => new Date(msg.timestamp) > new Date(Date.now() - 60 * 60 * 1e3)
      ).length
    };
  }
);
derived(
  telegramMessages,
  ($messages) => {
    const countries = /* @__PURE__ */ new Set();
    const channels = /* @__PURE__ */ new Set();
    $messages.forEach((msg) => {
      if (msg.location?.country) {
        countries.add(msg.location.country);
      }
      channels.add(msg.channel);
    });
    return {
      countries: Array.from(countries).sort(),
      channels: Array.from(channels).sort()
    };
  }
);
const filterActions = {
  // Update relevance threshold
  setRelevanceThreshold: (threshold) => {
    filterState.update((state) => ({
      ...state,
      relevanceThreshold: Math.max(0, Math.min(1, threshold))
    }));
  },
  // Toggle threat level
  toggleThreatLevel: (level) => {
    filterState.update((state) => {
      const newThreatLevels = new Set(state.threatLevels);
      if (newThreatLevels.has(level)) {
        newThreatLevels.delete(level);
      } else {
        newThreatLevels.add(level);
      }
      return {
        ...state,
        threatLevels: newThreatLevels
      };
    });
  },
  // Toggle country filter
  toggleCountry: (country) => {
    filterState.update((state) => {
      const newCountries = new Set(state.countries);
      if (newCountries.has(country)) {
        newCountries.delete(country);
      } else {
        newCountries.add(country);
      }
      return {
        ...state,
        countries: newCountries
      };
    });
  },
  // Toggle channel filter
  toggleChannel: (channel) => {
    filterState.update((state) => {
      const newChannels = new Set(state.channels);
      if (newChannels.has(channel)) {
        newChannels.delete(channel);
      } else {
        newChannels.add(channel);
      }
      return {
        ...state,
        channels: newChannels
      };
    });
  },
  // Set date range
  setDateRange: (start, end) => {
    filterState.update((state) => ({
      ...state,
      dateRange: { start, end }
    }));
  },
  // Clear all filters
  clearFilters: () => {
    filterState.set({
      relevanceThreshold: 0,
      threatLevels: /* @__PURE__ */ new Set(["HIGH", "MEDIUM", "LOW"]),
      countries: /* @__PURE__ */ new Set(),
      channels: /* @__PURE__ */ new Set(),
      dateRange: { start: null, end: null }
    });
    searchQuery.set("");
  },
  // Reset filters to show all data
  resetFilters: () => {
    filterState.set({
      relevanceThreshold: 0,
      threatLevels: /* @__PURE__ */ new Set(["HIGH", "MEDIUM", "LOW"]),
      countries: /* @__PURE__ */ new Set(),
      channels: /* @__PURE__ */ new Set(),
      dateRange: { start: null, end: null }
    });
    searchQuery.set("");
  }
};
const filterStore = filterActions;
const css$2 = {
  code: ".feed-item.svelte-129e5w6.svelte-129e5w6{background-color:transparent;padding:var(--spacing-md);border-bottom:1px solid var(--border-primary);transition:all 0.2s ease}.feed-item.svelte-129e5w6.svelte-129e5w6:hover{background-color:rgba(55, 65, 81, 0.3)}.feed-item-header.svelte-129e5w6.svelte-129e5w6{display:flex;align-items:center;gap:var(--spacing-sm);margin-bottom:var(--spacing-sm)}.feed-item-avatar.svelte-129e5w6.svelte-129e5w6{flex-shrink:0}.avatar-placeholder.svelte-129e5w6.svelte-129e5w6{width:40px;height:40px;border-radius:50%;background-color:var(--background-tertiary);display:flex;align-items:center;justify-content:center;font-size:var(--font-size-sm);font-weight:var(--font-weight-semibold);color:var(--text-accent)}.feed-item-meta.svelte-129e5w6.svelte-129e5w6{flex:1;display:flex;flex-direction:column;gap:2px}.feed-item-source.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-sm);font-weight:var(--font-weight-semibold);color:var(--text-primary)}.feed-item-timestamp.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-xs);font-weight:var(--font-weight-regular);color:var(--text-secondary)}.feed-item-badges.svelte-129e5w6.svelte-129e5w6{display:flex;align-items:center;gap:var(--spacing-sm)}.relevance-score.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-xs);color:var(--text-secondary)}.feed-item-body.svelte-129e5w6.svelte-129e5w6{margin-bottom:var(--spacing-md)}.feed-item-content.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-md);font-weight:var(--font-weight-regular);color:var(--text-primary);line-height:1.5;margin-bottom:var(--spacing-sm)}.feed-item-sentiment.svelte-129e5w6.svelte-129e5w6{display:flex;align-items:center;gap:var(--spacing-sm);margin-bottom:var(--spacing-sm)}.sentiment-label.svelte-129e5w6.svelte-129e5w6{padding:2px 6px;border-radius:4px;font-size:var(--font-size-xs);font-weight:var(--font-weight-medium);text-transform:uppercase}.sentiment-positive.svelte-129e5w6.svelte-129e5w6{background-color:rgba(16, 185, 129, 0.2);color:var(--status-active)}.sentiment-negative.svelte-129e5w6.svelte-129e5w6{background-color:rgba(249, 115, 22, 0.2);color:var(--status-high)}.sentiment-neutral.svelte-129e5w6.svelte-129e5w6{background-color:rgba(107, 114, 128, 0.2);color:var(--status-inactive)}.sentiment-score.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-xs);color:var(--text-secondary)}.feed-item-location.svelte-129e5w6.svelte-129e5w6{display:flex;align-items:center;gap:var(--spacing-xs);margin-bottom:var(--spacing-sm)}.location-icon.svelte-129e5w6.svelte-129e5w6{width:14px;height:14px;color:var(--text-secondary)}.location-text.svelte-129e5w6.svelte-129e5w6{font-size:var(--font-size-xs);color:var(--text-secondary)}.feed-item-entities.svelte-129e5w6.svelte-129e5w6{display:flex;flex-wrap:wrap;gap:var(--spacing-xs);margin-bottom:var(--spacing-sm)}.entity-tag.svelte-129e5w6.svelte-129e5w6{background-color:var(--background-tertiary);color:var(--text-secondary);padding:2px 6px;border-radius:4px;font-size:var(--font-size-xs);font-weight:var(--font-weight-medium)}.feed-item-footer.svelte-129e5w6.svelte-129e5w6{display:flex;justify-content:flex-end}.feed-item-actions.svelte-129e5w6.svelte-129e5w6{display:flex;gap:var(--spacing-xs)}.action-button.svelte-129e5w6.svelte-129e5w6{background:transparent;border:none;padding:var(--spacing-xs);cursor:pointer;transition:all 0.2s ease;border-radius:4px}.action-button.svelte-129e5w6.svelte-129e5w6:hover{background-color:var(--background-tertiary)}.action-icon.svelte-129e5w6.svelte-129e5w6{width:14px;height:14px;color:var(--text-secondary)}.action-button.svelte-129e5w6:hover .action-icon.svelte-129e5w6{color:var(--text-accent)}",
  map: `{"version":3,"file":"MessageCard.svelte","sources":["MessageCard.svelte"],"sourcesContent":["<script>\\n  import { createEventDispatcher } from 'svelte';\\n\\n  export let message;\\n\\n  const dispatch = createEventDispatcher();\\n\\n  function handleAction(action) {\\n    dispatch('action', {\\n      action,\\n      messageId: message.id\\n    });\\n  }\\n<\/script>\\n\\n<div class=\\"feed-item\\">\\n  <div class=\\"feed-item-header\\">\\n    <div class=\\"feed-item-avatar\\">\\n      <div class=\\"avatar-placeholder\\">\\n        {message.channel.charAt(0).toUpperCase()}\\n      </div>\\n    </div>\\n    <div class=\\"feed-item-meta\\">\\n      <div class=\\"feed-item-source\\">\\n        {message.channel}\\n      </div>\\n      <div class=\\"feed-item-timestamp\\">\\n        {new Date(message.timestamp).toLocaleTimeString()}\\n      </div>\\n    </div>\\n    <div class=\\"feed-item-badges\\">\\n      <span class=\\"tag tag-{message.threatLevel.toLowerCase()}\\">\\n        {message.threatLevel}\\n      </span>\\n      <span class=\\"relevance-score\\">\\n        {message.relevanceScore}%\\n      </span>\\n    </div>\\n  </div>\\n\\n  <div class=\\"feed-item-body\\">\\n    <p class=\\"feed-item-content\\">\\n      {message.content}\\n    </p>\\n    \\n    {#if message.sentiment}\\n      <div class=\\"feed-item-sentiment\\">\\n        <span class=\\"sentiment-label sentiment-{message.sentiment.label}\\">\\n          {message.sentiment.label}\\n        </span>\\n        <span class=\\"sentiment-score\\">\\n          {Math.round(message.sentiment.score * 100)}%\\n        </span>\\n      </div>\\n    {/if}\\n\\n    {#if message.location}\\n      <div class=\\"feed-item-location\\">\\n        <svg class=\\"location-icon\\" viewBox=\\"0 0 24 24\\" fill=\\"currentColor\\">\\n          <path d=\\"M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z\\"/>\\n        </svg>\\n        <span class=\\"location-text\\">\\n          {message.location.country}{#if message.location.region}, {message.location.region}{/if}\\n        </span>\\n      </div>\\n    {/if}\\n\\n    {#if message.entities && message.entities.length > 0}\\n      <div class=\\"feed-item-entities\\">\\n        {#each message.entities as entity}\\n          <span class=\\"entity-tag\\">{entity}</span>\\n        {/each}\\n      </div>\\n    {/if}\\n  </div>\\n\\n  <div class=\\"feed-item-footer\\">\\n    <div class=\\"feed-item-actions\\">\\n      <button \\n        class=\\"action-button\\"\\n        on:click={() => handleAction('archive')}\\n        title=\\"Archive message\\"\\n      >\\n        <svg class=\\"action-icon\\" viewBox=\\"0 0 24 24\\" fill=\\"currentColor\\">\\n          <path d=\\"M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM6.24 5h11.52l.83 1H5.42l.82-1zM5 19V8h14v11H5z\\"/>\\n          <path d=\\"M9 10v2h6v-2H9z\\"/>\\n        </svg>\\n      </button>\\n      <button \\n        class=\\"action-button\\"\\n        on:click={() => handleAction('flag')}\\n        title=\\"Flag for review\\"\\n      >\\n        <svg class=\\"action-icon\\" viewBox=\\"0 0 24 24\\" fill=\\"currentColor\\">\\n          <path d=\\"M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z\\"/>\\n        </svg>\\n      </button>\\n      <button \\n        class=\\"action-button\\"\\n        on:click={() => handleAction('share')}\\n        title=\\"Share message\\"\\n      >\\n        <svg class=\\"action-icon\\" viewBox=\\"0 0 24 24\\" fill=\\"currentColor\\">\\n          <path d=\\"M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z\\"/>\\n        </svg>\\n      </button>\\n    </div>\\n  </div>\\n</div>\\n\\n<style>\\n  .feed-item {\\n    background-color: transparent;\\n    padding: var(--spacing-md);\\n    border-bottom: 1px solid var(--border-primary);\\n    transition: all 0.2s ease;\\n  }\\n\\n  .feed-item:hover {\\n    background-color: rgba(55, 65, 81, 0.3);\\n  }\\n\\n  .feed-item-header {\\n    display: flex;\\n    align-items: center;\\n    gap: var(--spacing-sm);\\n    margin-bottom: var(--spacing-sm);\\n  }\\n\\n  .feed-item-avatar {\\n    flex-shrink: 0;\\n  }\\n\\n  .avatar-placeholder {\\n    width: 40px;\\n    height: 40px;\\n    border-radius: 50%;\\n    background-color: var(--background-tertiary);\\n    display: flex;\\n    align-items: center;\\n    justify-content: center;\\n    font-size: var(--font-size-sm);\\n    font-weight: var(--font-weight-semibold);\\n    color: var(--text-accent);\\n  }\\n\\n  .feed-item-meta {\\n    flex: 1;\\n    display: flex;\\n    flex-direction: column;\\n    gap: 2px;\\n  }\\n\\n  .feed-item-source {\\n    font-size: var(--font-size-sm);\\n    font-weight: var(--font-weight-semibold);\\n    color: var(--text-primary);\\n  }\\n\\n  .feed-item-timestamp {\\n    font-size: var(--font-size-xs);\\n    font-weight: var(--font-weight-regular);\\n    color: var(--text-secondary);\\n  }\\n\\n  .feed-item-badges {\\n    display: flex;\\n    align-items: center;\\n    gap: var(--spacing-sm);\\n  }\\n\\n  .relevance-score {\\n    font-size: var(--font-size-xs);\\n    color: var(--text-secondary);\\n  }\\n\\n  .feed-item-body {\\n    margin-bottom: var(--spacing-md);\\n  }\\n\\n  .feed-item-content {\\n    font-size: var(--font-size-md);\\n    font-weight: var(--font-weight-regular);\\n    color: var(--text-primary);\\n    line-height: 1.5;\\n    margin-bottom: var(--spacing-sm);\\n  }\\n\\n  .feed-item-sentiment {\\n    display: flex;\\n    align-items: center;\\n    gap: var(--spacing-sm);\\n    margin-bottom: var(--spacing-sm);\\n  }\\n\\n  .sentiment-label {\\n    padding: 2px 6px;\\n    border-radius: 4px;\\n    font-size: var(--font-size-xs);\\n    font-weight: var(--font-weight-medium);\\n    text-transform: uppercase;\\n  }\\n\\n  .sentiment-positive {\\n    background-color: rgba(16, 185, 129, 0.2);\\n    color: var(--status-active);\\n  }\\n\\n  .sentiment-negative {\\n    background-color: rgba(249, 115, 22, 0.2);\\n    color: var(--status-high);\\n  }\\n\\n  .sentiment-neutral {\\n    background-color: rgba(107, 114, 128, 0.2);\\n    color: var(--status-inactive);\\n  }\\n\\n  .sentiment-score {\\n    font-size: var(--font-size-xs);\\n    color: var(--text-secondary);\\n  }\\n\\n  .feed-item-location {\\n    display: flex;\\n    align-items: center;\\n    gap: var(--spacing-xs);\\n    margin-bottom: var(--spacing-sm);\\n  }\\n\\n  .location-icon {\\n    width: 14px;\\n    height: 14px;\\n    color: var(--text-secondary);\\n  }\\n\\n  .location-text {\\n    font-size: var(--font-size-xs);\\n    color: var(--text-secondary);\\n  }\\n\\n  .feed-item-entities {\\n    display: flex;\\n    flex-wrap: wrap;\\n    gap: var(--spacing-xs);\\n    margin-bottom: var(--spacing-sm);\\n  }\\n\\n  .entity-tag {\\n    background-color: var(--background-tertiary);\\n    color: var(--text-secondary);\\n    padding: 2px 6px;\\n    border-radius: 4px;\\n    font-size: var(--font-size-xs);\\n    font-weight: var(--font-weight-medium);\\n  }\\n\\n  .feed-item-footer {\\n    display: flex;\\n    justify-content: flex-end;\\n  }\\n\\n  .feed-item-actions {\\n    display: flex;\\n    gap: var(--spacing-xs);\\n  }\\n\\n  .action-button {\\n    background: transparent;\\n    border: none;\\n    padding: var(--spacing-xs);\\n    cursor: pointer;\\n    transition: all 0.2s ease;\\n    border-radius: 4px;\\n  }\\n\\n  .action-button:hover {\\n    background-color: var(--background-tertiary);\\n  }\\n\\n  .action-icon {\\n    width: 14px;\\n    height: 14px;\\n    color: var(--text-secondary);\\n  }\\n\\n  .action-button:hover .action-icon {\\n    color: var(--text-accent);\\n  }\\n</style>"],"names":[],"mappings":"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"}`
};
const MessageCard = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let { message } = $$props;
  createEventDispatcher();
  if ($$props.message === void 0 && $$bindings.message && message !== void 0) $$bindings.message(message);
  $$result.css.add(css$2);
  return `<div class="feed-item svelte-129e5w6"><div class="feed-item-header svelte-129e5w6"><div class="feed-item-avatar svelte-129e5w6"><div class="avatar-placeholder svelte-129e5w6">${escape(message.channel.charAt(0).toUpperCase())}</div></div> <div class="feed-item-meta svelte-129e5w6"><div class="feed-item-source svelte-129e5w6">${escape(message.channel)}</div> <div class="feed-item-timestamp svelte-129e5w6">${escape(new Date(message.timestamp).toLocaleTimeString())}</div></div> <div class="feed-item-badges svelte-129e5w6"><span class="${"tag tag-" + escape(message.threatLevel.toLowerCase(), true) + " svelte-129e5w6"}">${escape(message.threatLevel)}</span> <span class="relevance-score svelte-129e5w6">${escape(message.relevanceScore)}%</span></div></div> <div class="feed-item-body svelte-129e5w6"><p class="feed-item-content svelte-129e5w6">${escape(message.content)}</p> ${message.sentiment ? `<div class="feed-item-sentiment svelte-129e5w6"><span class="${"sentiment-label sentiment-" + escape(message.sentiment.label, true) + " svelte-129e5w6"}">${escape(message.sentiment.label)}</span> <span class="sentiment-score svelte-129e5w6">${escape(Math.round(message.sentiment.score * 100))}%</span></div>` : ``} ${message.location ? `<div class="feed-item-location svelte-129e5w6"><svg class="location-icon svelte-129e5w6" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"></path></svg> <span class="location-text svelte-129e5w6">${escape(message.location.country)}${message.location.region ? `, ${escape(message.location.region)}` : ``}</span></div>` : ``} ${message.entities && message.entities.length > 0 ? `<div class="feed-item-entities svelte-129e5w6">${each(message.entities, (entity) => {
    return `<span class="entity-tag svelte-129e5w6">${escape(entity)}</span>`;
  })}</div>` : ``}</div> <div class="feed-item-footer svelte-129e5w6"><div class="feed-item-actions svelte-129e5w6"><button class="action-button svelte-129e5w6" title="Archive message" data-svelte-h="svelte-lvalb9"><svg class="action-icon svelte-129e5w6" viewBox="0 0 24 24" fill="currentColor"><path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM6.24 5h11.52l.83 1H5.42l.82-1zM5 19V8h14v11H5z"></path><path d="M9 10v2h6v-2H9z"></path></svg></button> <button class="action-button svelte-129e5w6" title="Flag for review" data-svelte-h="svelte-1ki4zhl"><svg class="action-icon svelte-129e5w6" viewBox="0 0 24 24" fill="currentColor"><path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z"></path></svg></button> <button class="action-button svelte-129e5w6" title="Share message" data-svelte-h="svelte-1rxc2r1"><svg class="action-icon svelte-129e5w6" viewBox="0 0 24 24" fill="currentColor"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"></path></svg></button></div></div> </div>`;
});
const css$1 = {
  code: ".telegram-feed.svelte-18gt6ct.svelte-18gt6ct{width:100%;max-width:800px;margin:0 auto;padding:var(--spacing-lg)}.feed-header.svelte-18gt6ct.svelte-18gt6ct{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:var(--spacing-lg);gap:var(--spacing-md)}.feed-title.svelte-18gt6ct h1.svelte-18gt6ct{margin:0 0 var(--spacing-sm) 0;font-size:var(--font-size-xl);font-weight:var(--font-weight-bold);color:var(--text-primary)}.feed-stats.svelte-18gt6ct.svelte-18gt6ct{display:flex;gap:var(--spacing-lg);flex-shrink:0}.stat.svelte-18gt6ct.svelte-18gt6ct{display:flex;flex-direction:column;align-items:flex-end;gap:2px}.stat-value.svelte-18gt6ct.svelte-18gt6ct{font-size:var(--font-size-lg);font-weight:var(--font-weight-bold);color:var(--text-accent)}.stat-label.svelte-18gt6ct.svelte-18gt6ct{font-size:var(--font-size-xs);font-weight:var(--font-weight-medium);color:var(--text-secondary);text-transform:uppercase}.feed-content.svelte-18gt6ct.svelte-18gt6ct{min-height:400px}.empty-state.svelte-18gt6ct.svelte-18gt6ct{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:var(--spacing-xxl)}.empty-icon.svelte-18gt6ct.svelte-18gt6ct{font-size:3rem;margin-bottom:var(--spacing-lg);opacity:0.5}.empty-state.svelte-18gt6ct h3.svelte-18gt6ct{margin-bottom:var(--spacing-sm);color:var(--text-primary)}.empty-state.svelte-18gt6ct p.svelte-18gt6ct{color:var(--text-secondary);max-width:300px}.message-list.svelte-18gt6ct.svelte-18gt6ct{display:flex;flex-direction:column}@media(max-width: 768px){.telegram-feed.svelte-18gt6ct.svelte-18gt6ct{padding:var(--spacing-md)}.feed-header.svelte-18gt6ct.svelte-18gt6ct{flex-direction:column;gap:var(--spacing-sm)}.feed-stats.svelte-18gt6ct.svelte-18gt6ct{align-self:stretch;justify-content:space-between}.stat.svelte-18gt6ct.svelte-18gt6ct{align-items:center}}",
  map: `{"version":3,"file":"TelegramFeed.svelte","sources":["TelegramFeed.svelte"],"sourcesContent":["<script>\\n  import { onMount } from 'svelte';\\n  import { webSocketStore } from '$lib/stores/websocket';\\n  import { filterStore } from '$lib/stores/filters';\\n  import MessageCard from './MessageCard.svelte';\\n\\n  let filteredMessages = [];\\n  let wsState = null;\\n  let filterState = null;\\n\\n  // Subscribe to stores\\n  $: if (webSocketStore && filterStore) {\\n    wsState = $webSocketStore;\\n    filterState = $filterStore;\\n  }\\n\\n  // Filter messages based on current filter state\\n  $: if (wsState && filterState) {\\n    filteredMessages = wsState.messages.filter(message => {\\n      // Apply filters\\n      if (filterState.threatLevel && message.threatLevel !== filterState.threatLevel) {\\n        return false;\\n      }\\n      if (filterState.channel && message.channel !== filterState.channel) {\\n        return false;\\n      }\\n      if (filterState.minRelevance && message.relevanceScore < filterState.minRelevance) {\\n        return false;\\n      }\\n      return true;\\n    });\\n  }\\n\\n  function handleMessageAction(event) {\\n    const { action, messageId } = event.detail;\\n    console.log(\`Action: \${action} on message \${messageId}\`);\\n    \\n    if (action === 'flag') {\\n      // Add visual feedback for flag action\\n      const messageElement = document.querySelector(\`[data-message-id=\\"\${messageId}\\"]\`);\\n      if (messageElement) {\\n        messageElement.style.backgroundColor = 'rgba(249, 115, 22, 0.1)';\\n        setTimeout(() => {\\n          messageElement.style.backgroundColor = '';\\n        }, 1000);\\n      }\\n    }\\n  }\\n\\n  onMount(() => {\\n    // Initialize WebSocket connection\\n    webSocketStore.connect();\\n  });\\n<\/script>\\n\\n<div class=\\"telegram-feed\\">\\n  <div class=\\"feed-header\\">\\n    <div class=\\"feed-title\\">\\n      <h1>Live Intelligence Feed</h1>\\n      <div class=\\"status-indicator {wsState?.connected ? 'active' : 'inactive'}\\">\\n        <div class=\\"status-dot\\"></div>\\n        <span>{wsState?.connected ? 'LIVE MONITORING ACTIVE' : 'DISCONNECTED'}</span>\\n      </div>\\n    </div>\\n    <div class=\\"feed-stats\\">\\n      <div class=\\"stat\\">\\n        <span class=\\"stat-value\\">{filteredMessages.length}</span>\\n        <span class=\\"stat-label\\">Messages</span>\\n      </div>\\n      <div class=\\"stat\\">\\n        <span class=\\"stat-value\\">{wsState?.connected ? 'LIVE' : 'OFFLINE'}</span>\\n        <span class=\\"stat-label\\">Status</span>\\n      </div>\\n    </div>\\n  </div>\\n\\n  <div class=\\"feed-content panel\\">\\n    {#if filteredMessages.length === 0}\\n      <div class=\\"empty-state\\">\\n        <div class=\\"empty-icon\\">📡</div>\\n        <h3>No messages match your filters</h3>\\n        <p>Adjust your filters or wait for new intelligence to arrive.</p>\\n      </div>\\n    {:else}\\n      <div class=\\"message-list\\">\\n        {#each filteredMessages as message (message.id)}\\n          <div data-message-id={message.id}>\\n            <MessageCard {message} on:action={handleMessageAction} />\\n          </div>\\n        {/each}\\n      </div>\\n    {/if}\\n  </div>\\n</div>\\n\\n<style>\\n  .telegram-feed {\\n    width: 100%;\\n    max-width: 800px;\\n    margin: 0 auto;\\n    padding: var(--spacing-lg);\\n  }\\n\\n  .feed-header {\\n    display: flex;\\n    justify-content: space-between;\\n    align-items: flex-start;\\n    margin-bottom: var(--spacing-lg);\\n    gap: var(--spacing-md);\\n  }\\n\\n  .feed-title h1 {\\n    margin: 0 0 var(--spacing-sm) 0;\\n    font-size: var(--font-size-xl);\\n    font-weight: var(--font-weight-bold);\\n    color: var(--text-primary);\\n  }\\n\\n  .feed-stats {\\n    display: flex;\\n    gap: var(--spacing-lg);\\n    flex-shrink: 0;\\n  }\\n\\n  .stat {\\n    display: flex;\\n    flex-direction: column;\\n    align-items: flex-end;\\n    gap: 2px;\\n  }\\n\\n  .stat-value {\\n    font-size: var(--font-size-lg);\\n    font-weight: var(--font-weight-bold);\\n    color: var(--text-accent);\\n  }\\n\\n  .stat-label {\\n    font-size: var(--font-size-xs);\\n    font-weight: var(--font-weight-medium);\\n    color: var(--text-secondary);\\n    text-transform: uppercase;\\n  }\\n\\n  .feed-content {\\n    min-height: 400px;\\n  }\\n\\n  .empty-state {\\n    display: flex;\\n    flex-direction: column;\\n    align-items: center;\\n    justify-content: center;\\n    text-align: center;\\n    padding: var(--spacing-xxl);\\n  }\\n\\n  .empty-icon {\\n    font-size: 3rem;\\n    margin-bottom: var(--spacing-lg);\\n    opacity: 0.5;\\n  }\\n\\n  .empty-state h3 {\\n    margin-bottom: var(--spacing-sm);\\n    color: var(--text-primary);\\n  }\\n\\n  .empty-state p {\\n    color: var(--text-secondary);\\n    max-width: 300px;\\n  }\\n\\n  .message-list {\\n    display: flex;\\n    flex-direction: column;\\n  }\\n\\n  /* Responsive design */\\n  @media (max-width: 768px) {\\n    .telegram-feed {\\n      padding: var(--spacing-md);\\n    }\\n\\n    .feed-header {\\n      flex-direction: column;\\n      gap: var(--spacing-sm);\\n    }\\n\\n    .feed-stats {\\n      align-self: stretch;\\n      justify-content: space-between;\\n    }\\n\\n    .stat {\\n      align-items: center;\\n    }\\n  }\\n</style> "],"names":[],"mappings":"AAgGE,4CAAe,CACb,KAAK,CAAE,IAAI,CACX,SAAS,CAAE,KAAK,CAChB,MAAM,CAAE,CAAC,CAAC,IAAI,CACd,OAAO,CAAE,IAAI,YAAY,CAC3B,CAEA,0CAAa,CACX,OAAO,CAAE,IAAI,CACb,eAAe,CAAE,aAAa,CAC9B,WAAW,CAAE,UAAU,CACvB,aAAa,CAAE,IAAI,YAAY,CAAC,CAChC,GAAG,CAAE,IAAI,YAAY,CACvB,CAEA,0BAAW,CAAC,iBAAG,CACb,MAAM,CAAE,CAAC,CAAC,CAAC,CAAC,IAAI,YAAY,CAAC,CAAC,CAAC,CAC/B,SAAS,CAAE,IAAI,cAAc,CAAC,CAC9B,WAAW,CAAE,IAAI,kBAAkB,CAAC,CACpC,KAAK,CAAE,IAAI,cAAc,CAC3B,CAEA,yCAAY,CACV,OAAO,CAAE,IAAI,CACb,GAAG,CAAE,IAAI,YAAY,CAAC,CACtB,WAAW,CAAE,CACf,CAEA,mCAAM,CACJ,OAAO,CAAE,IAAI,CACb,cAAc,CAAE,MAAM,CACtB,WAAW,CAAE,QAAQ,CACrB,GAAG,CAAE,GACP,CAEA,yCAAY,CACV,SAAS,CAAE,IAAI,cAAc,CAAC,CAC9B,WAAW,CAAE,IAAI,kBAAkB,CAAC,CACpC,KAAK,CAAE,IAAI,aAAa,CAC1B,CAEA,yCAAY,CACV,SAAS,CAAE,IAAI,cAAc,CAAC,CAC9B,WAAW,CAAE,IAAI,oBAAoB,CAAC,CACtC,KAAK,CAAE,IAAI,gBAAgB,CAAC,CAC5B,cAAc,CAAE,SAClB,CAEA,2CAAc,CACZ,UAAU,CAAE,KACd,CAEA,0CAAa,CACX,OAAO,CAAE,IAAI,CACb,cAAc,CAAE,MAAM,CACtB,WAAW,CAAE,MAAM,CACnB,eAAe,CAAE,MAAM,CACvB,UAAU,CAAE,MAAM,CAClB,OAAO,CAAE,IAAI,aAAa,CAC5B,CAEA,yCAAY,CACV,SAAS,CAAE,IAAI,CACf,aAAa,CAAE,IAAI,YAAY,CAAC,CAChC,OAAO,CAAE,GACX,CAEA,2BAAY,CAAC,iBAAG,CACd,aAAa,CAAE,IAAI,YAAY,CAAC,CAChC,KAAK,CAAE,IAAI,cAAc,CAC3B,CAEA,2BAAY,CAAC,gBAAE,CACb,KAAK,CAAE,IAAI,gBAAgB,CAAC,CAC5B,SAAS,CAAE,KACb,CAEA,2CAAc,CACZ,OAAO,CAAE,IAAI,CACb,cAAc,CAAE,MAClB,CAGA,MAAO,YAAY,KAAK,CAAE,CACxB,4CAAe,CACb,OAAO,CAAE,IAAI,YAAY,CAC3B,CAEA,0CAAa,CACX,cAAc,CAAE,MAAM,CACtB,GAAG,CAAE,IAAI,YAAY,CACvB,CAEA,yCAAY,CACV,UAAU,CAAE,OAAO,CACnB,eAAe,CAAE,aACnB,CAEA,mCAAM,CACJ,WAAW,CAAE,MACf,CACF"}`
};
const TelegramFeed = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  let $filterStore, $$unsubscribe_filterStore;
  let $webSocketStore, $$unsubscribe_webSocketStore;
  $$unsubscribe_filterStore = subscribe(filterStore, (value) => $filterStore = value);
  $$unsubscribe_webSocketStore = subscribe(webSocketStore, (value) => $webSocketStore = value);
  let filteredMessages2 = [];
  let wsState = null;
  let filterState2 = null;
  $$result.css.add(css$1);
  {
    if (webSocketStore && filterStore) {
      wsState = $webSocketStore;
      filterState2 = $filterStore;
    }
  }
  {
    if (wsState && filterState2) {
      filteredMessages2 = wsState.messages.filter((message) => {
        if (filterState2.threatLevel && message.threatLevel !== filterState2.threatLevel) {
          return false;
        }
        if (filterState2.channel && message.channel !== filterState2.channel) {
          return false;
        }
        if (filterState2.minRelevance && message.relevanceScore < filterState2.minRelevance) {
          return false;
        }
        return true;
      });
    }
  }
  $$unsubscribe_filterStore();
  $$unsubscribe_webSocketStore();
  return `<div class="telegram-feed svelte-18gt6ct"><div class="feed-header svelte-18gt6ct"><div class="feed-title svelte-18gt6ct"><h1 class="svelte-18gt6ct" data-svelte-h="svelte-nfj8an">Live Intelligence Feed</h1> <div class="${"status-indicator " + escape(wsState?.connected ? "active" : "inactive", true)}"><div class="status-dot"></div> <span>${escape(wsState?.connected ? "LIVE MONITORING ACTIVE" : "DISCONNECTED")}</span></div></div> <div class="feed-stats svelte-18gt6ct"><div class="stat svelte-18gt6ct"><span class="stat-value svelte-18gt6ct">${escape(filteredMessages2.length)}</span> <span class="stat-label svelte-18gt6ct" data-svelte-h="svelte-1vhqrva">Messages</span></div> <div class="stat svelte-18gt6ct"><span class="stat-value svelte-18gt6ct">${escape(wsState?.connected ? "LIVE" : "OFFLINE")}</span> <span class="stat-label svelte-18gt6ct" data-svelte-h="svelte-1nqewxk">Status</span></div></div></div> <div class="feed-content panel svelte-18gt6ct">${filteredMessages2.length === 0 ? `<div class="empty-state svelte-18gt6ct" data-svelte-h="svelte-5mg1so"><div class="empty-icon svelte-18gt6ct">📡</div> <h3 class="svelte-18gt6ct">No messages match your filters</h3> <p class="svelte-18gt6ct">Adjust your filters or wait for new intelligence to arrive.</p></div>` : `<div class="message-list svelte-18gt6ct">${each(filteredMessages2, (message) => {
    return `<div${add_attribute("data-message-id", message.id, 0)}>${validate_component(MessageCard, "MessageCard").$$render($$result, { message }, {}, {})} </div>`;
  })}</div>`}</div> </div>`;
});
const css = {
  code: ".page-container.svelte-cfloie{min-height:100vh;background-color:var(--background-primary);color:var(--text-primary)}body{margin:0;padding:0;background:var(--osint-bg-primary);color:var(--osint-text-primary)}",
  map: `{"version":3,"file":"+page.svelte","sources":["+page.svelte"],"sourcesContent":["<script lang=\\"ts\\">\\n  import { onMount } from 'svelte';\\n  import TelegramFeed from '$lib/components/TelegramFeed.svelte';\\n  import { websocketStore } from '$lib/stores/websocket';\\n  import { filterStore } from '$lib/stores/filters';\\n\\n  onMount(() => {\\n    console.log('🔴 Telegram Intelligence Feed initialized');\\n    \\n    // Initialize WebSocket connection for real-time updates\\n    websocketStore.connect('ws://localhost:8000/ws/telegram');\\n    \\n    // Set up initial filter preferences\\n    filterStore.resetFilters();\\n  });\\n<\/script>\\n\\n<svelte:head>\\n  <title>Live Intelligence Feed - GeopolMonitor</title>\\n  <meta name=\\"description\\" content=\\"Real-time geopolitical intelligence monitoring dashboard\\" />\\n</svelte:head>\\n\\n<div class=\\"page-container\\">\\n  <TelegramFeed />\\n</div>\\n\\n<style>\\n  .page-container {\\n    min-height: 100vh;\\n    background-color: var(--background-primary);\\n    color: var(--text-primary);\\n  }\\n\\n  :global(body) {\\n    margin: 0;\\n    padding: 0;\\n    background: var(--osint-bg-primary);\\n    color: var(--osint-text-primary);\\n  }\\n</style> "],"names":[],"mappings":"AA2BE,6BAAgB,CACd,UAAU,CAAE,KAAK,CACjB,gBAAgB,CAAE,IAAI,oBAAoB,CAAC,CAC3C,KAAK,CAAE,IAAI,cAAc,CAC3B,CAEQ,IAAM,CACZ,MAAM,CAAE,CAAC,CACT,OAAO,CAAE,CAAC,CACV,UAAU,CAAE,IAAI,kBAAkB,CAAC,CACnC,KAAK,CAAE,IAAI,oBAAoB,CACjC"}`
};
const Page = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  $$result.css.add(css);
  return `${$$result.head += `<!-- HEAD_svelte-negssw_START -->${$$result.title = `<title>Live Intelligence Feed - GeopolMonitor</title>`, ""}<meta name="description" content="Real-time geopolitical intelligence monitoring dashboard"><!-- HEAD_svelte-negssw_END -->`, ""} <div class="page-container svelte-cfloie">${validate_component(TelegramFeed, "TelegramFeed").$$render($$result, {}, {}, {})} </div>`;
});
export {
  Page as default
};
//# sourceMappingURL=_page.svelte.js.map
