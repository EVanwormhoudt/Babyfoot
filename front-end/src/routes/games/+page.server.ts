import type { PageServerLoad } from './$types';
import { getGames } from '$lib/api/matches';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const scope = (url.searchParams.get('scope') as 'all' | 'monthly') ?? 'all';
	const parsedLimit = Number(url.searchParams.get('limit'));
	const limit = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 50) : 10;
	const parsedPage = Number(url.searchParams.get('page'));
	const page = Number.isFinite(parsedPage) && parsedPage > 0 ? Math.floor(parsedPage) : 1;
	const offset = (page - 1) * limit;
	const start_date = url.searchParams.get('start_date') ?? undefined;
	const end_date = url.searchParams.get('end_date') ?? undefined;

	const { items, total } = await getGames({ scope, limit, offset, start_date, end_date }, fetch);

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
