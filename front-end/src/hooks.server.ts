import {env} from '$env/dynamic/private';
import type {HandleFetch} from '@sveltejs/kit';

function normalizeBase(value: string | undefined): string | null {
    if (!value) return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    return trimmed.replace(/\/$/, '');
}

export const handleFetch: HandleFetch = async ({event, request, fetch}) => {
    const requestUrl = new URL(request.url);
    const isSameOriginApiRequest =
        requestUrl.origin === event.url.origin &&
        (requestUrl.pathname === '/api' || requestUrl.pathname.startsWith('/api/'));

    const internalApiBase = normalizeBase(env.INTERNAL_API_BASE);
    if (!isSameOriginApiRequest || !internalApiBase) {
        return fetch(request);
    }

    const targetUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, `${internalApiBase}/`);
    return fetch(new Request(targetUrl, request));
};
