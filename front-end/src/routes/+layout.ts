import type {LayoutLoad} from './$types';
import {getPlayers} from '$lib/api/players';

export const load: LayoutLoad = async ({fetch}) => {
    try {
        const playersLite = await getPlayers(fetch);
        return {playersLite};
    } catch {
        return {playersLite: []};
    }
};
