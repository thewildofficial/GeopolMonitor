<script>
	import { onMount } from 'svelte';
	import { writable } from 'svelte/store';
	import SentimentGauge from '$lib/components/SentimentGauge.svelte';
	import TrendTimeline from '$lib/components/TrendTimeline.svelte';
	import AlertPanel from '$lib/components/AlertPanel.svelte';

	// Store for mock data
	const analyticsData = writable({
		globalSentiment: -0.15,
		globalConfidence: 0.87,
		regionalSentiments: {
			'North America': { value: 0.25, confidence: 0.82 },
			'Europe': { value: -0.45, confidence: 0.91 },
			'Asia-Pacific': { value: 0.12, confidence: 0.75 },
			'Middle East': { value: -0.62, confidence: 0.88 },
			'Africa': { value: 0.08, confidence: 0.69 },
			'Latin America': { value: 0.31, confidence: 0.78 }
		},
		timelineData: [],
		stats: {
			totalMessages: 1247,
			activeChannels: 23,
			criticalAlerts: 3,
			avgProcessingTime: 1.2
		}
	});

	// Generate mock timeline data
	function generateTimelineData() {
		const data = [];
		const now = new Date();
		
		// Generate 7 days of hourly data
		for (let i = 168; i >= 0; i--) {
			const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
			
			// Create realistic sentiment patterns with regional influences
			const base = Math.sin(i / 24) * 0.2; // Daily cycle
			const weeklyTrend = Math.cos(i / 168) * 0.3; // Weekly trend
			const randomEvent = Math.random() < 0.05 ? (Math.random() - 0.5) * 0.8 : 0; // 5% chance of major event
			const noise = (Math.random() - 0.5) * 0.3; // Random variation
			
			const sentiment = Math.max(-1, Math.min(1, base + weeklyTrend + randomEvent + noise));
			const relevance = Math.random() * 0.4 + 0.6; // 0.6 to 1.0
			
			// Generate corresponding content based on sentiment
			const contents = {
				positive: [
					'Diplomatic breakthrough achieved in ongoing negotiations',
					'Economic indicators show positive regional growth',
					'Successful completion of international cooperation agreement',
					'Peace talks advance with promising developments'
				],
				negative: [
					'Tensions escalate in disputed border region',
					'Economic sanctions imposed following policy disagreement',
					'Military exercises raise concerns among neighboring states',
					'Trade dispute negotiations face significant obstacles'
				],
				neutral: [
					'Routine diplomatic meeting scheduled for next week',
					'Standard economic data released by regional authority',
					'Regular monitoring reports indicate stable conditions',
					'Ongoing discussions continue with measured progress'
				]
			};
			
			const contentType = sentiment > 0.2 ? 'positive' : sentiment < -0.2 ? 'negative' : 'neutral';
			const contentArray = contents[contentType];
			const content = contentArray[Math.floor(Math.random() * contentArray.length)];
			
			const channels = ['IntelAlerts', 'GeopoliticsToday', 'DiplomacyWatch', 'MilitaryUpdate', 'EconomicMonitor'];
			const channel = channels[Math.floor(Math.random() * channels.length)];
			
			data.push({
				timestamp: timestamp.toISOString(),
				sentiment_score: sentiment,
				relevance_score: relevance,
				content: content,
				channel_name: channel
			});
		}
		
		return data;
	}

	// Simulate real-time data updates
	function simulateRealTimeUpdates() {
		setInterval(() => {
			analyticsData.update(data => {
				// Update global sentiment with small variations
				const variation = (Math.random() - 0.5) * 0.1;
				data.globalSentiment = Math.max(-1, Math.min(1, data.globalSentiment + variation));
				
				// Update regional sentiments
				Object.keys(data.regionalSentiments).forEach(region => {
					const regionVariation = (Math.random() - 0.5) * 0.08;
					data.regionalSentiments[region].value = Math.max(-1, Math.min(1, 
						data.regionalSentiments[region].value + regionVariation
					));
				});
				
				// Update stats
				data.stats.totalMessages += Math.floor(Math.random() * 5);
				data.stats.avgProcessingTime = Math.max(0.5, Math.min(3.0, 
					data.stats.avgProcessingTime + (Math.random() - 0.5) * 0.2
				));
				
				return data;
			});
		}, 3000); // Update every 3 seconds
	}

	onMount(() => {
		// Initialize timeline data
		analyticsData.update(data => ({
			...data,
			timelineData: generateTimelineData()
		}));
		
		// Start real-time simulation
		simulateRealTimeUpdates();
	});

	// Helper function to get sentiment color
	function getSentimentColor(value) {
		if (value >= 0.3) return '#22c55e';
		if (value <= -0.3) return '#ef4444';
		return '#f59e0b';
	}
</script>

<style>
	.analytics-page {
		min-height: calc(100vh - 64px);
		background: var(--background-primary);
		padding: 24px;
	}

	.page-header {
		margin-bottom: 32px;
	}

	.page-title {
		font-size: 2rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: 8px;
	}

	.page-subtitle {
		font-size: 1rem;
		color: var(--text-secondary);
		margin-bottom: 24px;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 16px;
		margin-bottom: 32px;
	}

	.stat-card {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 12px;
		padding: 20px;
		text-align: center;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	.stat-value {
		font-size: 2rem;
		font-weight: 700;
		color: var(--accent-primary);
		display: block;
		margin-bottom: 4px;
	}

	.stat-label {
		font-size: 0.875rem;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.analytics-grid {
		display: grid;
		grid-template-columns: 1fr 2fr;
		gap: 24px;
		margin-bottom: 32px;
	}

	.sentiment-overview {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 12px;
		padding: 24px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.overview-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 24px;
		text-align: center;
	}

	.global-gauge {
		margin-bottom: 32px;
	}

	.regional-sentiments {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 16px;
	}

	.regional-item {
		background: var(--background-primary);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 16px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.regional-info {
		flex: 1;
	}

	.regional-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
	}

	.regional-confidence {
		font-size: 0.75rem;
		color: var(--text-tertiary);
	}

	.regional-value {
		font-size: 1.25rem;
		font-weight: 700;
		text-align: right;
	}

	.trend-section {
		margin-bottom: 32px;
	}

	.section-title {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 16px;
	}

	.status-bar {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 16px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 24px;
	}

	.status-item {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.status-indicator {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #22c55e;
		animation: pulse 2s infinite;
	}

	.status-text {
		font-size: 0.875rem;
		color: var(--text-secondary);
	}

	.status-value {
		font-weight: 600;
		color: var(--text-primary);
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	@media (max-width: 1024px) {
		.analytics-grid {
			grid-template-columns: 1fr;
		}
		
		.regional-sentiments {
			grid-template-columns: 1fr;
		}
	}

	@media (max-width: 768px) {
		.analytics-page {
			padding: 16px;
		}
		
		.page-title {
			font-size: 1.5rem;
		}
		
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
			gap: 12px;
		}
		
		.stat-card {
			padding: 16px;
		}
		
		.stat-value {
			font-size: 1.5rem;
		}
	}

	/* Additional regional sentiment grid styling */
	.regional-sentiments:last-child {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 16px;
	}
</style>

<svelte:head>
	<title>Analytics - GeopolMonitor</title>
</svelte:head>

<div class="analytics-page">
	<!-- Page Header -->
	<div class="page-header">
		<h1 class="page-title">Sentiment Analytics Dashboard</h1>
		<p class="page-subtitle">
			Real-time geopolitical sentiment analysis and trend monitoring
		</p>
		
		<!-- Status Bar -->
		<div class="status-bar">
			<div class="status-item">
				<div class="status-indicator"></div>
				<span class="status-text">System Status: <span class="status-value">LIVE</span></span>
			</div>
			<div class="status-item">
				<span class="status-text">Processing: <span class="status-value">{$analyticsData.stats.avgProcessingTime.toFixed(1)}s avg</span></span>
			</div>
			<div class="status-item">
				<span class="status-text">Last Updated: <span class="status-value">{new Date().toLocaleTimeString()}</span></span>
			</div>
		</div>
	</div>

	<!-- Key Statistics -->
	<div class="stats-grid">
		<div class="stat-card">
			<span class="stat-value">{$analyticsData.stats.totalMessages.toLocaleString()}</span>
			<span class="stat-label">Total Messages</span>
		</div>
		<div class="stat-card">
			<span class="stat-value">{$analyticsData.stats.activeChannels}</span>
			<span class="stat-label">Active Channels</span>
		</div>
		<div class="stat-card">
			<span class="stat-value">{$analyticsData.stats.criticalAlerts}</span>
			<span class="stat-label">Critical Alerts</span>
		</div>
		<div class="stat-card">
			<span class="stat-value">{($analyticsData.globalConfidence * 100).toFixed(0)}%</span>
			<span class="stat-label">AI Confidence</span>
		</div>
	</div>

	<!-- Main Analytics Grid -->
	<div class="analytics-grid">
		<!-- Sentiment Overview Panel -->
		<div class="sentiment-overview">
			<h2 class="overview-title">Global Sentiment Overview</h2>
			
			<!-- Global Sentiment Gauge -->
			<div class="global-gauge">
				<SentimentGauge 
					value={$analyticsData.globalSentiment}
					confidence={$analyticsData.globalConfidence}
					label="Global Sentiment"
					size={220}
				/>
			</div>
			
			<!-- Regional Breakdown -->
			<div class="regional-sentiments">
				{#each Object.entries($analyticsData.regionalSentiments) as [region, data]}
					<div class="regional-item">
						<div class="regional-info">
							<div class="regional-name">{region}</div>
							<div class="regional-confidence">
								Confidence: {Math.round(data.confidence * 100)}%
							</div>
						</div>
						<div 
							class="regional-value"
							style="color: {getSentimentColor(data.value)}"
						>
							{data.value >= 0 ? '+' : ''}{(data.value * 100).toFixed(0)}%
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Trend Timeline -->
		<div class="trend-section">
			<TrendTimeline 
				data={$analyticsData.timelineData}
				title="7-Day Sentiment Trend"
				height={400}
			/>
		</div>
	</div>

	<!-- Additional smaller gauges for key regions -->
	<div class="section-title">Regional Sentiment Details</div>
	<div class="regional-sentiments" style="margin-bottom: 32px;">
		{#each Object.entries($analyticsData.regionalSentiments).slice(0, 3) as [region, data]}
			<SentimentGauge 
				value={data.value}
				confidence={data.confidence}
				label={region}
				size={180}
			/>
		{/each}
	</div>
</div>

<!-- Alert Panel (positioned fixed) -->
<AlertPanel />

 