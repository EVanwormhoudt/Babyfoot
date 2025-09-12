import type {PageServerLoad} from './$types';
import {getGames} from '$lib/api/matches';

export const load: PageServerLoad = async ({fetch, url}) => {
    const scope = (url.searchParams.get('scope') as 'all' | 'monthly') ?? 'all';
    const limit = Number(url.searchParams.get('limit') ?? 10);
    const page = Math.max(1, Number(url.searchParams.get('page') ?? 1));
    const offset = (page - 1) * limit;
    const start_date = url.searchParams.get('start_date') ?? undefined;
    const end_date = url.searchParams.get('end_date') ?? undefined;

    const {items, total} = await getGames(
        {scope, limit, offset, start_date, end_date},
        fetch // pass SvelteKit SSR fetch
    );

    return {
        items,
        total,
        page,
        pageCount: Math.max(1, Math.ceil(total / limit)),
        limit,
        scope,
        start_date,
        end_date
    };
};
