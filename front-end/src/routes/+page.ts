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

export const load: PageLoad = async ({fetch}) => {
    const {items, total: _total} = await getGames({
        scope: 'all',
        limit: 5,
        offset: 0
    }, fetch);

    let games = items ?? [];
    games = games.sort((a, b) => new Date(b.game_timestamp).getTime() - new Date(a.game_timestamp).getTime());

    const lb = await getLeaderboard('monthly', {}, fetch);
    const top3: LeaderboardRow[] = Array.isArray(lb) ? lb.slice(0, 3) : [];

    return {
        games,
        top3: top3.filter((p) => (p?.wins ?? 0) > 0)
    };
};
