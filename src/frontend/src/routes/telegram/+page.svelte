<script>
  import TelegramFeed from '$lib/components/TelegramFeed.svelte';
  
  console.log('🔴 Telegram page loading...');
</script>

<svelte:head>
  <title>Live Intelligence Feed - GeopolMonitor</title>
  <meta name="description" content="Real-time geopolitical intelligence monitoring dashboard" />
</svelte:head>

<div class="page-container">
  <TelegramFeed />
</div>

<style>
  .page-container {
    min-height: 100vh;
    background-color: var(--background-primary);
    color: var(--text-primary);
  }
</style> 