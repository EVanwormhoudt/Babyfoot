import type {PageLoad} from './$types';
import {getPlayers, type PlayerLite} from '$lib/api/players';

function sortPlayers(players: PlayerLite[]): PlayerLite[] {
    return [...players].sort((a, b) => {
        const aActive = a.active !== false;
        const bActive = b.active !== false;
        if (aActive !== bActive) return aActive ? -1 : 1;
        return a.player_name.localeCompare(b.player_name, undefined, {sensitivity: 'base'});
    });
}

export const load: PageLoad = async ({fetch}) => {
    try {
        const players = await getPlayers(fetch);
        return {
            players: sortPlayers(players),
            loadError: null as string | null
        };
    } catch (error) {
        return {
            players: [] as PlayerLite[],
            loadError: error instanceof Error ? error.message : 'Impossible de charger les joueurs'
        };
    }
};
