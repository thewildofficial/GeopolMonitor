<script >
	import { cn } from '$lib/utils';

	export let className= '';
</script>

<p class={cn('text-sm text-muted-foreground', className)} {...$$restProps}>
	<slot />
</p> 