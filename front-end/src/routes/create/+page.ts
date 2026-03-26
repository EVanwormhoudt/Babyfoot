import type {PageLoad} from './$types';
import {getPlayers} from "$lib/api/players";
import {getGames} from "$lib/api/matches";
import type {GameRead} from "$lib/api/types";

export const load: PageLoad = async ({fetch, url}) => {
    const playersLiteRaw = await getPlayers(fetch);

    const now = new Date();
    const year = now.getFullYear();
    const start_date = `${year}-01-01T00:00:00`;
    const end_date = `${year + 1}-01-01T00:00:00`;

    const yearlyGames: GameRead[] = [];
    const pageSize = 200;
    for (let offset = 0; ; offset += pageSize) {
        const {items, total} = await getGames(
            {scope: 'all', limit: pageSize, offset, start_date, end_date},
            fetch
        );
        yearlyGames.push(...(items ?? []));
        if (offset + pageSize >= total || (items?.length ?? 0) === 0) break;
    }

    const playedYearCount = new Map<number, number>();
    for (const game of yearlyGames) {
        for (const team of game.teams ?? []) {
            const prev = playedYearCount.get(team.player_id) ?? 0;
            playedYearCount.set(team.player_id, prev + 1);
        }
    }

    const playersLite = playersLiteRaw.map((player) => {
        const matches_this_year = playedYearCount.get(player.id) ?? 0;
        return {
            ...player,
            played_this_year: matches_this_year > 0,
            matches_this_year
        };
    });

    return {playersLite};
};
