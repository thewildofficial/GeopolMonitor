<script>
	import { onMount, onDestroy } from 'svelte';
	import { writable, derived } from 'svelte/store';
	import maplibregl from 'maplibre-gl';
	import * as turf from '@turf/turf';

	// Props
	export let messages = [];
	export let selectedRegion = null;
	export let filters = {
		timeRange: '24h',
		relevanceThreshold: 0.5,
		showHeatmap: true,
		showEvents: true
	};

	// Map and component state
	let mapContainer;
	let map;
	let heatmapLayer = null;
	let eventMarkers = [];
	let countryHeatData = new Map();
	let regionPanelVisible = false;
	let selectedCountryData = null;

	// Reactive stores
	const mapLoaded = writable(false);
	const activeRegions = writable(0);
	const todayEvents = writable(0);

	// Derived stores for map data
	const filteredMessages = derived([messages], ([$messages]) => {
		return $messages.filter(msg => {
			const relevanceScore = msg.relevance_score || 0;
			const timeThreshold = getTimeThreshold(filters.timeRange);
			const messageTime = new Date(msg.timestamp);
			
			return relevanceScore >= filters.relevanceThreshold && 
				   messageTime >= timeThreshold;
		});
	});

	const heatmapData = derived([filteredMessages], ([$filteredMessages]) => {
		const regionCounts = new Map();
		
		$filteredMessages.forEach(msg => {
			if (msg.location && msg.location.coordinates) {
				const [lng, lat] = msg.location.coordinates;
				const country = msg.location.country || 'Unknown';
				
				if (!regionCounts.has(country)) {
					regionCounts.set(country, {
						count: 0,
						center: [lng, lat],
						messages: []
					});
				}
				
				const data = regionCounts.get(country);
				data.count++;
				data.messages.push(msg);
			}
		});
		
		return regionCounts;
	});

	// Helper functions
	function getTimeThreshold(range) {
		const now = new Date();
		switch (range) {
			case '1h': return new Date(now.getTime() - 60 * 60 * 1000);
			case '6h': return new Date(now.getTime() - 6 * 60 * 60 * 1000);
			case '24h': return new Date(now.getTime() - 24 * 60 * 60 * 1000);
			case '7d': return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
			default: return new Date(now.getTime() - 24 * 60 * 60 * 1000);
		}
	}

	function getRelevanceColor(score) {
		if (score >= 0.8) return '#ef4444'; // High - Red
		if (score >= 0.6) return '#f97316'; // Medium - Orange
		return '#22c55e'; // Low - Green
	}

	function createHeatmapExpression(data) {
		const maxCount = Math.max(...Array.from(data.values()).map(d => d.count));
		
		return [
			'interpolate',
			['linear'],
			['heatmap-density'],
			0, 'rgba(0, 0, 255, 0)',
			0.2, 'rgba(0, 150, 255, 0.2)',
			0.4, 'rgba(0, 255, 150, 0.4)',
			0.6, 'rgba(255, 255, 0, 0.6)',
			0.8, 'rgba(255, 150, 0, 0.8)',
			1, 'rgba(255, 0, 0, 1)'
		];
	}

	// Map lifecycle functions
	onMount(async () => {
		// Initialize MapLibre GL JS map
		map = new maplibregl.Map({
			container: mapContainer,
			style: {
				version: 8,
				sources: {
					'raster-tiles': {
						type: 'raster',
						tiles: [
							'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
						],
						tileSize: 256,
						attribution: '© OpenStreetMap contributors'
					}
				},
				layers: [
					{
						id: 'background',
						type: 'background',
						paint: {
							'background-color': '#0f172a' // Dark background for intelligence theme
						}
					},
					{
						id: 'raster-layer',
						type: 'raster',
						source: 'raster-tiles',
						paint: {
							'raster-opacity': 0.7
						}
					}
				]
			},
			center: [0, 20],
			zoom: 2,
			minZoom: 1,
			maxZoom: 10
		});

		// Add map controls
		map.addControl(new maplibregl.NavigationControl(), 'top-right');
		map.addControl(new maplibregl.FullscreenControl(), 'top-right');

		// Wait for map to load
		map.on('load', () => {
			mapLoaded.set(true);
			initializeHeatmapLayer();
			updateMapData();
		});

		// Handle country clicks
		map.on('click', async (e) => {
			const features = map.queryRenderedFeatures(e.point);
			if (features.length > 0) {
				await handleCountryClick(e.lngLat, features[0]);
			}
		});

		// Update cursor on hover
		map.on('mouseenter', 'countries-fill', () => {
			map.getCanvas().style.cursor = 'pointer';
		});
		
		map.on('mouseleave', 'countries-fill', () => {
			map.getCanvas().style.cursor = '';
		});
	});

	onDestroy(() => {
		if (map) {
			map.remove();
		}
	});

	function initializeHeatmapLayer() {
		// Add country boundaries source
		map.addSource('countries', {
			type: 'vector',
			url: 'https://api.maptiler.com/tiles/countries/tiles.json?key=YOUR_API_KEY' // Replace with actual key
		});

		// Add countries fill layer
		map.addLayer({
			id: 'countries-fill',
			type: 'fill',
			source: 'countries',
			'source-layer': 'countries',
			paint: {
				'fill-color': [
					'case',
					['has', 'activity_level'],
					[
						'interpolate',
						['linear'],
						['get', 'activity_level'],
						0, '#1e293b',
						1, '#334155',
						5, '#475569',
						10, '#64748b',
						20, '#94a3b8'
					],
					'#1e293b'
				],
				'fill-opacity': 0.8
			}
		});

		// Add countries border layer
		map.addLayer({
			id: 'countries-border',
			type: 'line',
			source: 'countries',
			'source-layer': 'countries',
			paint: {
				'line-color': '#00d9ff',
				'line-width': 0.5,
				'line-opacity': 0.6
			}
		});
	}

	async function updateMapData() {
		if (!map || !$mapLoaded) return;

		// Clear existing markers
		eventMarkers.forEach(marker => marker.remove());
		eventMarkers = [];

		// Update heatmap data
		const data = $heatmapData;
		activeRegions.set(data.size);
		todayEvents.set($filteredMessages.length);

		// Add event markers
		if (filters.showEvents) {
			$filteredMessages.forEach(message => {
				if (message.location && message.location.coordinates) {
					addEventMarker(message);
				}
			});
		}

		// Update country activity levels
		if (filters.showHeatmap) {
			updateCountryHeatmap(data);
		}
	}

	function addEventMarker(message) {
		const [lng, lat] = message.location.coordinates;
		const relevanceColor = getRelevanceColor(message.relevance_score || 0);
		
		// Create custom marker element
		const markerEl = document.createElement('div');
		markerEl.className = 'event-marker';
		markerEl.style.cssText = `
			width: 12px;
			height: 12px;
			border-radius: 50%;
			background: ${relevanceColor};
			border: 2px solid #fff;
			box-shadow: 0 2px 4px rgba(0,0,0,0.3);
			cursor: pointer;
			animation: pulse 2s infinite;
		`;

		// Create popup content
		const popup = new maplibregl.Popup({ offset: 15 })
			.setHTML(`
				<div class="event-popup">
					<div class="event-header">
						<span class="relevance-badge" style="background: ${relevanceColor}">
							${Math.round((message.relevance_score || 0) * 100)}%
						</span>
						<span class="event-time">${new Date(message.timestamp).toLocaleTimeString()}</span>
					</div>
					<div class="event-content">
						<strong>${message.location.country}</strong>
						<p>${message.content.substring(0, 150)}...</p>
					</div>
					<div class="event-source">
						Source: ${message.channel_name || 'Unknown'}
					</div>
				</div>
			`);

		// Add marker to map
		const marker = new maplibregl.Marker(markerEl)
			.setLngLat([lng, lat])
			.setPopup(popup)
			.addTo(map);

		eventMarkers.push(marker);
	}

	function updateCountryHeatmap(data) {
		// This would typically update the country fill colors based on activity
		// Implementation depends on having country boundary data
		console.log('Updating heatmap with data:', data);
	}

	async function handleCountryClick(lngLat, feature) {
		// Get country data from click
		const country = feature.properties?.name || 'Unknown';
		const countryData = $heatmapData.get(country);
		
		if (countryData) {
			selectedCountryData = {
				name: country,
				messageCount: countryData.count,
				messages: countryData.messages.slice(0, 10), // Show top 10
				coordinates: lngLat
			};
			regionPanelVisible = true;
		}
	}

	function closeRegionPanel() {
		regionPanelVisible = false;
		selectedCountryData = null;
	}

	// React to data changes
	$: if (map && $mapLoaded) {
		updateMapData();
	}
</script>

<style>
	.map-container {
		position: relative;
		width: 100%;
		height: 600px;
		border-radius: 8px;
		overflow: hidden;
		background: var(--background-primary);
		border: 1px solid var(--border-secondary);
	}

	.map-stats {
		position: absolute;
		top: 16px;
		left: 16px;
		z-index: 10;
		background: rgba(15, 23, 42, 0.9);
		backdrop-filter: blur(8px);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 16px;
		color: var(--text-primary);
		min-width: 200px;
	}

	.stat-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin: 8px 0;
	}

	.stat-label {
		font-size: 14px;
		color: var(--text-secondary);
	}

	.stat-value {
		font-size: 18px;
		font-weight: 600;
		color: var(--accent-primary);
	}

	.map-filters {
		position: absolute;
		top: 16px;
		right: 16px;
		z-index: 10;
		background: rgba(15, 23, 42, 0.9);
		backdrop-filter: blur(8px);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 16px;
		color: var(--text-primary);
	}

	.filter-group {
		margin: 12px 0;
	}

	.filter-group label {
		display: block;
		font-size: 12px;
		color: var(--text-secondary);
		margin-bottom: 4px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.filter-select {
		width: 100%;
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		color: var(--text-primary);
		padding: 6px 8px;
		border-radius: 4px;
		font-size: 14px;
	}

	.filter-checkbox {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 8px 0;
	}

	.region-panel {
		position: absolute;
		bottom: 16px;
		left: 16px;
		right: 16px;
		z-index: 10;
		background: rgba(15, 23, 42, 0.95);
		backdrop-filter: blur(8px);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 20px;
		color: var(--text-primary);
		max-height: 300px;
		overflow-y: auto;
	}

	.region-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;
		padding-bottom: 12px;
		border-bottom: 1px solid var(--border-secondary);
	}

	.region-title {
		font-size: 18px;
		font-weight: 600;
		color: var(--accent-primary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
		border-radius: 4px;
		transition: all 0.2s ease;
	}

	.close-btn:hover {
		background: var(--background-secondary);
		color: var(--text-primary);
	}

	.region-messages {
		display: grid;
		gap: 12px;
	}

	.region-message {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 6px;
		padding: 12px;
		font-size: 14px;
	}

	.message-meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
		font-size: 12px;
		color: var(--text-secondary);
	}

	.relevance-badge {
		padding: 2px 6px;
		border-radius: 12px;
		font-size: 11px;
		font-weight: 600;
		color: white;
	}

	:global(.event-popup) {
		background: var(--background-primary);
		color: var(--text-primary);
		border-radius: 8px;
		padding: 16px;
		min-width: 250px;
		max-width: 350px;
		border: 1px solid var(--border-secondary);
	}

	:global(.event-header) {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border-secondary);
	}

	:global(.event-content) {
		margin: 12px 0;
	}

	:global(.event-content strong) {
		color: var(--accent-primary);
		display: block;
		margin-bottom: 8px;
	}

	:global(.event-content p) {
		line-height: 1.4;
		color: var(--text-secondary);
		margin: 0;
	}

	:global(.event-source) {
		font-size: 12px;
		color: var(--text-tertiary);
		text-align: right;
		margin-top: 8px;
		padding-top: 8px;
		border-top: 1px solid var(--border-secondary);
	}

	:global(.event-marker) {
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.7;
			transform: scale(1.1);
		}
	}

	@media (max-width: 768px) {
		.map-container {
			height: 400px;
		}
		
		.map-stats,
		.map-filters {
			position: static;
			margin: 8px;
			width: auto;
		}
		
		.region-panel {
			position: static;
			margin: 16px;
			max-height: 250px;
		}
	}
</style>

<div class="map-container">
	<div bind:this={mapContainer}></div>
	
	<!-- Map Statistics -->
	<div class="map-stats">
		<div class="stat-row">
			<span class="stat-label">Active Regions</span>
			<span class="stat-value">{$activeRegions}</span>
		</div>
		<div class="stat-row">
			<span class="stat-label">Live Events</span>
			<span class="stat-value">{$todayEvents}</span>
		</div>
	</div>

	<!-- Map Filters -->
	<div class="map-filters">
		<div class="filter-group">
			<label for="timeRange">Time Range</label>
			<select id="timeRange" class="filter-select" bind:value={filters.timeRange}>
				<option value="1h">Last Hour</option>
				<option value="6h">Last 6 Hours</option>
				<option value="24h">Last 24 Hours</option>
				<option value="7d">Last 7 Days</option>
			</select>
		</div>
		
		<div class="filter-group">
			<label for="relevanceThreshold">Min Relevance</label>
			<select id="relevanceThreshold" class="filter-select" bind:value={filters.relevanceThreshold}>
				<option value={0}>All Messages</option>
				<option value={0.3}>Low (30%+)</option>
				<option value={0.6}>Medium (60%+)</option>
				<option value={0.8}>High (80%+)</option>
			</select>
		</div>
		
		<div class="filter-checkbox">
			<input type="checkbox" id="showHeatmap" bind:checked={filters.showHeatmap}>
			<label for="showHeatmap">Activity Heatmap</label>
		</div>
		
		<div class="filter-checkbox">
			<input type="checkbox" id="showEvents" bind:checked={filters.showEvents}>
			<label for="showEvents">Event Markers</label>
		</div>
	</div>

	<!-- Region Detail Panel -->
	{#if regionPanelVisible && selectedCountryData}
		<div class="region-panel">
			<div class="region-header">
				<div class="region-title">
					📍 {selectedCountryData.name} 
					<span style="font-weight: normal; color: var(--text-secondary);">
						({selectedCountryData.messageCount} messages)
					</span>
				</div>
				<button class="close-btn" on:click={closeRegionPanel}>
					✕
				</button>
			</div>
			
			<div class="region-messages">
				{#each selectedCountryData.messages as message}
					<div class="region-message">
						<div class="message-meta">
							<span class="relevance-badge" style="background: {getRelevanceColor(message.relevance_score || 0)}">
								{Math.round((message.relevance_score || 0) * 100)}%
							</span>
							<span>{new Date(message.timestamp).toLocaleString()}</span>
						</div>
						<div class="message-content">
							{message.content.substring(0, 200)}...
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div> 