<script lang="ts">
  import { onMount } from 'svelte';
  import '../lib/styles/global.css';

  onMount(() => {
    // Initialize any global app state here
    console.log('🚀 GeopolMonitor SvelteKit app initialized');
  });
</script>

<main class="app">
  <slot />
</main>

<style>
  :global(html, body) {
    margin: 0;
    padding: 0;
    height: 100%;
    font-family: 'Inter', system-ui, sans-serif;
    background: var(--osint-bg-primary);
    color: var(--osint-text-primary);
  }

  .app {
    height: 100vh;
    width: 100vw;
    overflow: hidden;
  }
</style> 