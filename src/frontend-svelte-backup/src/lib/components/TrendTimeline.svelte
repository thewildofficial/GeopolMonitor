<script>
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { Chart, registerables } from 'chart.js';
	import 'chartjs-adapter-date-fns';

	// Register Chart.js components
	Chart.register(...registerables);

	// Props
	export let data = [];
	export let title = 'Sentiment Trend';
	export let timeRange = '7d'; // '1d', '7d', '30d'
	export let showAverage = true;
	export let height = 300;

	// Component state
	let chartCanvas;
	let chartInstance;
	let containerWidth = 800;

	// Reactive data processing
	$: processedData = processTimelineData(data, timeRange);
	$: if (chartInstance && processedData) {
		updateChart();
	}

	// Color scheme for intelligence platform
	const colors = {
		positive: '#22c55e',
		negative: '#ef4444',
		neutral: '#f59e0b',
		average: '#00d9ff',
		grid: '#374151',
		text: '#e5e7eb'
	};

	function processTimelineData(rawData, range) {
		if (!rawData || rawData.length === 0) {
			return generateMockData(range);
		}

		// Sort by timestamp
		const sorted = [...rawData].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
		
		// Filter by time range
		const now = new Date();
		const cutoff = new Date();
		switch (range) {
			case '1d':
				cutoff.setDate(now.getDate() - 1);
				break;
			case '7d':
				cutoff.setDate(now.getDate() - 7);
				break;
			case '30d':
				cutoff.setDate(now.getDate() - 30);
				break;
		}

		const filtered = sorted.filter(item => new Date(item.timestamp) >= cutoff);
		
		// Calculate moving average
		const windowSize = Math.max(1, Math.floor(filtered.length / 20));
		const movingAverage = [];
		
		for (let i = windowSize - 1; i < filtered.length; i++) {
			const window = filtered.slice(i - windowSize + 1, i + 1);
			const avg = window.reduce((sum, item) => sum + (item.sentiment_score || 0), 0) / window.length;
			movingAverage.push({
				timestamp: filtered[i].timestamp,
				value: avg
			});
		}

		return {
			sentimentData: filtered.map(item => ({
				x: new Date(item.timestamp),
				y: item.sentiment_score || 0,
				relevance: item.relevance_score || 0,
				content: item.content?.substring(0, 100) + '...' || 'No content',
				channel: item.channel_name || 'Unknown'
			})),
			averageData: movingAverage.map(item => ({
				x: new Date(item.timestamp),
				y: item.value
			}))
		};
	}

	function generateMockData(range) {
		const points = range === '1d' ? 24 : range === '7d' ? 168 : 720; // Hours of data
		const now = new Date();
		const sentimentData = [];
		const averageData = [];
		
		for (let i = points; i >= 0; i--) {
			const timestamp = new Date(now.getTime() - i * 60 * 60 * 1000);
			
			// Generate realistic sentiment patterns
			const base = Math.sin(i / 24) * 0.3; // Daily cycle
			const noise = (Math.random() - 0.5) * 0.4; // Random variation
			const trend = (points - i) / points * 0.2 - 0.1; // Slight trend
			
			const sentiment = Math.max(-1, Math.min(1, base + noise + trend));
			const relevance = Math.random() * 0.5 + 0.5; // 0.5 to 1.0
			
			sentimentData.push({
				x: timestamp,
				y: sentiment,
				relevance: relevance,
				content: `Mock intelligence data point ${i}...`,
				channel: i % 3 === 0 ? 'IntelAlerts' : i % 3 === 1 ? 'GeopoliticsToday' : 'DiplomacyWatch'
			});
		}

		// Calculate moving average
		const windowSize = Math.max(1, Math.floor(sentimentData.length / 20));
		for (let i = windowSize - 1; i < sentimentData.length; i++) {
			const window = sentimentData.slice(i - windowSize + 1, i + 1);
			const avg = window.reduce((sum, item) => sum + item.y, 0) / window.length;
			averageData.push({
				x: sentimentData[i].x,
				y: avg
			});
		}

		return { sentimentData, averageData };
	}

	function createChart() {
		if (!chartCanvas || !processedData) return;

		const ctx = chartCanvas.getContext('2d');
		
		const datasets = [
			{
				label: 'Sentiment Score',
				data: processedData.sentimentData,
				backgroundColor: (context) => {
					const value = context.parsed?.y || 0;
					if (value > 0.2) return colors.positive + '40';
					if (value < -0.2) return colors.negative + '40';
					return colors.neutral + '40';
				},
				borderColor: (context) => {
					const value = context.parsed?.y || 0;
					if (value > 0.2) return colors.positive;
					if (value < -0.2) return colors.negative;
					return colors.neutral;
				},
				borderWidth: 2,
				pointRadius: (context) => {
					const relevance = context.raw?.relevance || 0;
					return Math.max(2, relevance * 6); // Size based on relevance
				},
				pointHoverRadius: 8,
				tension: 0.1,
				type: 'line'
			}
		];

		if (showAverage) {
			datasets.push({
				label: 'Moving Average',
				data: processedData.averageData,
				borderColor: colors.average,
				backgroundColor: colors.average + '20',
				borderWidth: 3,
				pointRadius: 0,
				pointHoverRadius: 6,
				tension: 0.3,
				type: 'line'
			});
		}

		chartInstance = new Chart(ctx, {
			type: 'line',
			data: { datasets },
			options: {
				responsive: true,
				maintainAspectRatio: false,
				interaction: {
					intersect: false,
					mode: 'index'
				},
				scales: {
					x: {
						type: 'time',
						time: {
							displayFormats: {
								hour: 'HH:mm',
								day: 'MMM dd',
								week: 'MMM dd'
							},
							tooltipFormat: 'MMM dd, HH:mm'
						},
						grid: {
							color: colors.grid + '60',
							borderColor: colors.grid
						},
						ticks: {
							color: colors.text,
							maxTicksLimit: 8
						}
					},
					y: {
						min: -1,
						max: 1,
						grid: {
							color: colors.grid + '60',
							borderColor: colors.grid
						},
						ticks: {
							color: colors.text,
							callback: function(value) {
								if (value === 0) return 'Neutral';
								if (value > 0) return `+${(value * 100).toFixed(0)}%`;
								return `${(value * 100).toFixed(0)}%`;
							}
						}
					}
				},
				plugins: {
					title: {
						display: !!title,
						text: title,
						color: colors.text,
						font: {
							size: 16,
							weight: '600'
						},
						padding: 20
					},
					legend: {
						labels: {
							color: colors.text,
							usePointStyle: true,
							padding: 20
						}
					},
					tooltip: {
						backgroundColor: 'rgba(15, 23, 42, 0.95)',
						titleColor: colors.text,
						bodyColor: colors.text,
						borderColor: colors.grid,
						borderWidth: 1,
						cornerRadius: 8,
						padding: 12,
						callbacks: {
							title: function(context) {
								return new Date(context[0].parsed.x).toLocaleString();
							},
							label: function(context) {
								const value = context.parsed.y;
								const sentiment = value > 0.2 ? 'Positive' : value < -0.2 ? 'Negative' : 'Neutral';
								return `${context.dataset.label}: ${(value * 100).toFixed(1)}% (${sentiment})`;
							},
							afterBody: function(context) {
								const dataPoint = context[0].raw;
								if (dataPoint.content && dataPoint.channel) {
									return [
										'',
										`Source: ${dataPoint.channel}`,
										`Relevance: ${Math.round(dataPoint.relevance * 100)}%`,
										'',
										dataPoint.content
									];
								}
								return [];
							}
						}
					}
				},
				elements: {
					point: {
						hoverBackgroundColor: colors.average,
						hoverBorderColor: '#ffffff',
						hoverBorderWidth: 2
					}
				}
			}
		});
	}

	function updateChart() {
		if (!chartInstance || !processedData) return;

		chartInstance.data.datasets[0].data = processedData.sentimentData;
		
		if (showAverage && chartInstance.data.datasets[1]) {
			chartInstance.data.datasets[1].data = processedData.averageData;
		}

		chartInstance.update('active');
	}

	function resizeChart() {
		if (chartInstance) {
			chartInstance.resize();
		}
	}

	onMount(() => {
		createChart();
		
		// Handle window resize (only in browser)
		if (browser) {
			window.addEventListener('resize', resizeChart);
		}
		
		return () => {
			if (browser) {
				window.removeEventListener('resize', resizeChart);
			}
		};
	});

	onDestroy(() => {
		if (chartInstance) {
			chartInstance.destroy();
		}
		if (browser) {
			window.removeEventListener('resize', resizeChart);
		}
	});
</script>

<style>
	.chart-container {
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 12px;
		padding: 20px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
		width: 100%;
	}

	.chart-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;
	}

	.chart-title {
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.chart-controls {
		display: flex;
		gap: 8px;
	}

	.time-range-btn {
		padding: 6px 12px;
		border: 1px solid var(--border-secondary);
		background: var(--background-primary);
		color: var(--text-secondary);
		border-radius: 6px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.time-range-btn:hover {
		background: var(--background-tertiary);
		color: var(--text-primary);
	}

	.time-range-btn.active {
		background: var(--accent-primary);
		color: var(--background-primary);
		border-color: var(--accent-primary);
	}

	.chart-wrapper {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.chart-canvas {
		width: 100% !important;
		max-width: 100%;
	}

	.chart-stats {
		display: flex;
		justify-content: space-around;
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid var(--border-secondary);
	}

	.stat-item {
		text-align: center;
	}

	.stat-value {
		font-size: 20px;
		font-weight: 600;
		color: var(--accent-primary);
		display: block;
	}

	.stat-label {
		font-size: 12px;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	@media (max-width: 768px) {
		.chart-container {
			padding: 16px;
		}
		
		.chart-header {
			flex-direction: column;
			gap: 12px;
			align-items: flex-start;
		}
		
		.chart-controls {
			width: 100%;
			justify-content: center;
		}
		
		.time-range-btn {
			flex: 1;
			text-align: center;
		}
		
		.chart-stats {
			gap: 16px;
		}
	}
</style>

<div class="chart-container">
	<div class="chart-header">
		<div class="chart-title">{title}</div>
		<div class="chart-controls">
			<button 
				class="time-range-btn"
				class:active={timeRange === '1d'}
				on:click={() => timeRange = '1d'}
			>
				24H
			</button>
			<button 
				class="time-range-btn"
				class:active={timeRange === '7d'}
				on:click={() => timeRange = '7d'}
			>
				7D
			</button>
			<button 
				class="time-range-btn"
				class:active={timeRange === '30d'}
				on:click={() => timeRange = '30d'}
			>
				30D
			</button>
		</div>
	</div>
	
	<div class="chart-wrapper" style="height: {height}px;">
		<canvas bind:this={chartCanvas} class="chart-canvas"></canvas>
	</div>
	
	{#if processedData}
		<div class="chart-stats">
			<div class="stat-item">
				<span class="stat-value">{processedData.sentimentData.length}</span>
				<span class="stat-label">Data Points</span>
			</div>
			<div class="stat-item">
				<span class="stat-value">
					{processedData.sentimentData.filter(d => d.y > 0.2).length}
				</span>
				<span class="stat-label">Positive</span>
			</div>
			<div class="stat-item">
				<span class="stat-value">
					{processedData.sentimentData.filter(d => d.y < -0.2).length}
				</span>
				<span class="stat-label">Negative</span>
			</div>
			<div class="stat-item">
				<span class="stat-value">
					{Math.round(processedData.sentimentData.reduce((sum, d) => sum + d.y, 0) / processedData.sentimentData.length * 100)}%
				</span>
				<span class="stat-label">Avg Score</span>
			</div>
		</div>
	{/if}
</div> 