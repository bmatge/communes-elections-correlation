import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		// Suppress sourcemap warnings from duckdb-wasm worker files
		sourcemapIgnoreList: (sourcePath) => sourcePath.includes('duckdb-wasm')
	}
});
