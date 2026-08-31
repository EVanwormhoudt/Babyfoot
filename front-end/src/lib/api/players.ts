// src/lib/api/players.ts
import { apiFetch, type Fetcher } from '$lib/api/client';

export type Scope = 'monthly' | 'yearly' | 'overall';
export type F = Fetcher;
export type LeaderboardOpts = { year?: number; month?: number };
export type StatsOpts = { year?: number; month?: number };
export type PlayerLite = {
    id: number;
    player_name: string;
    player_color: string;
    active?: boolean;
    last_game_timestamp?: string | null;
};
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

export type PlayerRatingHistoryPoint = {
    date: string;
    mu: number | null;
    sigma: number | null;
    rank: number;
    rank_type: Scope;
};

async function readApiError(res: Response, fallback: string): Promise<string> {
    try {
        const body = await res.json();
        if (typeof body?.detail === 'string' && body.detail.trim()) {
            return body.detail;
        }
    } catch {
        // ignore non-JSON bodies
    }

    try {
        const text = await res.text();
        if (text.trim()) return text;
    } catch {
        // ignore empty body
    }
    return fallback;
}

export async function getPlayers(eventFetch?: F) {
    // If you can, add a fields param on the backend to keep this light
    const res = await apiFetch('/players', {}, eventFetch); // e.g. ...?fields=id,name,color,active
    if (!res.ok) {
        throw new Error(await readApiError(res, 'Impossible de charger les joueurs'));
    }
    return res.json() as Promise<PlayerLite[]>;
}

export async function createPlayer(data: { player_name: string; player_color: string }, eventFetch?: F) {
    const res = await apiFetch('/players', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }, eventFetch);
    if (!res.ok) {
        throw new Error(await readApiError(res, `Impossible de creer le joueur (${res.status})`));
    }
    return res.json() as Promise<PlayerLite>;
}

export async function getPlayer(id: number, eventFetch?: F) {
    const res = await apiFetch(`/players/${id}`, {}, eventFetch);
    return res.json();
}

export async function updatePlayer(id: number, data: any, eventFetch?: F) {
    const res = await apiFetch(`/players/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }, eventFetch);
    if (!res.ok) {
        throw new Error(await readApiError(res, `Impossible de mettre a jour le joueur (${res.status})`));
    }
    return res.json() as Promise<PlayerLite>;
}

export async function deletePlayer(id: number, eventFetch?: F) {
    const res = await apiFetch(`/players/${id}`, {method: 'DELETE'}, eventFetch);
    return res.ok;
}

export async function getPlayerHistory(id: number, eventFetch?: F) {
    const res = await apiFetch(`/players/${id}/history`, {}, eventFetch);
    return res.json();
}

export async function getPlayerRatingHistory(
    id: number,
    ratingType?: Scope,
    optsOrFetch?: StatsOpts | F,
    maybeFetch?: F
) {
    const opts: StatsOpts =
        typeof optsOrFetch === 'function' ? {} : (optsOrFetch ?? {});
    const f: F =
        typeof optsOrFetch === 'function' ? (optsOrFetch as F) : (maybeFetch ?? fetch);

    const params = new URLSearchParams();
    if (ratingType) {
        params.set('rating_type', ratingType);
    }
    if (ratingType && ratingType !== 'overall' && typeof opts.year === 'number' && Number.isFinite(opts.year)) {
        params.set('year', String(opts.year));
    }
    if (ratingType === 'monthly' && typeof opts.month === 'number' && opts.month >= 1 && opts.month <= 12) {
        params.set('month', String(opts.month));
    }
    const query = params.toString();
    const url = query
        ? `/players/${id}/rating-history?${query}`
        : `/players/${id}/rating-history`;

    const res = await apiFetch(url, {}, f);
    if (!res.ok) {
        throw new Error(`Impossible de charger l'historique Elo (${res.status})`);
    }
    return res.json() as Promise<PlayerRatingHistoryPoint[]>;
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

    const res = await apiFetch(`/players/leaderboard?${params.toString()}`, {}, f);
    if (!res.ok) throw new Error(`Impossible de charger le classement : ${res.status}`);
    return res.json();
}

export async function getPlayerStats(
    id: number,
    scope: Scope = 'overall',
    optsOrFetch?: StatsOpts | F,
    maybeFetch?: F
) {
    const opts: StatsOpts =
        typeof optsOrFetch === 'function' ? {} : (optsOrFetch ?? {});
    const f: F =
        typeof optsOrFetch === 'function' ? (optsOrFetch as F) : (maybeFetch ?? fetch);

    const params = new URLSearchParams({scope});
    if (typeof opts.year === 'number' && Number.isFinite(opts.year)) {
        params.set('year', String(opts.year));
    }
    if (scope === 'monthly' && typeof opts.month === 'number' && opts.month >= 1 && opts.month <= 12) {
        params.set('month', String(opts.month));
    }

    const res = await apiFetch(`/players/${id}/stats?${params.toString()}`, {}, f);
    if (!res.ok) {
        throw new Error(`Impossible de charger les statistiques joueur (${res.status})`);
    }
    return res.json() as Promise<PlayerStats>;
}
