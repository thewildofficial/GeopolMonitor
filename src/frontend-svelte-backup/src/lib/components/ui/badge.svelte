<script >
	import { cn } from '$lib/utils';
	import { cva } from 'class-variance-authority';

	const badgeVariants = cva(
		'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
		{
			variants: {
				variant: {
					default: 'border-transparent bg-primary text-primary-foreground hover:bg-primary/80',
					secondary: 'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80',
					destructive: 'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80',
					outline: 'text-gray-100',
					// OSINT-specific variants
					high: 'border-transparent bg-orange-500 text-white hover:bg-orange-600',
					medium: 'border-transparent bg-yellow-500 text-black hover:bg-yellow-600',
					low: 'border-transparent bg-blue-500 text-white hover:bg-blue-600',
					active: 'border-transparent bg-green-500 text-white hover:bg-green-600'
				}
			},
			defaultVariants: {
				variant: 'default'
			}
		}
	);

	export let variant = 'default';
	export let className= '';
</script>

<div class={cn(badgeVariants({ variant }), className)} {...$$restProps}>
	<slot />
</div> 