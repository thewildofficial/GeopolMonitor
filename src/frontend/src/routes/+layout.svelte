<script lang="ts">
  import { onMount } from 'svelte';
  import '$lib/styles/global.css';

  onMount(() => {
    // Initialize any global app state here
    console.log('🚀 GeopolMonitor SvelteKit app initialized');
  });
</script>

<main>
  <slot />
</main>

<style>
  main {
    width: 100%;
    min-height: 100vh;
    background-color: var(--background-primary);
    color: var(--text-primary);
  }
</style> 