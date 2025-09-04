<script >
	import { cn } from '$lib/utils';

	export let className= '';
	export let tag: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' = 'h3';
</script>

<svelte:element
	this={tag}
	class={cn('text-2xl font-semibold leading-none tracking-tight', className)}
	{...$$restProps}
>
	<slot />
</svelte:element> 