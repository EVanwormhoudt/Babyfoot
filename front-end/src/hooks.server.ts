import type {HandleFetch} from '@sveltejs/kit';
import {buildInternalApiRequest, isSameOriginApiRequest, normalizeBase} from '$lib/server/api-proxy';
import {env} from '$env/dynamic/private';

export const handleFetch: HandleFetch = async ({event, request, fetch}) => {
    const internalApiBase = normalizeBase(env.INTERNAL_API_BASE);
    if (!isSameOriginApiRequest(event, request) || !internalApiBase) {
        return fetch(request);
    }

    return fetch(buildInternalApiRequest(event, request));
};
