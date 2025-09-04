<script>
  import { onMount } from 'svelte';
  import { webSocketStore } from '$lib/stores/websocket';
  import { filterStore } from '$lib/stores/filters';
  import MessageCard from './MessageCard.svelte';

  let filteredMessages = [];
  let wsState = null;
  let filterState = null;

  // Subscribe to stores
  onMount(() => {
    console.log('🔴 TelegramFeed component initialized');
    
    // Subscribe to WebSocket store
    const unsubscribeWS = webSocketStore.subscribe(value => {
      wsState = value;
      console.log('📡 WebSocket state updated:', value);
    });

    // Subscribe to filter store
    const unsubscribeFilter = filterStore.subscribe(value => {
      filterState = value;
      console.log('🔍 Filter state updated:', value);
    });

    // Connect WebSocket
    webSocketStore.connect();

    // Cleanup function
    return () => {
      unsubscribeWS();
      unsubscribeFilter();
    };
  });

  // Filter messages based on current filter state
  $: if (wsState && filterState) {
    filteredMessages = wsState.messages.filter(message => {
      // Apply filters
      if (filterState.threatLevel && message.threatLevel !== filterState.threatLevel) {
        return false;
      }
      if (filterState.channel && message.channel !== filterState.channel) {
        return false;
      }
      if (filterState.searchTerm && !message.content.toLowerCase().includes(filterState.searchTerm.toLowerCase())) {
        return false;
      }
      return true;
    });
  } else if (wsState) {
    filteredMessages = wsState.messages;
  }

  function handleMessageAction(event) {
    console.log('Message action:', event.detail);
    // Handle message actions like flag, save, etc.
  }
</script>

<div class="telegram-feed">
  <div class="panel">
    <div class="feed-header">
      <h1>Live Intelligence Feed</h1>
      <div class="connection-status">
        <span class="status-indicator {wsState?.connected ? 'active' : 'inactive'}">
          <div class="status-dot"></div>
          {wsState?.connected ? 'Connected' : 'Disconnected'}
        </span>
        <span class="message-count">
          {filteredMessages.length} messages
        </span>
      </div>
    </div>

    <div class="feed-content">
      {#if filteredMessages.length > 0}
        {#each filteredMessages as message (message.id)}
          <MessageCard {message} on:action={handleMessageAction} />
        {/each}
      {:else}
        <div class="no-messages">
          <p>No messages match current filters</p>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .telegram-feed {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing-lg);
  }

  .feed-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
  }

  .feed-header h1 {
    margin: 0;
    color: var(--text-primary);
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-bold);
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: var(--spacing-lg);
  }

  .message-count {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    font-weight: var(--font-weight-medium);
  }

  .feed-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .no-messages {
    text-align: center;
    padding: var(--spacing-xxl);
    color: var(--text-secondary);
  }

  .no-messages p {
    margin: 0;
    font-style: italic;
  }

  @media (max-width: 768px) {
    .telegram-feed {
      padding: var(--spacing-md);
    }
    
    .feed-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-md);
    }
    
    .connection-status {
      gap: var(--spacing-md);
    }
  }
</style> 