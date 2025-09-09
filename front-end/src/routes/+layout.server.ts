// src/routes/+layout.server.ts
import type {LayoutServerLoad} from './$types';
import {getPlayers} from '$lib/api/players';

export const load: LayoutServerLoad = async ({fetch, setHeaders}) => {
    const playersLite = await getPlayers(fetch);
    return {playersLite};
};