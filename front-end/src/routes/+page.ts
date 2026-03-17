// src/routes/+page.ts
import type {PageLoad} from './$types';
import {getGames} from '$lib/api/matches';
import {getLeaderboard} from '$lib/api/players';
import type {GameRead} from '$lib/api/types';

export type Player = {
    id: number;
    player_name?: string;
    player_color?: string;
    active?: boolean;
};

type LeaderboardRating = {
    mu_overall?: number;
    mu_monthly?: number;
    mu_yearly?: number;
};

export type LeaderboardRow = {
    id: number;
    active: boolean;
    player_name: string;
    wins: number;
    games_played: number;
    mu: number;
    rating?: LeaderboardRating | null;
};

function isTenZero(game: GameRead): boolean {
    return (
        (Number(game.result_team1) === 10 && Number(game.result_team2) === 0) ||
        (Number(game.result_team1) === 0 && Number(game.result_team2) === 10)
    );
}

export const load: PageLoad = async ({fetch}) => {
    const pageSize = 200;
    const {items, total} = await getGames({
        scope: 'all',
        limit: pageSize,
        offset: 0
    }, fetch);

    const firstBatch = (items ?? []).sort(
        (a, b) => new Date(b.game_timestamp).getTime() - new Date(a.game_timestamp).getTime()
    );
    const games = firstBatch.slice(0, 5);
    let lastTenZeroMatch: GameRead | null = firstBatch.find(isTenZero) ?? null;

    if (!lastTenZeroMatch) {
        for (let offset = pageSize; offset < total; offset += pageSize) {
            const {items: nextItems} = await getGames(
                {scope: 'all', limit: pageSize, offset},
                fetch
            );
            const nextBatch = (nextItems ?? []).sort(
                (a, b) => new Date(b.game_timestamp).getTime() - new Date(a.game_timestamp).getTime()
            );
            const match = nextBatch.find(isTenZero);
            if (match) {
                lastTenZeroMatch = match;
                break;
            }
        }
    }

    const lb = await getLeaderboard('monthly', {}, fetch);
    const top3: LeaderboardRow[] = Array.isArray(lb) ? lb.slice(0, 3) : [];

    return {
        games,
        lastTenZeroMatch,
        top3: top3.filter((p) => (p?.wins ?? 0) > 0)
    };
};
