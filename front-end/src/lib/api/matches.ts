import {PUBLIC_API_BASE} from '$env/static/public';

export async function getGames(scope = 'all', limit = 10, offset = 0) {
    const url = new URL(`${PUBLIC_API_BASE}/api/games`);
    url.searchParams.append('scope', scope);
    url.searchParams.append('limit', limit.toString());
    url.searchParams.append('offset', offset.toString());
    const res = await fetch(url);
    return res.json();
}

export async function createGame(data: any) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/games`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function getGame(id: number) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/games/${id}`);
    return res.json();
}

export async function updateGame(id: number, data: any) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/games/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    return res.json();
}

export async function deleteGame(id: number) {
    const res = await fetch(`${PUBLIC_API_BASE}/api/games/${id}`, {
        method: 'DELETE'
    });
    return res.ok;
}