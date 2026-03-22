import {sveltekit} from '@sveltejs/kit/vite';
import {defineConfig} from 'vite';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        host: true,
        allowedHosts: ['babyfoot.vanwormhoudt.com', 'localhost', '127.0.0.1'],
    },
});
