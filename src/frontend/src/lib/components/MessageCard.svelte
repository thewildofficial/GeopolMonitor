<script>
  import { createEventDispatcher } from 'svelte';

  export let message;

  const dispatch = createEventDispatcher();

  function handleAction(action) {
    dispatch('action', {
      action,
      messageId: message.id
    });
  }
</script>

<div class="feed-item">
  <div class="feed-item-header">
    <div class="feed-item-avatar">
      <div class="avatar-placeholder">
        {message.channel.charAt(0).toUpperCase()}
      </div>
    </div>
    <div class="feed-item-meta">
      <div class="feed-item-source">
        {message.channel}
      </div>
      <div class="feed-item-timestamp">
        {new Date(message.timestamp).toLocaleTimeString()}
      </div>
    </div>
    <div class="feed-item-badges">
      <span class="tag tag-{message.threatLevel.toLowerCase()}">
        {message.threatLevel}
      </span>
      <span class="relevance-score">
        {message.relevanceScore}%
      </span>
    </div>
  </div>

  <div class="feed-item-body">
    <p class="feed-item-content">
      {message.content}
    </p>
    
    {#if message.sentiment}
      <div class="feed-item-sentiment">
        <span class="sentiment-label sentiment-{message.sentiment.label}">
          {message.sentiment.label}
        </span>
        <span class="sentiment-score">
          {Math.round(message.sentiment.score * 100)}%
        </span>
      </div>
    {/if}

    {#if message.location}
      <div class="feed-item-location">
        <svg class="location-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        <span class="location-text">
          {message.location.country}{#if message.location.region}, {message.location.region}{/if}
        </span>
      </div>
    {/if}

    {#if message.entities && message.entities.length > 0}
      <div class="feed-item-entities">
        {#each message.entities as entity}
          <span class="entity-tag">{entity}</span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="feed-item-footer">
    <div class="feed-item-actions">
      <button 
        class="action-button"
        on:click={() => handleAction('archive')}
        title="Archive message"
      >
        <svg class="action-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM6.24 5h11.52l.83 1H5.42l.82-1zM5 19V8h14v11H5z"/>
          <path d="M9 10v2h6v-2H9z"/>
        </svg>
      </button>
      <button 
        class="action-button"
        on:click={() => handleAction('flag')}
        title="Flag for review"
      >
        <svg class="action-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z"/>
        </svg>
      </button>
      <button 
        class="action-button"
        on:click={() => handleAction('share')}
        title="Share message"
      >
        <svg class="action-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/>
        </svg>
      </button>
    </div>
  </div>
</div>

<style>
  .feed-item {
    background-color: transparent;
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--border-primary);
    transition: all 0.2s ease;
  }

  .feed-item:hover {
    background-color: rgba(55, 65, 81, 0.3);
  }

  .feed-item-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  .feed-item-avatar {
    flex-shrink: 0;
  }

  .avatar-placeholder {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: var(--background-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--text-accent);
  }

  .feed-item-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .feed-item-source {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
  }

  .feed-item-timestamp {
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-regular);
    color: var(--text-secondary);
  }

  .feed-item-badges {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .relevance-score {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  .feed-item-body {
    margin-bottom: var(--spacing-md);
  }

  .feed-item-content {
    font-size: var(--font-size-md);
    font-weight: var(--font-weight-regular);
    color: var(--text-primary);
    line-height: 1.5;
    margin-bottom: var(--spacing-sm);
  }

  .feed-item-sentiment {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  .sentiment-label {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
    text-transform: uppercase;
  }

  .sentiment-positive {
    background-color: rgba(16, 185, 129, 0.2);
    color: var(--status-active);
  }

  .sentiment-negative {
    background-color: rgba(249, 115, 22, 0.2);
    color: var(--status-high);
  }

  .sentiment-neutral {
    background-color: rgba(107, 114, 128, 0.2);
    color: var(--status-inactive);
  }

  .sentiment-score {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  .feed-item-location {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-sm);
  }

  .location-icon {
    width: 14px;
    height: 14px;
    color: var(--text-secondary);
  }

  .location-text {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  .feed-item-entities {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-sm);
  }

  .entity-tag {
    background-color: var(--background-tertiary);
    color: var(--text-secondary);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-medium);
  }

  .feed-item-footer {
    display: flex;
    justify-content: flex-end;
  }

  .feed-item-actions {
    display: flex;
    gap: var(--spacing-xs);
  }

  .action-button {
    background: transparent;
    border: none;
    padding: var(--spacing-xs);
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 4px;
  }

  .action-button:hover {
    background-color: var(--background-tertiary);
  }

  .action-icon {
    width: 14px;
    height: 14px;
    color: var(--text-secondary);
  }

  .action-button:hover .action-icon {
    color: var(--text-accent);
  }
</style>