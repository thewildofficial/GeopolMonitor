<script>
	import { onMount, onDestroy } from 'svelte';
	import { tweened } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';

	// Props
	export let value = 0; // Sentiment value between -1 and 1
	export let label = 'Overall Sentiment';
	export let size = 200;
	export let confidence = 0.85;
	export let showLabels = true;

	// Animation store
	const animatedValue = tweened(0, {
		duration: 1500,
		easing: cubicOut
	});

	// Update animated value when prop changes
	$: animatedValue.set(value);

	// Calculate gauge properties
	$: normalizedValue = Math.max(-1, Math.min(1, $animatedValue));
	$: angle = ((normalizedValue + 1) / 2) * 180; // Convert to 0-180 degrees
	$: rotation = angle - 90; // Adjust for starting position
	$: percentage = Math.round(Math.abs(normalizedValue) * 100);
	
	// Color based on sentiment
	$: sentimentColor = getSentimentColor(normalizedValue);
	$: sentimentLabel = getSentimentLabel(normalizedValue);

	// SVG properties
	$: radius = size / 2 - 20;
	$: strokeWidth = 8;
	$: center = size / 2;
	$: circumference = Math.PI * radius;

	function getSentimentColor(val) {
		if (val >= 0.3) return '#22c55e'; // Positive - Green
		if (val <= -0.3) return '#ef4444'; // Negative - Red
		return '#f59e0b'; // Neutral - Orange
	}

	function getSentimentLabel(val) {
		if (val >= 0.5) return 'Very Positive';
		if (val >= 0.2) return 'Positive';
		if (val >= -0.2) return 'Neutral';
		if (val >= -0.5) return 'Negative';
		return 'Very Negative';
	}

	function getConfidenceColor(conf) {
		if (conf >= 0.8) return '#22c55e';
		if (conf >= 0.6) return '#f59e0b';
		return '#ef4444';
	}

	// Generate tick marks for the gauge
	$: tickMarks = Array.from({ length: 11 }, (_, i) => {
		const tickAngle = (i * 18) - 90; // -90 to 90 degrees
		const tickValue = (i / 5) - 1; // -1 to 1
		const tickRadius = radius - 5;
		
		return {
			angle: tickAngle,
			value: tickValue,
			x1: center + Math.cos(tickAngle * Math.PI / 180) * (tickRadius - 5),
			y1: center + Math.sin(tickAngle * Math.PI / 180) * (tickRadius - 5),
			x2: center + Math.cos(tickAngle * Math.PI / 180) * tickRadius,
			y2: center + Math.sin(tickAngle * Math.PI / 180) * tickRadius,
			major: i % 5 === 0
		};
	});

	// Needle position
	$: needleAngle = rotation;
	$: needleLength = radius - 15;
	$: needleX = center + Math.cos(needleAngle * Math.PI / 180) * needleLength;
	$: needleY = center + Math.sin(needleAngle * Math.PI / 180) * needleLength;
</script>

<style>
	.gauge-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		background: var(--background-secondary);
		border: 1px solid var(--border-secondary);
		border-radius: 12px;
		padding: 20px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.gauge-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 16px;
		text-align: center;
	}

	.gauge-svg {
		overflow: visible;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
	}

	.gauge-arc {
		fill: none;
		stroke: var(--border-secondary);
		stroke-width: 8;
		stroke-linecap: round;
	}

	.gauge-arc-fill {
		fill: none;
		stroke-width: 8;
		stroke-linecap: round;
		transition: stroke 0.3s ease;
	}

	.gauge-needle {
		stroke-width: 3;
		stroke-linecap: round;
		transition: all 0.3s ease;
		filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
	}

	.gauge-center {
		fill: var(--background-primary);
		stroke: var(--border-secondary);
		stroke-width: 2;
	}

	.gauge-tick {
		stroke: var(--text-tertiary);
		stroke-width: 1;
	}

	.gauge-tick.major {
		stroke: var(--text-secondary);
		stroke-width: 2;
	}

	.gauge-labels {
		display: flex;
		justify-content: space-between;
		width: 100%;
		margin-top: 16px;
		padding: 0 20px;
	}

	.gauge-label {
		font-size: 12px;
		color: var(--text-secondary);
		text-align: center;
	}

	.sentiment-value {
		font-size: 24px;
		font-weight: 700;
		margin-bottom: 4px;
		transition: color 0.3s ease;
	}

	.sentiment-text {
		font-size: 14px;
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.confidence-indicator {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 12px;
		padding: 8px 12px;
		background: var(--background-primary);
		border-radius: 6px;
		border: 1px solid var(--border-secondary);
	}

	.confidence-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		transition: background-color 0.3s ease;
	}

	.confidence-text {
		font-size: 12px;
		color: var(--text-secondary);
	}

	.confidence-value {
		font-weight: 600;
		color: var(--text-primary);
	}

	@media (max-width: 768px) {
		.gauge-container {
			padding: 16px;
		}
		
		.gauge-title {
			font-size: 14px;
		}
		
		.sentiment-value {
			font-size: 20px;
		}
		
		.gauge-labels {
			padding: 0 10px;
		}
	}
</style>

<div class="gauge-container">
	{#if showLabels}
		<div class="gauge-title">{label}</div>
	{/if}
	
	<svg class="gauge-svg" width={size} height={size * 0.6 + 60}>
		<!-- Background arc -->
		<path
			class="gauge-arc"
			d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
		/>
		
		<!-- Colored sentiment arc -->
		<path
			class="gauge-arc-fill"
			stroke={sentimentColor}
			stroke-dasharray={`${(Math.abs(normalizedValue) / 2) * circumference} ${circumference}`}
			d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
		/>
		
		<!-- Tick marks -->
		{#each tickMarks as tick}
			<line
				class="gauge-tick"
				class:major={tick.major}
				x1={tick.x1}
				y1={tick.y1}
				x2={tick.x2}
				y2={tick.y2}
			/>
		{/each}
		
		<!-- Needle -->
		<line
			class="gauge-needle"
			stroke={sentimentColor}
			x1={center}
			y1={center}
			x2={needleX}
			y2={needleY}
		/>
		
		<!-- Center circle -->
		<circle
			class="gauge-center"
			cx={center}
			cy={center}
			r="6"
		/>
	</svg>
	
	{#if showLabels}
		<div class="gauge-labels">
			<div class="gauge-label">
				<div class="sentiment-value" style="color: {sentimentColor}">
					{normalizedValue >= 0 ? '+' : ''}{(normalizedValue * 100).toFixed(0)}%
				</div>
				<div class="sentiment-text" style="color: {sentimentColor}">
					{sentimentLabel}
				</div>
			</div>
		</div>
		
		<div class="confidence-indicator">
			<div 
				class="confidence-dot" 
				style="background-color: {getConfidenceColor(confidence)}"
			></div>
			<span class="confidence-text">
				Confidence: <span class="confidence-value">{Math.round(confidence * 100)}%</span>
			</span>
		</div>
	{/if}
</div> 