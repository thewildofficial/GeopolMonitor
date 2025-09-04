<script>
	import { onMount, onDestroy } from 'svelte';
	import { writable } from 'svelte/store';

	// Props
	export let alerts = [];
	export let maxAlerts = 10;
	export let autoDisappear = true;
	export let alertTimeout = 10000; // 10 seconds

	// Internal state
	const activeAlerts = writable([]);
	let alertTimeouts = new Map();

	// Alert types and their styles
	const alertTypes = {
		critical: {
			icon: '🚨',
			color: '#ef4444',
			bgColor: 'rgba(239, 68, 68, 0.1)',
			borderColor: 'rgba(239, 68, 68, 0.3)'
		},
		warning: {
			icon: '⚠️',
			color: '#f59e0b',
			bgColor: 'rgba(245, 158, 11, 0.1)',
			borderColor: 'rgba(245, 158, 11, 0.3)'
		},
		info: {
			icon: 'ℹ️',
			color: '#3b82f6',
			bgColor: 'rgba(59, 130, 246, 0.1)',
			borderColor: 'rgba(59, 130, 246, 0.3)'
		},
		success: {
			icon: '✅',
			color: '#22c55e',
			bgColor: 'rgba(34, 197, 94, 0.1)',
			borderColor: 'rgba(34, 197, 94, 0.3)'
		}
	};

	// Mock alert generator for demonstration
	function generateMockAlert() {
		const mockAlerts = [
			{
				type: 'critical',
				title: 'Sentiment Threshold Breach',
				message: 'Eastern Europe sentiment dropped below -0.8 (critical threshold)',
				timestamp: new Date(),
				metadata: {
					region: 'Eastern Europe',
					threshold: -0.8,
					current: -0.85,
					channels: ['IntelAlerts', 'MilitaryWatch']
				}
			},
			{
				type: 'warning',
				title: 'Sentiment Volatility Alert',
				message: 'High volatility detected in Asia-Pacific region over last 2 hours',
				timestamp: new Date(),
				metadata: {
					region: 'Asia-Pacific',
					volatility: 0.65,
					timeframe: '2 hours'
				}
			},
			{
				type: 'info',
				title: 'Trending Topic Detected',
				message: 'New topic cluster identified: "Trade Agreement Negotiations"',
				timestamp: new Date(),
				metadata: {
					topic: 'Trade Agreement Negotiations',
					relevance: 0.89,
					messages: 47
				}
			},
			{
				type: 'success',
				title: 'Sentiment Recovery',
				message: 'Middle East sentiment improved above +0.5 threshold',
				timestamp: new Date(),
				metadata: {
					region: 'Middle East',
					threshold: 0.5,
					current: 0.62
				}
			}
		];

		return mockAlerts[Math.floor(Math.random() * mockAlerts.length)];
	}

	// Add new alert
	function addAlert(alert) {
		const alertWithId = {
			...alert,
			id: Date.now() + Math.random(),
			timestamp: alert.timestamp || new Date()
		};

		activeAlerts.update(alerts => {
			const newAlerts = [alertWithId, ...alerts].slice(0, maxAlerts);
			return newAlerts;
		});

		// Auto-remove if enabled
		if (autoDisappear) {
			const timeoutId = setTimeout(() => {
				removeAlert(alertWithId.id);
			}, alertTimeout);
			
			alertTimeouts.set(alertWithId.id, timeoutId);
		}
	}

	// Remove alert
	function removeAlert(alertId) {
		activeAlerts.update(alerts => alerts.filter(alert => alert.id !== alertId));
		
		// Clear timeout if exists
		if (alertTimeouts.has(alertId)) {
			clearTimeout(alertTimeouts.get(alertId));
			alertTimeouts.delete(alertId);
		}
	}

	// Clear all alerts
	function clearAllAlerts() {
		// Clear all timeouts
		alertTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
		alertTimeouts.clear();
		
		// Clear alerts
		activeAlerts.set([]);
	}

	// Mock alert simulation
	let mockInterval;
	onMount(() => {
		// Add initial mock alerts
		setTimeout(() => addAlert(generateMockAlert()), 500);
		setTimeout(() => addAlert(generateMockAlert()), 1500);
		
		// Generate mock alerts periodically
		mockInterval = setInterval(() => {
			if (Math.random() < 0.3) { // 30% chance every 5 seconds
				addAlert(generateMockAlert());
			}
		}, 5000);
	});

	onDestroy(() => {
		if (mockInterval) {
			clearInterval(mockInterval);
		}
		clearAllAlerts();
	});

	// Format timestamp
	function formatTime(timestamp) {
		return new Date(timestamp).toLocaleTimeString();
	}

	// Get alert style
	function getAlertStyle(type) {
		return alertTypes[type] || alertTypes.info;
	}
</script>

<style>
	.alert-panel {
		position: fixed;
		top: 80px;
		right: 20px;
		width: 350px;
		max-height: 600px;
		z-index: 1000;
		pointer-events: none;
	}

	.alert-container {
		display: flex;
		flex-direction: column;
		gap: 12px;
		overflow-y: auto;
		max-height: 100%;
		padding-right: 8px;
	}

	.alert-item {
		background: var(--background-secondary);
		border: 1px solid;
		border-radius: 8px;
		padding: 16px;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		backdrop-filter: blur(8px);
		pointer-events: auto;
		transition: all 0.3s ease;
		animation: slideIn 0.3s ease-out;
	}

	.alert-item:hover {
		transform: translateX(-4px);
		box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
	}

	.alert-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 8px;
	}

	.alert-icon-title {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
	}

	.alert-icon {
		font-size: 18px;
		flex-shrink: 0;
	}

	.alert-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		line-height: 1.3;
	}

	.alert-close {
		background: none;
		border: none;
		color: var(--text-tertiary);
		cursor: pointer;
		padding: 2px;
		border-radius: 4px;
		font-size: 16px;
		line-height: 1;
		transition: all 0.2s ease;
		flex-shrink: 0;
		margin-left: 8px;
	}

	.alert-close:hover {
		background: var(--background-primary);
		color: var(--text-secondary);
	}

	.alert-message {
		font-size: 13px;
		color: var(--text-secondary);
		line-height: 1.4;
		margin-bottom: 12px;
	}

	.alert-metadata {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-bottom: 8px;
	}

	.metadata-tag {
		background: var(--background-primary);
		border: 1px solid var(--border-secondary);
		border-radius: 12px;
		padding: 4px 8px;
		font-size: 11px;
		color: var(--text-tertiary);
		font-weight: 500;
	}

	.alert-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 11px;
		color: var(--text-tertiary);
		border-top: 1px solid var(--border-secondary);
		padding-top: 8px;
		margin-top: 8px;
	}

	.alert-time {
		font-weight: 500;
	}

	.alert-controls {
		position: sticky;
		top: 0;
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 8px;
		padding: 12px 16px;
		margin-bottom: 12px;
		backdrop-filter: blur(8px);
		pointer-events: auto;
		z-index: 10;
	}

	.controls-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}

	.controls-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.alert-count {
		background: var(--accent-primary);
		color: var(--background-primary);
		border-radius: 12px;
		padding: 2px 8px;
		font-size: 11px;
		font-weight: 600;
	}

	.controls-actions {
		display: flex;
		gap: 8px;
	}

	.control-btn {
		background: var(--background-primary);
		border: 1px solid var(--border-secondary);
		color: var(--text-secondary);
		border-radius: 4px;
		padding: 4px 8px;
		font-size: 11px;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.control-btn:hover {
		background: var(--background-tertiary);
		color: var(--text-primary);
	}

	.empty-state {
		text-align: center;
		padding: 40px 20px;
		color: var(--text-tertiary);
		font-size: 14px;
	}

	.empty-icon {
		font-size: 2rem;
		margin-bottom: 12px;
		opacity: 0.5;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	@media (max-width: 768px) {
		.alert-panel {
			right: 12px;
			left: 12px;
			width: auto;
			top: 70px;
		}
		
		.alert-item {
			padding: 12px;
		}
		
		.alert-title {
			font-size: 13px;
		}
		
		.alert-message {
			font-size: 12px;
		}
	}

	/* Scrollbar styling */
	.alert-container::-webkit-scrollbar {
		width: 4px;
	}

	.alert-container::-webkit-scrollbar-track {
		background: transparent;
	}

	.alert-container::-webkit-scrollbar-thumb {
		background: var(--border-secondary);
		border-radius: 2px;
	}

	.alert-container::-webkit-scrollbar-thumb:hover {
		background: var(--border-primary);
	}
</style>

<div class="alert-panel">
	<div class="alert-controls">
		<div class="controls-header">
			<div class="controls-title">Live Alerts</div>
			<div class="alert-count">{$activeAlerts.length}</div>
		</div>
		<div class="controls-actions">
			<button class="control-btn" on:click={() => addAlert(generateMockAlert())}>
				+ Test Alert
			</button>
			<button class="control-btn" on:click={clearAllAlerts}>
				Clear All
			</button>
		</div>
	</div>
	
	<div class="alert-container">
		{#if $activeAlerts.length === 0}
			<div class="empty-state">
				<div class="empty-icon">🔔</div>
				<div>No active alerts</div>
				<div style="font-size: 12px; margin-top: 4px;">System monitoring normally</div>
			</div>
		{:else}
			{#each $activeAlerts as alert (alert.id)}
				<div 
					class="alert-item"
					style="
						border-color: {getAlertStyle(alert.type).borderColor};
						background: {getAlertStyle(alert.type).bgColor};
					"
				>
					<div class="alert-header">
						<div class="alert-icon-title">
							<span class="alert-icon">{getAlertStyle(alert.type).icon}</span>
							<div class="alert-title" style="color: {getAlertStyle(alert.type).color}">
								{alert.title}
							</div>
						</div>
						<button class="alert-close" on:click={() => removeAlert(alert.id)}>
							×
						</button>
					</div>
					
					<div class="alert-message">
						{alert.message}
					</div>
					
					{#if alert.metadata}
						<div class="alert-metadata">
							{#each Object.entries(alert.metadata) as [key, value]}
								<span class="metadata-tag">
									{key}: {value}
								</span>
							{/each}
						</div>
					{/if}
					
					<div class="alert-footer">
						<span class="alert-time">{formatTime(alert.timestamp)}</span>
						<span style="color: {getAlertStyle(alert.type).color}; text-transform: uppercase;">
							{alert.type}
						</span>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div> 