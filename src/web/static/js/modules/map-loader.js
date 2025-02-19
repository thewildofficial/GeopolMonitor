import { normalizeCountry } from './countries.js';

class MapLoader {
    constructor() {
        this.cache = new Map();
        this.version = '1.0.0';
        this.baseUrl = '/static/assets/map-chunks';
    }

    async init() {
        // Initialize cache from IndexedDB
        await this.initCache();
    }

    async initCache() {
        try {
            const db = await this.openDB();
            const tx = db.transaction('mapCache', 'readonly');
            const store = tx.objectStore('mapCache');
            const cacheVersion = await store.get('version');

            if (cacheVersion?.value !== this.version) {
                // Clear cache if version mismatch
                await this.clearCache();
            } else {
                // Load cached chunks
                const chunks = await store.getAll();
                chunks.forEach(chunk => {
                    if (chunk.key !== 'version') {
                        this.cache.set(chunk.key, chunk.value);
                    }
                });
            }
        } catch (error) {
            console.warn('Failed to initialize cache:', error);
            // Proceed without cache
        }
    }

    async openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('mapData', 1);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('mapCache')) {
                    db.createObjectStore('mapCache', { keyPath: 'key' });
                }
            };
        });
    }

    async clearCache() {
        const db = await this.openDB();
        const tx = db.transaction('mapCache', 'readwrite');
        const store = tx.objectStore('mapCache');
        await store.clear();
        await store.put({ key: 'version', value: this.version });
        this.cache.clear();
    }

    async loadChunk(zoom, region) {
        const chunkKey = `${zoom}-${region}`;

        // Check memory cache first
        if (this.cache.has(chunkKey)) {
            return this.cache.get(chunkKey);
        }

        try {
            // Try to load from IndexedDB
            const db = await this.openDB();
            const tx = db.transaction('mapCache', 'readonly');
            const store = tx.objectStore('mapCache');
            const cachedChunk = await store.get(chunkKey);

            if (cachedChunk) {
                this.cache.set(chunkKey, cachedChunk.value);
                return cachedChunk.value;
            }

            // Fetch from server if not in cache
            const response = await fetch(`${this.baseUrl}/${chunkKey}.json`);
            if (!response.ok) throw new Error('Failed to fetch map chunk');

            const data = await response.json();

            // Cache the chunk
            await this.cacheChunk(chunkKey, data);

            return data;
        } catch (error) {
            console.error('Error loading map chunk:', error);
            throw error;
        }
    }

    async cacheChunk(key, data) {
        // Save to memory cache
        this.cache.set(key, data);

        // Save to IndexedDB
        try {
            const db = await this.openDB();
            const tx = db.transaction('mapCache', 'readwrite');
            const store = tx.objectStore('mapCache');
            await store.put({ key, value: data });
        } catch (error) {
            console.warn('Failed to cache chunk:', error);
        }
    }

    getRegionForCoordinates(lat, lng) {
        // Simple region calculation based on coordinates
        const latRegion = Math.floor((lat + 90) / 45);
        const lngRegion = Math.floor((lng + 180) / 45);
        return `r${latRegion}-${lngRegion}`;
    }

    getZoomLevel(mapZoom) {
        // Convert Leaflet zoom levels to our chunk zoom levels
        if (mapZoom <= 3) return 'low';
        if (mapZoom <= 5) return 'medium';
        return 'high';
    }
}

export const mapLoader = new MapLoader();