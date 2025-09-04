<script>
	import { cn } from '$lib/utils';

	export let className = '';
</script>

<div class={cn('rounded-lg border border-gray-700 bg-gray-800 text-white shadow-sm', className)} {...$$restProps}>
	<slot />
</div> 