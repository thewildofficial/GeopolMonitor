import { writable, derived } from 'svelte/store';
import type { FilterState, TelegramMessage } from '$lib/types';
import { telegramMessages } from './websocket';

// Filter state store
export const filterState = writable<FilterState>({
  relevanceThreshold: 0.5,
  threatLevels: new Set(['HIGH', 'MEDIUM', 'LOW']),
  countries: new Set(),
  channels: new Set(),
  dateRange: {
    start: null,
    end: null
  }
});

// Search query store
export const searchQuery = writable<string>('');

// Filtered messages (derived from telegram messages and filters)
export const filteredMessages = derived(
  [telegramMessages, filterState, searchQuery],
  ([$messages, $filters, $search]) => {
    let filtered = $messages;

    // Apply relevance threshold filter
    filtered = filtered.filter(msg => msg.relevanceScore >= $filters.relevanceThreshold);

    // Apply threat level filter
    if ($filters.threatLevels.size > 0) {
      filtered = filtered.filter(msg => $filters.threatLevels.has(msg.threatLevel));
    }

    // Apply country filter
    if ($filters.countries.size > 0) {
      filtered = filtered.filter(msg => 
        msg.location && $filters.countries.has(msg.location.country)
      );
    }

    // Apply channel filter
    if ($filters.channels.size > 0) {
      filtered = filtered.filter(msg => $filters.channels.has(msg.channel));
    }

    // Apply date range filter
    if ($filters.dateRange.start || $filters.dateRange.end) {
      filtered = filtered.filter(msg => {
        const msgDate = new Date(msg.timestamp);
        const inRange = (!$filters.dateRange.start || msgDate >= $filters.dateRange.start) &&
                       (!$filters.dateRange.end || msgDate <= $filters.dateRange.end);
        return inRange;
      });
    }

    // Apply search query filter
    if ($search.trim()) {
      const searchLower = $search.toLowerCase();
      filtered = filtered.filter(msg => 
        msg.content.toLowerCase().includes(searchLower) ||
        msg.channel.toLowerCase().includes(searchLower) ||
        msg.entities.some(entity => entity.toLowerCase().includes(searchLower))
      );
    }

    return filtered;
  }
);

// Statistics derived from filtered messages
export const messageStats = derived(
  filteredMessages,
  ($filtered) => {
    const total = $filtered.length;
    const highThreat = $filtered.filter(msg => msg.threatLevel === 'HIGH').length;
    const mediumThreat = $filtered.filter(msg => msg.threatLevel === 'MEDIUM').length;
    const lowThreat = $filtered.filter(msg => msg.threatLevel === 'LOW').length;

    // Country breakdown
    const countryCounts: { [key: string]: number } = {};
    $filtered.forEach(msg => {
      if (msg.location?.country) {
        countryCounts[msg.location.country] = (countryCounts[msg.location.country] || 0) + 1;
      }
    });

    // Channel breakdown
    const channelCounts: { [key: string]: number } = {};
    $filtered.forEach(msg => {
      channelCounts[msg.channel] = (channelCounts[msg.channel] || 0) + 1;
    });

    // Average sentiment
    const avgSentiment = total > 0 
      ? $filtered.reduce((sum, msg) => sum + msg.sentiment.score, 0) / total 
      : 0;

    // Average relevance
    const avgRelevance = total > 0 
      ? $filtered.reduce((sum, msg) => sum + msg.relevanceScore, 0) / total 
      : 0;

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
      recentActivity: $filtered.filter(msg => 
        new Date(msg.timestamp) > new Date(Date.now() - 60 * 60 * 1000)
      ).length
    };
  }
);

// Available filter options (derived from all messages)
export const filterOptions = derived(
  telegramMessages,
  ($messages) => {
    const countries = new Set<string>();
    const channels = new Set<string>();

    $messages.forEach(msg => {
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

// Filter actions
export const filterActions = {
  // Update relevance threshold
  setRelevanceThreshold: (threshold: number) => {
    filterState.update(state => ({
      ...state,
      relevanceThreshold: Math.max(0, Math.min(1, threshold))
    }));
  },

  // Toggle threat level
  toggleThreatLevel: (level: 'HIGH' | 'MEDIUM' | 'LOW') => {
    filterState.update(state => {
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
  toggleCountry: (country: string) => {
    filterState.update(state => {
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
  toggleChannel: (channel: string) => {
    filterState.update(state => {
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
  setDateRange: (start: Date | null, end: Date | null) => {
    filterState.update(state => ({
      ...state,
      dateRange: { start, end }
    }));
  },

  // Clear all filters
  clearFilters: () => {
    filterState.set({
      relevanceThreshold: 0,
      threatLevels: new Set(['HIGH', 'MEDIUM', 'LOW']),
      countries: new Set(),
      channels: new Set(),
      dateRange: { start: null, end: null }
    });
    searchQuery.set('');
  }
}; 