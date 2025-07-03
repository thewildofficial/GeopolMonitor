<script lang="ts">
  import { onMount } from 'svelte';
  import { slide } from 'svelte/transition';
  import { filteredMessages, messageStats } from '$stores/filters';
  import { websocketState, connectionQuality } from '$stores/websocket';
  import MessageCard from './MessageCard.svelte';
  import type { TelegramMessage } from '$lib/types';

  // Component state
  let feedContainer: HTMLElement;
  let autoScroll = true;
  let isAtBottom = true;

  // Reactive declarations
  $: messages = $filteredMessages;
  $: stats = $messageStats;
  $: isConnected = $websocketState.connected;

  // Handle scroll events
  function handleScroll(event: Event) {
    const target = event.target as HTMLElement;
    const threshold = 100;
    isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - threshold;
    
    if (!isAtBottom) {
      autoScroll = false;
    }
  }

  // Auto-scroll to bottom when new messages arrive
  $: if (autoScroll && isAtBottom && feedContainer) {
    setTimeout(() => {
      feedContainer.scrollTop = feedContainer.scrollHeight;
    }, 50);
  }

  // Scroll to bottom
  function scrollToBottom() {
    autoScroll = true;
    if (feedContainer) {
      feedContainer.scrollTo({
        top: feedContainer.scrollHeight,
        behavior: 'smooth'
      });
    }
  }

  // Handle message actions
  function handleMessageAction(event: CustomEvent) {
    const { action, messageId } = event.detail;
    console.log(`Action ${action} on message ${messageId}`);
  }
</script>

<div class="telegram-feed">
  <!-- Header -->
  <div class="feed-header">
    <div class="header-left">
      <h2 class="feed-title">🔴 LIVE TELEGRAM FEED</h2>
      <div class="connection-status" class:connected={isConnected}>
        {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
      </div>
    </div>
    <div class="header-right">
      <div class="stats-summary">
        <span class="stat-item">
          <span class="stat-value">{stats.total}</span>
          <span class="stat-label">Messages</span>
        </span>
        <span class="stat-item">
          <span class="stat-value threat-high">{stats.threatBreakdown.high}</span>
          <span class="stat-label">High Threat</span>
        </span>
      </div>
    </div>
  </div>

  <!-- Message feed -->
  <div class="feed-content">
    <div 
      class="message-container"
      bind:this={feedContainer}
      on:scroll={handleScroll}
    >
      {#if messages.length === 0}
        <div class="empty-state">
          <div class="empty-icon">🛰️</div>
          <h3>Monitoring Global Communications</h3>
          <p>Waiting for intelligence signals...</p>
        </div>
      {:else}
        {#each messages as message (message.id)}
          <MessageCard {message} on:action={handleMessageAction} />
        {/each}
      {/if}
    </div>

    <!-- Scroll to bottom button -->
    {#if !isAtBottom && messages.length > 0}
      <button 
        class="scroll-bottom-btn"
        on:click={scrollToBottom}
        transition:slide={{ duration: 200 }}
      >
        ⬇️ New messages
      </button>
    {/if}
  </div>
</div>

<style>
  .telegram-feed {
    display: flex;
    flex-direction: column;
    height: 100vh;
    background: var(--osint-bg-primary);
    color: var(--osint-text-primary);
    font-family: 'Inter', system-ui, sans-serif;
  }

  .feed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    background: var(--osint-surface);
    border-bottom: 1px solid var(--osint-border);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .feed-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--osint-accent-cyan);
  }

  .connection-status {
    font-size: 0.875rem;
    color: var(--osint-accent-red);
  }

  .connection-status.connected {
    color: var(--osint-accent-green);
  }

  .stats-summary {
    display: flex;
    gap: 1.5rem;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--osint-text-primary);
  }

  .stat-value.threat-high {
    color: var(--osint-accent-red);
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--osint-text-muted);
    text-transform: uppercase;
  }

  .feed-content {
    flex: 1;
    position: relative;
    overflow: hidden;
  }

  .message-container {
    height: 100%;
    overflow-y: auto;
    scroll-behavior: smooth;
    padding: 1rem;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    text-align: center;
    color: var(--osint-text-muted);
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
    opacity: 0.6;
  }

  .empty-state h3 {
    margin: 0 0 0.5rem 0;
    color: var(--osint-text-secondary);
  }

  .scroll-bottom-btn {
    position: absolute;
    bottom: 1rem;
    left: 50%;
    transform: translateX(-50%);
    padding: 0.75rem 1.5rem;
    background: var(--osint-accent-cyan);
    color: var(--osint-bg-primary);
    border: none;
    border-radius: 24px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: var(--osint-shadow-card-elevated);
    z-index: 10;
  }
</style> 