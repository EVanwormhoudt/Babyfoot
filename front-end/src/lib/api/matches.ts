import {PUBLIC_API_BASE} from '$env/static/public';

export async function getGames({
                                   scope = 'all',
                                   limit = 10,
                                   offset = 0,
                                   start_date,
                                   end_date
                               }: {
    scope?: 'all' | 'monthly';
    limit?: number;
    offset?: number;
    start_date?: string;
    end_date?: string;
}) {
    const url = new URL(`${PUBLIC_API_BASE}/api/games`);
    url.searchParams.set('scope', scope);
    url.searchParams.set('limit', String(limit));
    url.searchParams.set('offset', String(offset));
    if (start_date) url.searchParams.set('start_date', start_date);
    if (end_date) url.searchParams.set('end_date', end_date);


    const res = await fetch(url, {headers: {'accept': 'application/json'}});
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json(); // List[GameRead]
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