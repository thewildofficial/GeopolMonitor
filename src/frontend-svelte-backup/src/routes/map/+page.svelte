<script>
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import GlobalMap from '$lib/components/GlobalMap.svelte';

	// Mock data for demonstration
	const mockMessages = writable([
		{
			id: 'msg1',
			content: 'Regional tensions escalating in Eastern Europe as military exercises continue near border areas. Intelligence sources report increased activity.',
			timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 min ago
			relevance_score: 0.92,
			channel_name: 'IntelAlerts',
			location: {
				country: 'Ukraine',
				coordinates: [30.5234, 50.4501] // Kyiv
			},
			sentiment_score: -0.7,
			entities: ['Ukraine', 'Russia', 'Military', 'Border']
		},
		{
			id: 'msg2',
			content: 'Economic indicators show positive trends in Southeast Asian markets with tech sector leading growth initiatives.',
			timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(), // 45 min ago
			relevance_score: 0.76,
			channel_name: 'GeopoliticsToday',
			location: {
				country: 'Singapore',
				coordinates: [103.8198, 1.3521] // Singapore
			},
			sentiment_score: 0.6,
			entities: ['Singapore', 'Economy', 'Technology', 'Growth']
		},
		{
			id: 'msg3',
			content: 'Diplomatic summit scheduled in Geneva to address recent trade agreements and regional cooperation frameworks.',
			timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(), // 15 min ago
			relevance_score: 0.85,
			channel_name: 'DiplomacyWatch',
			location: {
				country: 'Switzerland',
				coordinates: [6.1432, 46.2044] // Geneva
			},
			sentiment_score: 0.3,
			entities: ['Switzerland', 'Diplomacy', 'Trade', 'Summit']
		},
		{
			id: 'msg4',
			content: 'Maritime security concerns rise in strategic shipping lanes following recent incident reports from naval patrols.',
			timestamp: new Date(Date.now() - 1000 * 60 * 60).toISOString(), // 1 hour ago
			relevance_score: 0.88,
			channel_name: 'MaritimeIntel',
			location: {
				country: 'South China Sea',
				coordinates: [113.9213, 16.0583] // South China Sea
			},
			sentiment_score: -0.5,
			entities: ['Maritime', 'Security', 'Shipping', 'Naval']
		},
		{
			id: 'msg5',
			content: 'Energy infrastructure developments in North Africa show progress with renewable energy projects gaining momentum.',
			timestamp: new Date(Date.now() - 1000 * 60 * 90).toISOString(), // 1.5 hours ago
			relevance_score: 0.72,
			channel_name: 'EnergyWatch',
			location: {
				country: 'Morocco',
				coordinates: [-7.0926, 31.7917] // Morocco
			},
			sentiment_score: 0.8,
			entities: ['Morocco', 'Energy', 'Renewable', 'Infrastructure']
		}
	]);

	// Map filters - reactive to user interaction
	let mapFilters = {
		timeRange: '24h',
		relevanceThreshold: 0.5,
		showHeatmap: true,
		showEvents: true
	};

	let selectedRegion = null;

	// Page data
	let pageTitle = 'Global Intelligence Map';
	let pageDescription = 'Real-time visualization of geopolitical events and intelligence across the globe. Interactive heatmaps show activity density and relevance scoring.';

	onMount(() => {
		console.log('🗺️ Global Map page initialized');
		console.log('Mock messages loaded:', $mockMessages.length);
	});

	// Handler for when user selects a region on the map
	function handleRegionSelect(event) {
		selectedRegion = event.detail;
		console.log('Region selected:', selectedRegion);
	}
</script>

<svelte:head>
	<title>{pageTitle} - GeopolMonitor</title>
	<meta name="description" content={pageDescription} />
	<meta property="og:title" content="{pageTitle} - GeopolMonitor" />
	<meta property="og:description" content={pageDescription} />
	<!-- MapLibre GL CSS -->
	<link href='https://unpkg.com/maplibre-gl@latest/dist/maplibre-gl.css' rel='stylesheet' />
</svelte:head>

<style>
	.map-page {
		min-height: 100vh;
		background: var(--background-primary);
		color: var(--text-primary);
		padding: 20px;
	}

	.page-header {
		text-align: center;
		margin-bottom: 32px;
		padding: 20px 0;
		border-bottom: 1px solid var(--border-secondary);
	}

	.page-title {
		font-size: 2.5rem;
		font-weight: 700;
		margin-bottom: 12px;
		background: linear-gradient(135deg, var(--accent-primary), #4f46e5);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.page-subtitle {
		font-size: 1.1rem;
		color: var(--text-secondary);
		max-width: 600px;
		margin: 0 auto;
		line-height: 1.6;
	}

	.live-indicator {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.3);
		padding: 6px 12px;
		border-radius: 20px;
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-top: 16px;
	}

	.pulse-dot {
		width: 8px;
		height: 8px;
		background: #ef4444;
		border-radius: 50%;
		animation: pulse-animation 2s infinite;
	}

	@keyframes pulse-animation {
		0% {
			box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
		}
		70% {
			box-shadow: 0 0 0 10px rgba(239, 68, 68, 0);
		}
		100% {
			box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
		}
	}

	.map-section {
		max-width: 1400px;
		margin: 0 auto;
		background: var(--background-secondary);
		border-radius: 12px;
		padding: 24px;
		border: 1px solid var(--border-secondary);
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.map-controls {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
		padding: 16px;
		background: var(--background-primary);
		border-radius: 8px;
		border: 1px solid var(--border-secondary);
	}

	.control-group {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.control-label {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-secondary);
		margin-right: 8px;
	}

	.control-select {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		color: var(--text-primary);
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 14px;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.control-select:hover {
		border-color: var(--accent-primary);
	}

	.control-checkbox {
		display: flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
	}

	.control-checkbox input {
		margin: 0;
		cursor: pointer;
	}

	.filter-summary {
		display: flex;
		align-items: center;
		gap: 16px;
		font-size: 14px;
		color: var(--text-secondary);
	}

	.filter-badge {
		background: var(--accent-primary);
		color: var(--background-primary);
		padding: 4px 8px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 600;
	}

	.map-wrapper {
		position: relative;
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--border-secondary);
	}

	.region-info {
		margin-top: 20px;
		padding: 16px;
		background: var(--background-primary);
		border-radius: 8px;
		border: 1px solid var(--border-secondary);
	}

	.region-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--accent-primary);
		margin-bottom: 8px;
	}

	.region-details {
		color: var(--text-secondary);
		font-size: 14px;
	}

	@media (max-width: 768px) {
		.map-page {
			padding: 12px;
		}
		
		.page-title {
			font-size: 2rem;
		}
		
		.map-section {
			padding: 16px;
		}
		
		.map-controls {
			flex-direction: column;
			gap: 12px;
		}
		
		.control-group {
			flex-wrap: wrap;
			justify-content: center;
		}
	}
</style>

<div class="map-page">
	<div class="page-header">
		<h1 class="page-title">🌍 Global Intelligence Map</h1>
		<p class="page-subtitle">
			{pageDescription}
		</p>
		<div class="live-indicator">
			<div class="pulse-dot"></div>
			Real-time Monitoring Active
		</div>
	</div>

	<div class="map-section">
		<div class="map-controls">
			<div class="control-group">
				<div class="control-label">Time Range:</div>
				<select class="control-select" bind:value={mapFilters.timeRange}>
					<option value="1h">Last Hour</option>
					<option value="6h">Last 6 Hours</option>
					<option value="24h">Last 24 Hours</option>
					<option value="7d">Last 7 Days</option>
				</select>

				<div class="control-label">Min Relevance:</div>
				<select class="control-select" bind:value={mapFilters.relevanceThreshold}>
					<option value={0}>All Messages</option>
					<option value={0.3}>Low (30%+)</option>
					<option value={0.6}>Medium (60%+)</option>
					<option value={0.8}>High (80%+)</option>
				</select>
			</div>

			<div class="control-group">
				<label class="control-checkbox">
					<input type="checkbox" bind:checked={mapFilters.showHeatmap}>
					<span>Activity Heatmap</span>
				</label>

				<label class="control-checkbox">
					<input type="checkbox" bind:checked={mapFilters.showEvents}>
					<span>Event Markers</span>
				</label>
			</div>
		</div>

		<div class="filter-summary">
			<span>Active Filters:</span>
			<span class="filter-badge">Time: {mapFilters.timeRange}</span>
			<span class="filter-badge">Relevance: {Math.round(mapFilters.relevanceThreshold * 100)}%+</span>
			{#if mapFilters.showHeatmap}
				<span class="filter-badge">Heatmap: ON</span>
			{/if}
			{#if mapFilters.showEvents}
				<span class="filter-badge">Events: ON</span>
			{/if}
		</div>

		<div class="map-wrapper">
			<GlobalMap 
				messages={$mockMessages}
				bind:selectedRegion
				bind:filters={mapFilters}
				on:regionSelect={handleRegionSelect}
			/>
		</div>

		{#if selectedRegion}
			<div class="region-info">
				<div class="region-title">📍 Selected Region: {selectedRegion.name}</div>
				<div class="region-details">
					{selectedRegion.messageCount} messages • Last updated: {new Date().toLocaleTimeString()}
				</div>
			</div>
		{/if}
	</div>
</div> 