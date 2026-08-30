import type { PageLoad } from './$types';
import {
	getPlayers,
	getPlayerRatingHistory,
	getPlayerStats,
	type PlayerRatingHistoryPoint,
	type PlayerStats,
	type Scope
} from '$lib/api/players';
import { getGames } from '$lib/api/matches';
import type { GameRead } from '$lib/api/types';

const RECENT_MATCH_LIMIT = 3;

type PlayerLite = {
	id: number;
	player_name: string;
	player_color: string;
	active?: boolean;
};

function isScope(value: string | null): value is Scope {
	return value === 'overall' || value === 'monthly' || value === 'yearly';
}

export const load: PageLoad = async ({ fetch, url }) => {
	const players = await getPlayers(fetch);
	const activePlayers = players.filter((p) => p.active !== false);
	const selectablePlayers: PlayerLite[] = activePlayers.length > 0 ? activePlayers : players;

	const rawScope = url.searchParams.get('scope');
	const scope: Scope = isScope(rawScope) ? rawScope : 'overall';

	const rawPlayerId = Number(url.searchParams.get('player_id'));
	const playerExists = selectablePlayers.some((p) => p.id === rawPlayerId);
	const selectedPlayerId = playerExists ? rawPlayerId : (selectablePlayers[0]?.id ?? null);

	const rawComparePlayerId = Number(url.searchParams.get('compare_player_id'));
	const comparePlayerExists = selectablePlayers.some(
		(p) => p.id === rawComparePlayerId && p.id !== selectedPlayerId
	);
	const selectedComparePlayerId = comparePlayerExists ? rawComparePlayerId : null;

	const now = new Date();
	const currentYear = now.getFullYear();
	const currentMonth = now.getMonth() + 1;

	const rawYear = Number(url.searchParams.get('year'));
	const selectedYear =
		Number.isFinite(rawYear) && rawYear > 1900 ? Math.trunc(rawYear) : currentYear;

	const rawMonth = Number(url.searchParams.get('month'));
	const selectedMonth =
		Number.isFinite(rawMonth) && rawMonth >= 1 && rawMonth <= 12
			? Math.trunc(rawMonth)
			: currentMonth;

	const yearOptions = Array.from({ length: 12 }, (_, index) => currentYear - index);

	let stats: PlayerStats | null = null;
	let statsError: string | null = null;
	let ratingHistory: PlayerRatingHistoryPoint[] = [];
	let ratingHistoryError: string | null = null;
	let comparisonStats: PlayerStats | null = null;
	let comparisonStatsError: string | null = null;
	let comparisonRatingHistory: PlayerRatingHistoryPoint[] = [];
	let comparisonRatingHistoryError: string | null = null;
	let recentMatches: GameRead[] = [];
	let recentMatchesTotal = 0;
	let recentMatchesError: string | null = null;

	if (selectedPlayerId !== null) {
		const periodOpts =
			scope === 'monthly'
				? { year: selectedYear, month: selectedMonth }
				: scope === 'yearly'
					? { year: selectedYear }
					: {};

		const loadPlayerBundle = async (playerId: number) => {
			const [statsResult, historyResult] = await Promise.allSettled([
				getPlayerStats(playerId, scope, periodOpts, fetch),
				getPlayerRatingHistory(playerId, scope, periodOpts, fetch)
			]);

			return { statsResult, historyResult };
		};

		const loadRecentMatches = async (playerId: number) => {
			const [matchesResult] = await Promise.allSettled([
				getGames(
					{
						scope: 'all',
						limit: RECENT_MATCH_LIMIT,
						offset: 0,
						player_id: playerId
					},
					fetch
				)
			]);

			return matchesResult;
		};

		const [primaryBundle, comparisonBundle, recentMatchesResult] = await Promise.all([
			loadPlayerBundle(selectedPlayerId),
			selectedComparePlayerId !== null
				? loadPlayerBundle(selectedComparePlayerId)
				: Promise.resolve(null),
			loadRecentMatches(selectedPlayerId)
		]);

		const { statsResult, historyResult } = primaryBundle;

		if (statsResult.status === 'fulfilled') {
			stats = statsResult.value;
		} else {
			statsError =
				statsResult.reason instanceof Error
					? statsResult.reason.message
					: 'Impossible de charger les statistiques';
		}

		if (historyResult.status === 'fulfilled') {
			ratingHistory = historyResult.value;
		} else {
			ratingHistoryError =
				historyResult.reason instanceof Error
					? historyResult.reason.message
					: "Impossible de charger l'historique Elo";
		}

		if (comparisonBundle) {
			if (comparisonBundle.statsResult.status === 'fulfilled') {
				comparisonStats = comparisonBundle.statsResult.value;
			} else {
				comparisonStatsError =
					comparisonBundle.statsResult.reason instanceof Error
						? comparisonBundle.statsResult.reason.message
						: 'Impossible de charger les statistiques de comparaison';
			}

			if (comparisonBundle.historyResult.status === 'fulfilled') {
				comparisonRatingHistory = comparisonBundle.historyResult.value;
			} else {
				comparisonRatingHistoryError =
					comparisonBundle.historyResult.reason instanceof Error
						? comparisonBundle.historyResult.reason.message
						: "Impossible de charger l'historique Elo de comparaison";
			}
		}

		if (recentMatchesResult.status === 'fulfilled') {
			recentMatches = recentMatchesResult.value.items;
			recentMatchesTotal = recentMatchesResult.value.total;
		} else {
			recentMatchesError =
				recentMatchesResult.reason instanceof Error
					? recentMatchesResult.reason.message
					: 'Impossible de charger les derniers matchs';
		}
	}

	return {
		players: selectablePlayers,
		selectedPlayerId,
		selectedComparePlayerId,
		scope,
		selectedYear,
		selectedMonth,
		yearOptions,
		stats,
		statsError,
		ratingHistory,
		ratingHistoryError,
		comparisonStats,
		comparisonStatsError,
		comparisonRatingHistory,
		comparisonRatingHistoryError,
		recentMatches,
		recentMatchesTotal,
		recentMatchesError,
		recentMatchLimit: RECENT_MATCH_LIMIT
	};
};
