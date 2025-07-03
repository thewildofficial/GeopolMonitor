<script lang="ts">
  // Simple component to test basic functionality
  console.log('Telegram page loading...');
</script>

<div class="telegram-page">
  <div class="container">
    <h1>🔴 LIVE TELEGRAM FEED</h1>
    <p>Intelligence monitoring platform is initializing...</p>
    
    <div class="status">
      <div class="status-item">
        <span class="status-label">Connection:</span>
        <span class="status-value">🔴 Establishing...</span>
      </div>
      <div class="status-item">
        <span class="status-label">Messages:</span>
        <span class="status-value">0</span>
      </div>
    </div>
    
    <div class="placeholder">
      <div class="empty-state">
        <div class="empty-icon">🛰️</div>
        <h3>Monitoring Global Communications</h3>
        <p>Waiting for intelligence signals...</p>
      </div>
    </div>
  </div>
</div>

<style>
  .telegram-page {
    min-height: 100vh;
    background: var(--osint-bg-primary);
    color: var(--osint-text-primary);
    padding: 2rem;
    font-family: 'Inter', system-ui, sans-serif;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
  }

  h1 {
    color: var(--osint-accent-cyan);
    text-align: center;
    margin-bottom: 2rem;
  }

  p {
    color: var(--osint-text-secondary);
    text-align: center;
    margin-bottom: 2rem;
  }

  .status {
    display: flex;
    gap: 2rem;
    justify-content: center;
    margin-bottom: 3rem;
  }

  .status-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .status-label {
    font-size: 0.875rem;
    color: var(--osint-text-muted);
    text-transform: uppercase;
  }

  .status-value {
    font-weight: 600;
    color: var(--osint-text-primary);
  }

  .placeholder {
    background: var(--osint-surface);
    border: 1px solid var(--osint-border);
    border-radius: 8px;
    padding: 3rem;
    text-align: center;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .empty-icon {
    font-size: 4rem;
    opacity: 0.6;
  }

  .empty-state h3 {
    margin: 0;
    color: var(--osint-text-secondary);
  }

  .empty-state p {
    margin: 0;
    color: var(--osint-text-muted);
  }
</style> 