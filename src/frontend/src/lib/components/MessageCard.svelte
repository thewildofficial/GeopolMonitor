<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { TelegramMessage } from '$lib/types';

  export let message: TelegramMessage;

  const dispatch = createEventDispatcher();

  function handleAction(action: string) {
    dispatch('action', {
      action,
      messageId: message.id
    });
  }

  function getThreatClass(level: string): string {
    switch (level) {
      case 'HIGH': return 'threat-high';
      case 'MEDIUM': return 'threat-medium';
      case 'LOW': return 'threat-low';
      default: return 'threat-unknown';
    }
  }

  function getSentimentClass(sentiment: string): string {
    switch (sentiment) {
      case 'positive': return 'sentiment-positive';
      case 'negative': return 'sentiment-negative';
      case 'neutral': return 'sentiment-neutral';
      default: return 'sentiment-unknown';
    }
  }
</script>

<div class="message-card">
  <div class="message-header">
    <div class="channel-info">
      <span class="channel-name">{message.channel}</span>
      <span class="message-time">{new Date(message.timestamp).toLocaleTimeString()}</span>
    </div>
    <div class="message-meta">
      <span class="threat-badge {getThreatClass(message.threatLevel)}">
        {message.threatLevel}
      </span>
      <span class="relevance-score">
        📊 {message.relevanceScore}%
      </span>
    </div>
  </div>

  <div class="message-content">
    <p class="message-text">{message.content}</p>
    
    {#if message.sentiment}
      <div class="sentiment-info">
        <span class="sentiment-label {getSentimentClass(message.sentiment.label)}">
          {message.sentiment.label.toUpperCase()}
        </span>
        <span class="sentiment-score">{Math.round(message.sentiment.score * 100)}%</span>
      </div>
    {/if}

    {#if message.location}
      <div class="location-info">
        <span class="location-icon">📍</span>
        <span class="location-text">
          {message.location.country}
          {#if message.location.region}, {message.location.region}{/if}
        </span>
      </div>
    {/if}

    {#if message.entities && message.entities.length > 0}
      <div class="tags-container">
        {#each message.entities as entity}
          <span class="tag">{entity}</span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="message-actions">
    <button 
      class="action-btn"
      on:click={() => handleAction('archive')}
      title="Archive message"
    >
      📁
    </button>
    <button 
      class="action-btn"
      on:click={() => handleAction('flag')}
      title="Flag for review"
    >
      🚩
    </button>
    <button 
      class="action-btn"
      on:click={() => handleAction('share')}
      title="Share message"
    >
      📤
    </button>
  </div>
</div>

<style>
  .message-card {
    background: var(--osint-surface);
    border: 1px solid var(--osint-border);
    border-radius: 8px;
    margin-bottom: 1rem;
    padding: 1rem;
    transition: all 0.2s ease;
  }

  .message-card:hover {
    border-color: var(--osint-accent-cyan);
    box-shadow: var(--osint-shadow-card);
  }

  .message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .channel-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .channel-name {
    font-weight: 600;
    color: var(--osint-accent-cyan);
  }

  .message-time {
    font-size: 0.875rem;
    color: var(--osint-text-muted);
  }

  .message-meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .threat-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .threat-high {
    background: var(--osint-accent-red);
    color: white;
  }

  .threat-medium {
    background: var(--osint-accent-orange);
    color: white;
  }

  .threat-low {
    background: var(--osint-accent-green);
    color: white;
  }

  .threat-unknown {
    background: var(--osint-text-muted);
    color: white;
  }

  .relevance-score {
    font-size: 0.875rem;
    color: var(--osint-text-secondary);
  }

  .message-content {
    margin-bottom: 1rem;
  }

  .message-text {
    margin: 0 0 0.75rem 0;
    line-height: 1.5;
    color: var(--osint-text-primary);
  }

  .sentiment-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .sentiment-label {
    padding: 0.125rem 0.375rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .sentiment-positive {
    background: var(--osint-accent-green);
    color: white;
  }

  .sentiment-negative {
    background: var(--osint-accent-red);
    color: white;
  }

  .sentiment-neutral {
    background: var(--osint-text-muted);
    color: white;
  }

  .sentiment-score {
    font-size: 0.875rem;
    color: var(--osint-text-secondary);
  }

  .location-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
    color: var(--osint-text-secondary);
    font-size: 0.875rem;
  }

  .tags-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .tag {
    background: var(--osint-bg-secondary);
    color: var(--osint-text-secondary);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    border: 1px solid var(--osint-border);
  }

  .message-actions {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .action-btn {
    background: var(--osint-bg-secondary);
    border: 1px solid var(--osint-border);
    border-radius: 4px;
    padding: 0.5rem;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 1rem;
  }

  .action-btn:hover {
    background: var(--osint-accent-cyan);
    border-color: var(--osint-accent-cyan);
    transform: translateY(-1px);
  }
</style>