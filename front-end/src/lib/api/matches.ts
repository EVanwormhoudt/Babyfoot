import {PUBLIC_API_BASE} from '$env/static/public';
import type {GameRead} from "$lib/api/types";

export type F = typeof fetch;

export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
    }
}

async function readApiError(res: Response, fallback: string): Promise<string> {
    try {
        const body = await res.clone().json();
        if (typeof body?.detail === 'string' && body.detail.trim()) {
            return body.detail;
        }
    } catch {
        // ignore non-JSON payloads
    }

    try {
        const text = await res.text();
        if (text.trim()) {
            return text;
        }
    } catch {
        // ignore unreadable/empty body
    }

    return fallback;
}

export async function getGames(
    params: {
        scope?: 'all' | 'monthly';
        limit?: number;
        offset?: number;
        start_date?: string;
        end_date?: string;
    },
    fetcher?: F
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
        throw new ApiError(
            res.status,
            await readApiError(res, `Impossible de charger les matchs (${res.status})`)
        );
    }
    return await res.json() as { items: GameRead[]; total: number };
}

export async function createGame(data: unknown, fetcher?: F): Promise<GameRead> {
    const f = fetcher ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/games`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        throw new ApiError(
            res.status,
            await readApiError(res, `Impossible de creer le match (${res.status})`)
        );
    }
    return await res.json() as GameRead;
}

export async function getGame(id: number, fetcher?: F): Promise<GameRead> {
    const f = fetcher ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/games/${id}`);
    if (!res.ok) {
        throw new ApiError(
            res.status,
            await readApiError(res, `Impossible de charger le match (${res.status})`)
        );
    }
    return await res.json() as GameRead;
}

export async function updateGame(id: number, data: unknown, fetcher?: F): Promise<GameRead> {
    const f = fetcher ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/games/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        throw new ApiError(
            res.status,
            await readApiError(res, `Impossible de modifier le match (${res.status})`)
        );
    }
    return await res.json() as GameRead;
}

export async function deleteGame(id: number, fetcher?: F): Promise<boolean> {
    const f = fetcher ?? fetch;
    const res = await f(`${PUBLIC_API_BASE}/api/games/${id}`, {
        method: 'DELETE'
    });
    return res.ok;
}
