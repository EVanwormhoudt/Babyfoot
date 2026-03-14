import {PUBLIC_API_BASE} from '$env/static/public';
import type {GameRead} from "$lib/api/types";

export type F = typeof fetch;


export async function getGames(
    params: {
        scope?: 'all' | 'monthly';
        limit?: number;
        offset?: number;
        start_date?: string;
        end_date?: string;
    },
    fetcher: typeof fetch // REQUIRED: inject fetch from load
): Promise<{ items: GameRead[]; total: number }> {
    const f = fetcher ?? fetch; // <= SAFE DEFAULT

    const qs = new URLSearchParams({
        scope: params.scope ?? 'all',
        limit: String(params.limit ?? 10),
        offset: String(params.offset ?? 0),
        ...(params.start_date ? {start_date: params.start_date} : {}),
        ...(params.end_date ? {end_date: params.end_date} : {})
    });

    const res = await f(`${PUBLIC_API_BASE}/api/games?${qs.toString()}`, {
        headers: {accept: 'application/json'}
    });
    if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(`Failed to load games (${res.status}) ${text}`);
    }
    return await res.json() as { items: GameRead[]; total: number };
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
