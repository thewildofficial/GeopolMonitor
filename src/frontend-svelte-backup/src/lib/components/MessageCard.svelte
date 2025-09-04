<script>
  import { createEventDispatcher } from 'svelte';
  import { Card, CardHeader, CardContent, CardFooter, Badge, Button } from '$lib/components/ui';

  export let message;

  const dispatch = createEventDispatcher();

  function handleAction(action) {
    dispatch('action', {
      action,
      messageId: message.id
    });
  }

  // Get badge variant based on threat level
  function getThreatBadgeVariant(level) {
    switch (level?.toLowerCase()) {
      case 'high': return 'destructive';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'outline';
    }
  }

  // Get sentiment badge variant
  function getSentimentBadgeVariant(sentiment) {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'default';
      case 'negative': return 'destructive';
      case 'neutral': return 'secondary';
      default: return 'outline';
    }
  }
</script>

<Card class="feed-item bg-transparent border-b border-gray-700 hover:bg-gray-800/30 transition-colors">
  <CardHeader class="pb-3">
    <div class="feed-header-content flex items-center gap-3">
      <div class="feed-item-avatar">
        <div class="avatar-placeholder w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-sm font-semibold text-gray-300">
          {message.channel.charAt(0).toUpperCase()}
        </div>
      </div>
      <div class="feed-item-meta flex-1 flex flex-col gap-0.5">
        <div class="feed-item-source text-sm font-semibold text-white">
          {message.channel}
        </div>
        <div class="feed-item-timestamp text-xs text-gray-400">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
      <div class="feed-item-badges flex items-center gap-2">
        <Badge variant={getThreatBadgeVariant(message.threatLevel)}>
          {message.threatLevel}
        </Badge>
        <span class="relevance-score text-xs text-gray-400">
          {message.relevanceScore}%
        </span>
      </div>
    </div>
  </CardHeader>

  <CardContent class="py-3">
    <p class="feed-item-content text-sm text-white leading-relaxed mb-3">
      {message.content}
    </p>
    
    {#if message.sentiment}
      <div class="feed-item-sentiment flex items-center gap-2 mb-3">
        <Badge variant={getSentimentBadgeVariant(message.sentiment.label)}>
          {message.sentiment.label}
        </Badge>
        <span class="sentiment-score text-xs text-gray-400">
          {Math.round(message.sentiment.score * 100)}%
        </span>
      </div>
    {/if}

    {#if message.location}
      <div class="feed-item-location flex items-center gap-1 mb-3">
        <svg class="location-icon w-3.5 h-3.5 text-gray-400" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        <span class="location-text text-xs text-gray-400">
          {message.location.country}{#if message.location.region}, {message.location.region}{/if}
        </span>
      </div>
    {/if}

    {#if message.entities && message.entities.length > 0}
      <div class="feed-item-entities flex flex-wrap gap-1 mb-3">
        {#each message.entities as entity}
          <Badge variant="outline" class="text-xs">{entity}</Badge>
        {/each}
      </div>
    {/if}
  </CardContent>

  <CardFooter class="pt-3 justify-end">
    <div class="feed-item-actions flex gap-1">
      <Button 
        variant="ghost" 
        size="sm"
        on:click={() => handleAction('archive')}
        title="Archive message"
        class="h-8 w-8 p-0"
      >
        <svg class="action-icon w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM6.24 5h11.52l.83 1H5.42l.82-1zM5 19V8h14v11H5z"/>
          <path d="M9 10v2h6v-2H9z"/>
        </svg>
      </Button>
      <Button 
        variant="ghost" 
        size="sm"
        on:click={() => handleAction('flag')}
        title="Flag for review"
        class="h-8 w-8 p-0"
      >
        <svg class="action-icon w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z"/>
        </svg>
      </Button>
      <Button 
        variant="ghost" 
        size="sm"
        on:click={() => handleAction('share')}
        title="Share message"
        class="h-8 w-8 p-0"
      >
        <svg class="action-icon w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.50-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/>
        </svg>
      </Button>
    </div>
  </CardFooter>
</Card>

<style>
  /* Custom styles for icons and any remaining layout adjustments */
  .action-icon {
    transition: color 0.2s ease;
  }
</style>