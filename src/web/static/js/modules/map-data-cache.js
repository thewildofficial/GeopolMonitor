/**
 * Map Data Cache - Manages caching of country statistics to reduce API calls
 * Implements a smart refresh strategy with time-based expiration
 */

export class MapDataCache {
    constructor(options = {}) {
        // Cache settings with defaults
        this.ttl = options.ttl || 5 * 60 * 1000; // Default: 5 minutes TTL
        this.maxAge = options.maxAge || 30 * 60 * 1000; // Default: 30 minutes max age
        this.staleWhileRevalidate = options.staleWhileRevalidate !== false; // Default: true
        
        // Initialize cache storage
        this.cache = {
            countryStats: null,
            lastFetched: null,
            isRefreshing: false
        };
        
        // Debug mode for development
        this.debug = options.debug || false;
    }
    
    /**
     * Get country statistics from cache or API
     * @param {Object} options - Query parameters for the API call
     * @param {Function} fetchCallback - Actual API fetch function to call if cache is stale
     * @returns {Promise<Object>} - Country statistics data
     */
    async getCountryStats(options = {}, fetchCallback) {
        const now = Date.now();
        const isStale = !this.cache.lastFetched || (now - this.cache.lastFetched) > this.ttl;
        const isExpired = !this.cache.lastFetched || (now - this.cache.lastFetched) > this.maxAge;
        
        // If we have valid cache data and it's not expired or stale, return it immediately
        if (this.cache.countryStats && !isExpired && !isStale) {
            this.log('Using fresh cache data');
            return this.cache.countryStats;
        }
        
        // If data is stale but not expired, and staleWhileRevalidate is enabled,
        // refresh in the background but still return cached data
        if (this.cache.countryStats && !isExpired && isStale && this.staleWhileRevalidate) {
            this.log('Using stale cache data while refreshing');
            if (!this.cache.isRefreshing) {
                this.refreshCache(options, fetchCallback);
            }
            return this.cache.countryStats;
        }
        
        // Otherwise fetch new data
        return await this.refreshCache(options, fetchCallback);
    }
    
    /**
     * Refresh the cache with fresh data
     * @private
     */
    async refreshCache(options = {}, fetchCallback) {
        if (this.cache.isRefreshing) {
            this.log('Refresh already in progress, waiting...');
            // Wait for existing refresh to complete
            while (this.cache.isRefreshing) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            return this.cache.countryStats;
        }
        
        try {
            this.cache.isRefreshing = true;
            this.log('Fetching fresh data from API');
            
            const freshData = await fetchCallback(options);
            this.cache.countryStats = freshData;
            this.cache.lastFetched = Date.now();
            
            return freshData;
        } catch (error) {
            this.log('Error refreshing cache:', error);
            // If refresh fails but we have old data, return that
            if (this.cache.countryStats) {
                return this.cache.countryStats;
            }
            throw error;
        } finally {
            this.cache.isRefreshing = false;
        }
    }
    
    /**
     * Invalidate the cache
     */
    invalidate() {
        this.log('Cache invalidated');
        this.cache.countryStats = null;
        this.cache.lastFetched = null;
    }
    
    /**
     * Check if cache is valid
     */
    isValid() {
        if (!this.cache.countryStats || !this.cache.lastFetched) {
            return false;
        }
        
        const now = Date.now();
        return (now - this.cache.lastFetched) <= this.maxAge;
    }
    
    /**
     * Get cache status information
     */
    getStatus() {
        if (!this.cache.lastFetched) {
            return {
                status: 'empty',
                age: null,
                isStale: true,
                isExpired: true
            };
        }
        
        const now = Date.now();
        const age = now - this.cache.lastFetched;
        const isStale = age > this.ttl;
        const isExpired = age > this.maxAge;
        
        return {
            status: isExpired ? 'expired' : isStale ? 'stale' : 'fresh',
            age: Math.round(age / 1000),
            lastFetched: new Date(this.cache.lastFetched).toISOString(),
            isStale,
            isExpired
        };
    }
    
    /**
     * Debug logging
     * @private
     */
    log(...args) {
        if (this.debug) {
            console.log('[MapDataCache]', ...args);
        }
    }
}

// Create and export a singleton instance
export const mapDataCache = new MapDataCache({
    ttl: 5 * 60 * 1000, // 5 minutes
    maxAge: 30 * 60 * 1000, // 30 minutes
    debug: false
});

export default mapDataCache;