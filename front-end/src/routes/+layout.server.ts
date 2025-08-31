// src/routes/+layout.server.ts
import type {LayoutServerLoad} from './$types';
import {getPlayers} from '$lib/api/players';

export const load: LayoutServerLoad = async ({fetch, setHeaders}) => {
    const playersLite = await getPlayers(fetch);
    setHeaders({'cache-control': 'public, max-age=60, stale-while-revalidate=300'});
    return {playersLite};
};