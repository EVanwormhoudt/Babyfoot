// src/routes/+page.ts
import type {PageLoad} from './$types';
import {getGames} from '$lib/api/matches';
import {getLeaderboard} from '$lib/api/players';

// ——— Types from your backend (and a loose LB row) ———
export type Player = {
    player_name?: string;
    color?: string;

};

export type TeamRead = {
    id: number;
    player?: Player;
    team_number?: number;
    rating?: any;
};

export type GameRead = {
    id: number;
    game_timestamp: string; // ISO
    result_team1: number;
    result_team2: number;
    teams: TeamRead[];
};

export type LeaderboardRow = {
    name?: string;
    username?: string;
    player_name?: string;
    display_name?: string;
    rating?: number;
    elo?: number;
    points?: number;
    score?: number;
    wins?: number;
    losses?: number;
    avatar_url?: string;

};

export const load: PageLoad = async ({fetch}) => {
    // Last 5 matches
    const data: { items: GameRead[]; total: number } = await getGames({
        scope: 'all',
        limit: 5,
        offset: 0
    }, fetch);

    let games = data.items ?? [];
    games = games.sort((a, b) => new Date(b.game_timestamp).getTime() - new Date(a.game_timestamp).getTime());
    // Monthly leaderboard, take top 3
    const lb = await getLeaderboard('monthly', {}, fetch);
    let top3: LeaderboardRow[] = [];

    if (Array.isArray(lb)) {
        top3 = lb.slice(0, 3);
    } else if (lb?.players && Array.isArray(lb.players)) {
        top3 = lb.players.slice(0, 3);
    } else if (lb?.data && Array.isArray(lb.data)) {
        top3 = lb.data.slice(0, 3);
    }

    top3 = top3.filter((p) => p && (p.wins ?? 0) > 0);
    return {games, top3};
};
