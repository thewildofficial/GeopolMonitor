<script>
	import { page } from '$app/stores';
	
	// Navigation items
	const navItems = [
		{
			name: 'Dashboard',
			href: '/',
			icon: '🏠'
		},
		{
			name: 'Telegram Feed',
			href: '/telegram',
			icon: '💬'
		},
		{
			name: 'Global Map',
			href: '/map',
			icon: '🌍'
		},
		{
			name: 'Analytics',
			href: '/analytics',
			icon: '📊'
		}
	];

	// Check if a route is active
	function isActive(href) {
		if (href === '/') {
			return $page.url.pathname === '/';
		}
		return $page.url.pathname.startsWith(href);
	}
</script>

<style>
	.nav-container {
		background: var(--background-secondary);
		border-bottom: 1px solid var(--border-secondary);
		padding: 0 20px;
		position: sticky;
		top: 0;
		z-index: 50;
		backdrop-filter: blur(8px);
	}

	.nav-content {
		max-width: 1200px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 64px;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 12px;
		text-decoration: none;
		color: var(--text-primary);
		font-weight: 700;
		font-size: 1.25rem;
	}

	.nav-brand:hover {
		color: var(--accent-primary);
	}

	.brand-icon {
		font-size: 1.5rem;
	}

	.nav-menu {
		display: flex;
		gap: 8px;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.nav-item {
		position: relative;
	}

	.nav-link {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		border-radius: 6px;
		text-decoration: none;
		color: var(--text-secondary);
		font-weight: 500;
		font-size: 14px;
		transition: all 0.2s ease;
		position: relative;
	}

	.nav-link:hover {
		color: var(--text-primary);
		background: var(--background-primary);
	}

	.nav-link.active {
		color: var(--accent-primary);
		background: rgba(110, 231, 183, 0.1);
	}

	.nav-link.active::after {
		content: '';
		position: absolute;
		bottom: -16px;
		left: 50%;
		transform: translateX(-50%);
		width: 20px;
		height: 2px;
		background: var(--accent-primary);
		border-radius: 1px;
	}

	.nav-icon {
		font-size: 1rem;
	}

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		background: rgba(34, 197, 94, 0.1);
		border: 1px solid rgba(34, 197, 94, 0.3);
		border-radius: 16px;
		font-size: 12px;
		font-weight: 600;
		color: #22c55e;
	}

	.status-dot {
		width: 6px;
		height: 6px;
		background: #22c55e;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	@media (max-width: 768px) {
		.nav-content {
			padding: 0 16px;
		}
		
		.nav-menu {
			gap: 4px;
		}
		
		.nav-link {
			padding: 6px 12px;
			font-size: 13px;
		}
		
		.brand-text {
			display: none;
		}
		
		.status-indicator {
			padding: 4px 8px;
			font-size: 11px;
		}
	}

	@media (max-width: 640px) {
		.nav-link span {
			display: none;
		}
		
		.nav-link {
			padding: 8px;
		}
	}
</style>

<nav class="nav-container">
	<div class="nav-content">
		<!-- Brand -->
		<a href="/" class="nav-brand">
			<span class="brand-icon">🎯</span>
			<span class="brand-text">GeopolMonitor</span>
		</a>

		<!-- Navigation Menu -->
		<ul class="nav-menu">
			{#each navItems as item}
				<li class="nav-item">
					<a 
						href={item.href} 
						class="nav-link"
						class:active={isActive(item.href)}
					>
						<span class="nav-icon">{item.icon}</span>
						<span>{item.name}</span>
					</a>
				</li>
			{/each}
		</ul>

		<!-- Status Indicator -->
		<div class="nav-actions">
			<div class="status-indicator">
				<div class="status-dot"></div>
				<span>LIVE</span>
			</div>
		</div>
	</div>
</nav> 