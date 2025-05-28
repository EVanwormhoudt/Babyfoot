import {PUBLIC_API_BASE} from '$env/static/public';

export async function getPlayers(fetch: any) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players`);
    return res.json();
}

export async function createPlayer(data: { player_name: string; player_color: string }) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function getPlayer(id: number) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/${id}`);
    return res.json();
}

export async function updatePlayer(id: number, data: any) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function deletePlayer(id: number) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/${id}`, {
        method: 'DELETE'
    });
    return res.ok;
}

export async function getPlayerHistory(id: number) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/${id}/history`);
    return res.json();
}

export async function getLeaderboard(type: 'monthly' | 'yearly' | 'overall' = 'monthly') {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/leaderboard/?leaderboard_type=${type}`);
    return res.json();
}

export async function getPlayerStats(id: number, scope = 'overall') {
    const res = await fetch(`${PUBLIC_API_BASE}/api/players/${id}/stats?scope=${scope}`);
    return res.json();
}