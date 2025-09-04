/**
 * MiniMap.js
 * Implements a compact map visualization for the briefing page
 * Leverages the existing Leaflet integration
 */

class MiniMap {
  constructor(options = {}) {
    // DOM element to render the map
    this.mapElement = options.mapElement || 'briefingMap';
    
    // Map settings
    this.settings = {
      initialZoom: options.initialZoom || 2,
      maxZoom: options.maxZoom || 6,
      centerLatLng: options.centerLatLng || [20, 0], // Default to roughly center of world
      tileLayer: options.tileLayer || 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      tileAttribution: options.tileAttribution || '© OpenStreetMap contributors, © CartoDB'
    };
    
    // Map instance
    this.map = null;
    
    // Layers
    this.layers = {
      hotspots: null,
      regions: null
    };
    
    // Data
    this.currentHotspots = [];
    
    // Initialize
    this.init();
  }
  
  /**
   * Initialize the mini map
   */
  init() {
    // Check if the map element exists
    const mapContainer = document.getElementById(this.mapElement);
    if (!mapContainer) {
      console.error(`Map container element #${this.mapElement} not found`);
      return;
    }
    
    // Check if Leaflet is available
    if (typeof L === 'undefined') {
      console.error('Leaflet library not loaded');
      return;
    }
    
    // Create the map
    this.map = L.map(this.mapElement, {
      center: this.settings.centerLatLng,
      zoom: this.settings.initialZoom,
      zoomControl: false,
      attributionControl: false,
      dragging: true,
      scrollWheelZoom: false
    });
    
    // Add zoom control to top right
    L.control.zoom({
      position: 'topright'
    }).addTo(this.map);
    
    // Add tile layer
    L.tileLayer(this.settings.tileLayer, {
      attribution: this.settings.tileAttribution,
      maxZoom: this.settings.maxZoom
    }).addTo(this.map);
    
    // Create layers
    this.layers.hotspots = L.layerGroup().addTo(this.map);
    this.layers.regions = L.layerGroup().addTo(this.map);
    
    // Add minimal attribution control
    L.control.attribution({
      position: 'bottomright',
      prefix: ''
    }).addAttribution('© OpenStreetMap').addTo(this.map);
    
    // Handle window resize
    window.addEventListener('resize', this.handleResize.bind(this));
    
    // Initialize empty state
    this.updateHotspots([]);
  }
  
  /**
   * Handle window resize event
   */
  handleResize() {
    if (!this.map) return;
    
    // Update map size
    this.map.invalidateSize();
  }
  
  /**
   * Update the map with hotspot data
   * @param {Array} hotspots - Array of hotspot objects with coordinates
   */
  updateHotspots(hotspots = []) {
    if (!this.map || !this.layers.hotspots) return;
    
    // Store current hotspots
    this.currentHotspots = hotspots;
    
    // Clear existing hotspots
    this.layers.hotspots.clearLayers();
    
    if (hotspots.length === 0) {
      // Show empty state if no hotspots
      this.showEmptyState();
      return;
    }
    
    // Create markers for each hotspot
    hotspots.forEach(hotspot => {
      if (!hotspot.coordinates) return;
      
      // Extract coordinates
      const { lat, lng } = hotspot.coordinates;
      if (!lat || !lng) return;
      
      // Calculate size and color based on activity level
      const activityLevel = hotspot.activity_level || 1;
      const radius = this.calcMarkerRadius(activityLevel);
      const color = this.getActivityColor(activityLevel);
      
      // Create circle marker
      const marker = L.circleMarker([lat, lng], {
        radius: radius,
        color: 'rgba(255,255,255,0.5)',
        weight: 2,
        fillColor: color,
        fillOpacity: 0.7
      }).addTo(this.layers.hotspots);
      
      // Add pulsing effect for high activity
      if (activityLevel > 7) {
        this.addPulseEffect(marker);
      }
      
      // Add tooltip
      marker.bindTooltip(`
        <div class="map-tooltip">
          <div class="tooltip-header">
            <strong>${hotspot.region || 'Unknown Region'}</strong>
          </div>
          <div class="tooltip-body">
            <div>Activity Level: ${activityLevel}</div>
            <div>Articles: ${hotspot.article_count || 0}</div>
          </div>
        </div>
      `, { 
        offset: [0, -radius],
        direction: 'top'
      });
      
      // Add click handler
      marker.on('click', () => {
        this.onHotspotClick(hotspot);
      });
    });
    
    // Auto-fit map to show all hotspots
    if (hotspots.length > 0) {
      const validMarkers = hotspots
        .filter(h => h.coordinates?.lat && h.coordinates?.lng)
        .map(h => [h.coordinates.lat, h.coordinates.lng]);
      
      if (validMarkers.length > 0) {
        this.map.fitBounds(validMarkers, { 
          padding: [20, 20],
          maxZoom: 5
        });
      }
    }
  }
  
  /**
   * Calculate the radius for a hotspot marker based on activity level
   * @param {number} activityLevel - Activity level value 
   * @returns {number} Radius in pixels
   */
  calcMarkerRadius(activityLevel) {
    // Base size 5, up to 15 for highest activity
    return 5 + Math.min(10, activityLevel);
  }
  
  /**
   * Get color for a hotspot based on activity level
   * @param {number} activityLevel - Activity level value
   * @returns {string} Color code
   */
  getActivityColor(activityLevel) {
    if (activityLevel > 7) {
      return '#FF6B6B'; // High activity - red
    } else if (activityLevel > 4) {
      return '#FFDE7D'; // Medium activity - yellow
    } else {
      return '#48DBB4'; // Low activity - green
    }
  }
  
  /**
   * Add pulsing effect to a marker for high-activity regions
   * @param {L.CircleMarker} marker - The marker to animate
   */
  addPulseEffect(marker) {
    // Create a pulsing circle
    const pulseOptions = {
      color: marker.options.fillColor,
      fillColor: marker.options.fillColor,
      fillOpacity: 0.3,
      weight: 1,
      radius: marker.options.radius * 2,
      className: 'pulsing-circle'
    };
    
    // Add CSS animation class
    const pulseCircle = L.circleMarker(marker.getLatLng(), pulseOptions)
      .addTo(this.layers.hotspots);
      
    // Add CSS for animation
    if (!document.getElementById('pulse-animation-style')) {
      const style = document.createElement('style');
      style.id = 'pulse-animation-style';
      style.innerHTML = `
        .pulsing-circle {
          animation: pulse-animation 2s infinite;
        }
        
        @keyframes pulse-animation {
          0% {
            opacity: 0.6;
            transform: scale(1);
          }
          50% {
            opacity: 0.2;
          }
          100% {
            opacity: 0;
            transform: scale(2);
          }
        }
      `;
      document.head.appendChild(style);
    }
  }
  
  /**
   * Show empty state when no hotspots are available
   */
  showEmptyState() {
    // Reset view
    this.map.setView(this.settings.centerLatLng, this.settings.initialZoom);
    
    // Add empty state overlay
    const mapContainer = document.getElementById(this.mapElement);
    if (!mapContainer) return;
    
    // Check if overlay already exists
    let overlay = mapContainer.querySelector('.map-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'map-overlay';
      overlay.innerHTML = `
        <div class="map-empty-state">
          <i class="fas fa-globe-americas"></i>
          <p>No regional hotspots detected</p>
        </div>
      `;
      mapContainer.appendChild(overlay);
    } else {
      overlay.style.display = 'flex';
    }
  }
  
  /**
   * Hide empty state overlay
   */
  hideEmptyState() {
    const mapContainer = document.getElementById(this.mapElement);
    if (!mapContainer) return;
    
    const overlay = mapContainer.querySelector('.map-overlay');
    if (overlay) {
      overlay.style.display = 'none';
    }
  }
  
  /**
   * Handle hotspot click
   * @param {Object} hotspot - The clicked hotspot data
   */
  onHotspotClick(hotspot) {
    if (!hotspot.region) return;
    
    // Trigger region filter
    const event = new CustomEvent('briefing:filter:region', {
      detail: {
        region: hotspot.region
      }
    });
    
    document.dispatchEvent(event);
    
    // Find and activate the region tab
    const regionTab = document.querySelector(`.region-tab[data-region="${hotspot.region.toLowerCase()}"]`);
    if (regionTab) {
      regionTab.click();
    }
  }
  
  /**
   * Update the map when briefing data changes
   * @param {Object} briefingData - The briefing data
   */
  updateFromBriefing(briefingData) {
    if (!briefingData || !briefingData.metadata) return;
    
    const hotspots = briefingData.metadata.regional_hotspots || [];
    
    // Transform data if needed
    const formattedHotspots = hotspots.map(hotspot => {
      // Check if coordinates need conversion
      if (!hotspot.coordinates && hotspot.lat && hotspot.lng) {
        hotspot.coordinates = {
          lat: hotspot.lat,
          lng: hotspot.lng
        };
      }
      
      return hotspot;
    });
    
    this.updateHotspots(formattedHotspots);
  }
  
  /**
   * Pan the map to a specific region
   * @param {string} regionName - Name of the region 
   */
  focusOnRegion(regionName) {
    if (!regionName || !this.currentHotspots.length) return;
    
    // Find the hotspot for this region
    const hotspot = this.currentHotspots.find(h => 
      h.region && h.region.toLowerCase() === regionName.toLowerCase()
    );
    
    if (hotspot?.coordinates?.lat && hotspot?.coordinates?.lng) {
      this.map.setView(
        [hotspot.coordinates.lat, hotspot.coordinates.lng], 
        Math.min(this.settings.maxZoom, this.settings.initialZoom + 2)
      );
    }
  }
  
  /**
   * Update the map with region data
   * @param {Array} regions - Array of region objects with activity data
   */
  updateRegions(regions = []) {
    if (!this.map || !this.layers.regions) return;
    
    // Clear existing regions
    this.layers.regions.clearLayers();
    
    if (!regions || regions.length === 0) return;
    
    regions.forEach(region => {
      if (!region.coordinates) return;
      
      const { lat, lng } = region.coordinates;
      if (!lat || !lng) return;
      
      // Create region marker
      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        color: '#4A90E2',
        weight: 2,
        fillColor: '#4A90E2',
        fillOpacity: 0.4
      }).addTo(this.layers.regions);
      
      // Add tooltip
      marker.bindTooltip(`
        <div class="map-tooltip">
          <div class="tooltip-header">
            <strong>${region.name}</strong>
          </div>
          <div class="tooltip-body">
            <div>Articles: ${region.article_count || 0}</div>
          </div>
        </div>
      `);
    });
    
    // Fit map to show all regions
    if (regions.length > 0) {
      const validMarkers = regions
        .filter(r => r.coordinates?.lat && r.coordinates?.lng)
        .map(r => [r.coordinates.lat, r.coordinates.lng]);
      
      if (validMarkers.length > 0) {
        this.map.fitBounds(validMarkers, { 
          padding: [20, 20],
          maxZoom: 5
        });
      }
    }
  }
}

// Export the class
window.BriefingMiniMap = MiniMap;