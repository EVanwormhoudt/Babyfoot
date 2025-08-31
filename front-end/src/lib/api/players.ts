// src/lib/api/players.ts
import {PUBLIC_API_BASE} from '$env/static/public';

type F = typeof fetch;

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

export async function getLeaderboard(type: 'monthly' | 'yearly' | 'overall' = 'monthly', eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/leaderboard?leaderboard_type=${type}`);
    return res.json();
}

export async function getPlayerStats(id: number, scope = 'overall', eventFetch?: F) {
    const f = eventFetch ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/players/${id}/stats?scope=${scope}`);
    return res.json();
}
