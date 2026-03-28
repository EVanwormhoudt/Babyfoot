import type {PageLoad} from './$types';
import {
    getPlayers,
    getPlayerRatingHistory,
    getPlayerStats,
    type PlayerRatingHistoryPoint,
    type PlayerStats,
    type Scope
} from '$lib/api/players';

type PlayerLite = {
    id: number;
    player_name: string;
    player_color: string;
    active?: boolean;
};

function isScope(value: string | null): value is Scope {
    return value === 'overall' || value === 'monthly' || value === 'yearly';
}

export const load: PageLoad = async ({fetch, url}) => {
    const players = await getPlayers(fetch);
    const activePlayers = players.filter((p) => p.active !== false);
    const selectablePlayers: PlayerLite[] = activePlayers.length > 0 ? activePlayers : players;

    const rawScope = url.searchParams.get('scope');
    const scope: Scope = isScope(rawScope) ? rawScope : 'overall';

    const rawPlayerId = Number(url.searchParams.get('player_id'));
    const playerExists = selectablePlayers.some((p) => p.id === rawPlayerId);
    const selectedPlayerId = playerExists ? rawPlayerId : (selectablePlayers[0]?.id ?? null);
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;

    const rawYear = Number(url.searchParams.get('year'));
    const selectedYear = Number.isFinite(rawYear) && rawYear > 1900 ? Math.trunc(rawYear) : currentYear;

    const rawMonth = Number(url.searchParams.get('month'));
    const selectedMonth =
        Number.isFinite(rawMonth) && rawMonth >= 1 && rawMonth <= 12 ? Math.trunc(rawMonth) : currentMonth;

    const yearOptions = Array.from({length: 12}, (_, index) => currentYear - index);

    let stats: PlayerStats | null = null;
    let statsError: string | null = null;
    let ratingHistory: PlayerRatingHistoryPoint[] = [];
    let ratingHistoryError: string | null = null;

    if (selectedPlayerId !== null) {
        const periodOpts =
            scope === 'monthly' ? {year: selectedYear, month: selectedMonth}
                : scope === 'yearly' ? {year: selectedYear}
                    : {};

        const [statsResult, historyResult] = await Promise.allSettled([
            getPlayerStats(selectedPlayerId, scope, periodOpts, fetch),
            getPlayerRatingHistory(selectedPlayerId, scope, periodOpts, fetch)
        ]);

        if (statsResult.status === 'fulfilled') {
            stats = statsResult.value;
        } else {
            statsError = statsResult.reason instanceof Error ? statsResult.reason.message : 'Impossible de charger les statistiques';
        }

        if (historyResult.status === 'fulfilled') {
            ratingHistory = historyResult.value;
        } else {
            ratingHistoryError = historyResult.reason instanceof Error
                ? historyResult.reason.message
                : "Impossible de charger l'historique Elo";
        }
    }

    return {
        players: selectablePlayers,
        selectedPlayerId,
        scope,
        selectedYear,
        selectedMonth,
        yearOptions,
        stats,
        statsError,
        ratingHistory,
        ratingHistoryError
    };
};
