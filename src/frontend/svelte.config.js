import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// Configure adapter to build static files for Flask integration
		adapter: adapter({
			// Build output goes to Flask's static directory
			pages: '../web/static/svelte-build',
			assets: '../web/static/svelte-build',
			fallback: 'index.html',
			precompress: false,
			strict: false
		}),
		
		// Configure paths for Flask integration - removed assets path for dev server compatibility
		paths: {
			base: ''
		},
		
		// API routes will proxy to Flask backend
		alias: {
			$lib: 'src/lib',
			$components: 'src/lib/components',
			$stores: 'src/lib/stores',
			$types: 'src/lib/types',
			$utils: 'src/lib/utils'
		},
		
		// Since we're building for static deployment with Flask backend
		prerender: {
			handleMissingId: 'warn',
			handleHttpError: 'warn',
			entries: ['/', '/telegram']
		}
	}
};

export default config; 