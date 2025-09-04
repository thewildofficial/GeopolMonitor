import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	
	// Development server configuration
	server: {
		port: 5173,
		host: true,
		// Proxy API calls to Flask backend during development
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				secure: false
			},
			'/ws': {
				target: 'ws://localhost:8000',
				changeOrigin: true,
				ws: true
			}
		}
	},
	
	// Build configuration
	build: {
		target: 'es2020',
		sourcemap: true,
		rollupOptions: {
			output: {
				// Ensure consistent chunk naming for Flask integration
				chunkFileNames: 'chunks/[name]-[hash].js',
				assetFileNames: 'assets/[name]-[hash][extname]'
			}
		}
	},
	
	// Optimization
	optimizeDeps: {
		include: ['chart.js', 'maplibre-gl', 'd3', '@turf/turf']
	},
	
	// Define globals for development
	define: {
		global: 'globalThis'
	}
}); 