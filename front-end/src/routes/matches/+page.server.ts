import type {PageServerLoad} from './$types';
import {getGames} from '$lib/api/matches';
import {getPlayers, type PlayerLite} from '$lib/api/players';

function sortPlayers(players: PlayerLite[]): PlayerLite[] {
    return [...players].sort((a, b) => {
        const aActive = a.active !== false;
        const bActive = b.active !== false;
        if (aActive !== bActive) return aActive ? -1 : 1;
        return a.player_name.localeCompare(b.player_name, undefined, {sensitivity: 'base'});
    });
}

export const load: PageServerLoad = async ({fetch, url}) => {
    const scope = (url.searchParams.get('scope') as 'all' | 'monthly') ?? 'all';
    const parsedLimit = Number(url.searchParams.get('limit'));
    const limit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 50) : 10;
    const parsedPage = Number(url.searchParams.get('page'));
    const page = Number.isFinite(parsedPage) && parsedPage > 0 ? Math.floor(parsedPage) : 1;
    const offset = (page - 1) * limit;
    const start_date = url.searchParams.get('start_date') ?? undefined;
    const end_date = url.searchParams.get('end_date') ?? undefined;
    const parsedPlayerId = Number(url.searchParams.get('player_id'));
    const player_id = Number.isFinite(parsedPlayerId) && parsedPlayerId > 0
        ? Math.floor(parsedPlayerId)
        : undefined;

    const [players, {items, total}] = await Promise.all([
        getPlayers(fetch),
        getGames(
            {scope, limit, offset, start_date, end_date, player_id},
            fetch // pass SvelteKit SSR fetch
        )
    ]);

    return {
        items,
        total,
        players: sortPlayers(players),
        page,
        pageCount: Math.max(1, Math.ceil(total / limit)),
        limit,
        scope,
        start_date,
        end_date,
        player_id: player_id ?? null
    };
};
