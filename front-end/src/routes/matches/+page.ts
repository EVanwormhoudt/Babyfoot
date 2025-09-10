// +page.ts
import type {PageLoad} from './$types';
import {getGames} from '$lib/api/matches';

export type GameRead = any;

function startOfDayUTC(d: Date) {
    return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 0, 0, 0));
}

function addDaysUTC(d: Date, days: number) {
    const copy = new Date(d.getTime());
    copy.setUTCDate(copy.getUTCDate() + days);
    return copy;
}

function startOfMonthUTC(year: number, monthIndex0: number) {
    return new Date(Date.UTC(year, monthIndex0, 1, 0, 0, 0));
}

export const load: PageLoad = async ({url}) => {
    const page = Math.max(1, Number(url.searchParams.get('page') ?? '1'));
    const perPage = Math.min(24, Math.max(1, Number(url.searchParams.get('pp') ?? '9')));

    const dateParam = url.searchParams.get('date');
    const monthParam = url.searchParams.get('month');

    let start_date: string | undefined;
    let end_date: string | undefined;

    if (dateParam) {
        const start = startOfDayUTC(new Date(dateParam + 'T00:00:00Z'));
        const end = addDaysUTC(start, 1);
        start_date = start.toISOString();
        end_date = end.toISOString();
    } else if (monthParam) {
        const [y, m] = monthParam.split('-').map(Number);
        const start = startOfMonthUTC(y, (m ?? 1) - 1);
        const end = startOfMonthUTC(y, (m ?? 1));
        start_date = start.toISOString();
        end_date = end.toISOString();
    }

    const limit = perPage;
    const offset = (page - 1) * perPage;
    const scope: 'all' | 'monthly' = monthParam ? 'monthly' : 'all';

    const items = await getGames({scope, limit, offset, start_date, end_date});

    const hasNext = items.length === perPage;
    return {matches: items, page, perPage, dateParam, monthParam, hasNext};
};
