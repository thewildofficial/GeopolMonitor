<script lang="ts">
  import { onMount } from 'svelte';
  import '$lib/styles/global.css';
  import Navigation from '$lib/components/Navigation.svelte';

  onMount(() => {
    // Initialize any global app state here
    console.log('🚀 GeopolMonitor SvelteKit app initialized');
    
    // Ensure dark theme is applied for shadcn/ui components
    if (typeof document !== 'undefined') {
      document.documentElement.classList.add('dark');
    }
  });
</script>

<svelte:head>
  <title>GeopolMonitor - Intelligence Platform</title>
</svelte:head>

<div class="w-full min-h-screen bg-gray-900 text-gray-100">
  <Navigation />
  <main>
    <slot />
  </main>
</div>

<style>
  main {
    width: 100%;
    min-height: 100vh;
    background-color: var(--background-primary);
    color: var(--text-primary);
  }
</style> 