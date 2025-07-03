<script lang="ts">
  import { onMount } from 'svelte';
  
  onMount(() => {
    // Redirect to telegram page on load
    window.location.href = '/telegram';
  });
</script>

<div class="landing-page">
  <div class="container">
    <div class="hero">
      <div class="logo">
        🛰️
      </div>
      <h1 class="title">GeopolMonitor</h1>
      <p class="subtitle">Global Intelligence Monitoring Platform</p>
      <div class="redirecting">
        <div class="spinner"></div>
        <p>Redirecting to Telegram Feed...</p>
      </div>
    </div>
  </div>
</div>

<style>
  .landing-page {
    min-height: 100vh;
    background: var(--osint-bg-primary);
    color: var(--osint-text-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter', system-ui, sans-serif;
  }

  .container {
    text-align: center;
    max-width: 600px;
    padding: 2rem;
  }

  .logo {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.8;
  }

  .title {
    font-size: 3rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    color: var(--osint-accent-cyan);
    text-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
  }

  .subtitle {
    font-size: 1.25rem;
    color: var(--osint-text-secondary);
    margin: 0 0 2rem 0;
  }

  .redirecting {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--osint-border);
    border-top: 3px solid var(--osint-accent-cyan);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .redirecting p {
    color: var(--osint-text-muted);
    margin: 0;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
</style> 