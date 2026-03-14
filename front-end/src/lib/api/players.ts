// src/lib/api/players.ts
import {PUBLIC_API_BASE} from '$env/static/public';

export type Scope = 'monthly' | 'yearly' | 'overall';
export type F = typeof fetch;
export type LeaderboardOpts = { year?: number; month?: number };
export type TeammateStat = {
    player_id: number;
    player_name: string;
    games_played: number;
    wins: number;
    win_rate: number;
};

export type PlayerStats = {
    games_played: number;
    wins: number;
    win_rate: number;
    average_team_score: number;
    average_opponent_score: number;
    best_teammate?: TeammateStat | null;
    worst_teammate?: TeammateStat | null;
    current_win_streak: number;
    longest_win_streak: number;
};

export async function getPlayers(eventFetch?: F) {
    const f = eventFetch ?? fetch;
    // If you can, add a fields param on the backend to keep this light
    const res = await f(`${PUBLIC_API_BASE}/api/players`); // e.g. ...?fields=id,name,color,active
    if (!res.ok) throw new Error('Failed to load players');
    return res.json() as Promise<Array<{ id: number; player_name: string; player_color: string; active?: boolean }>>;
}

export async function createPlayer(data: { player_name: string; player_color: string }, eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function getPlayer(id: number, eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}`);
    return res.json();
}

export async function updatePlayer(id: number, data: any, eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function deletePlayer(id: number, eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}`, {method: 'DELETE'});
    return res.ok;
}

export async function getPlayerHistory(id: number, eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}/history`);
    return res.json();
}


export async function getLeaderboard(
    type: Scope = 'monthly',
    optsOrFetch?: LeaderboardOpts | F,
    maybeFetch?: F
) {
    const opts: LeaderboardOpts =
        typeof optsOrFetch === 'function' ? {} : (optsOrFetch ?? {});
    const f: F =
        typeof optsOrFetch === 'function' ? (optsOrFetch as F) : (maybeFetch ?? fetch);

    const params = new URLSearchParams({leaderboard_type: type});

    if (typeof opts.year === 'number' && Number.isFinite(opts.year)) {
        params.set('year', String(opts.year));
    }
    if (type === 'monthly' && typeof opts.month === 'number' && opts.month >= 1 && opts.month <= 12) {
        params.set('month', String(opts.month));
    }

    const res = await f(`${PUBLIC_API_BASE}/api/players/leaderboard?${params.toString()}`);
    if (!res.ok) throw new Error(`Failed to load leaderboard: ${res.status}`);
    return res.json();
}

export async function getPlayerStats(id: number, scope = 'overall', eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}/stats?scope=${scope}`);
    if (!res.ok) {
        throw new Error(`Failed to load player stats (${res.status})`);
    }
    return res.json() as Promise<PlayerStats>;
}
