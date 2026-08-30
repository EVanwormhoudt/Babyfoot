<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import type { PlayerRatingHistoryPoint, PlayerStats, Scope } from '$lib/api/players';
	import type { PageData } from './$types';
	import { getStoredCurrentPlayerId } from '$lib/current-player';

	type ChartPoint = {
		x: number;
		y: number;
		mu: number;
		dateLabel: string;
		sigma: number | null;
		rank: number;
		rankType: Scope;
	};

	type ChartSeriesKey = 'primary' | 'comparison';

	type ChartSeriesInput = {
		key: ChartSeriesKey;
		name: string;
		history: PlayerRatingHistoryPoint[];
		color: string;
		strongColor: string;
		fillTop: string;
		fillBottom: string;
		gradientId: string;
	};

	type ChartSeries = {
		key: ChartSeriesKey;
		name: string;
		color: string;
		strongColor: string;
		fillTop: string;
		fillBottom: string;
		gradientId: string;
		path: string;
		areaPath: string;
		points: ChartPoint[];
		minMu: number;
		maxMu: number;
		latestMu: number;
		trendDelta: number;
	};

	type AxisXTick = {
		x: number;
		label: string;
	};

	type AxisYTick = {
		y: number;
		value: number;
	};

	type ChartModel = {
		width: number;
		height: number;
		series: ChartSeries[];
		path: string;
		areaPath: string;
		points: ChartPoint[];
		xTicks: AxisXTick[];
		yTicks: AxisYTick[];
		minMu: number;
		maxMu: number;
		latestMu: number;
		startDate: string;
		endDate: string;
		leftX: number;
		rightX: number;
		topY: number;
		midY: number;
		bottomY: number;
	};

	type HoveredPointRef = {
		seriesIndex: number;
		pointIndex: number;
	};

	type ComparisonRow = {
		label: string;
		primary: string;
		comparison: string;
		delta: string;
	};

	type RecentMatch = PageData['recentMatches'][number];
	type RecentMatchTeam = RecentMatch['teams'][number];
	type RecentMatchOutcome = 'win' | 'loss' | 'draw' | 'unknown';

	let { data } = $props<{ data: PageData }>();

	let selectedPlayerId = $state(data.selectedPlayerId ? String(data.selectedPlayerId) : '');
	let selectedComparePlayerId = $state(
		data.selectedComparePlayerId ? String(data.selectedComparePlayerId) : ''
	);
	let selectedScope = $state<Scope>(data.scope);
	let selectedYear = $state(String(data.selectedYear));
	let selectedMonth = $state(String(data.selectedMonth));
	let hoveredPointRef = $state<HoveredPointRef | null>(null);

	const monthOptions = [
		{ value: 1, label: 'Janvier' },
		{ value: 2, label: 'Fevrier' },
		{ value: 3, label: 'Mars' },
		{ value: 4, label: 'Avril' },
		{ value: 5, label: 'Mai' },
		{ value: 6, label: 'Juin' },
		{ value: 7, label: 'Juillet' },
		{ value: 8, label: 'Aout' },
		{ value: 9, label: 'Septembre' },
		{ value: 10, label: 'Octobre' },
		{ value: 11, label: 'Novembre' },
		{ value: 12, label: 'Decembre' }
	];

	const selectedPlayer = $derived(
		data.players.find((p: { id: number }) => String(p.id) === selectedPlayerId)
	);
	const selectedPlayerIdNumber = $derived(Number(selectedPlayerId));

	const selectedPlayerName = $derived(selectedPlayer?.player_name ?? 'Joueur');
	const selectedComparePlayer = $derived(
		data.players.find((p: { id: number }) => String(p.id) === selectedComparePlayerId)
	);
	const selectedComparePlayerName = $derived(selectedComparePlayer?.player_name ?? 'Comparaison');
	const hasComparison = $derived(Boolean(selectedComparePlayerId && data.comparisonStats));
	const selectedScopeLabel = $derived.by(() => {
		if (selectedScope === 'monthly') {
			const month = monthOptions.find((item) => String(item.value) === selectedMonth);
			return `${month?.label ?? 'Mois'} ${selectedYear}`;
		}
		if (selectedScope === 'yearly') {
			return selectedYear;
		}
		return 'General';
	});

	function applyFilters() {
		const playerIdNum = Number(selectedPlayerId);
		const comparePlayerIdNum = Number(selectedComparePlayerId);
		if (
			selectedComparePlayerId &&
			(!Number.isFinite(comparePlayerIdNum) ||
				comparePlayerIdNum <= 0 ||
				comparePlayerIdNum === playerIdNum)
		) {
			selectedComparePlayerId = '';
		}

		// eslint-disable-next-line svelte/prefer-svelte-reactivity
		const params = new URLSearchParams();
		if (selectedPlayerId) params.set('player_id', selectedPlayerId);
		if (selectedComparePlayerId) params.set('compare_player_id', selectedComparePlayerId);
		params.set('scope', selectedScope);
		if (selectedScope !== 'overall') {
			params.set('year', selectedYear);
		}
		if (selectedScope === 'monthly') {
			params.set('month', selectedMonth);
		}

		let target: string = resolve('/stats');
		target = `${target}?${params.toString()}`;
		goto(target, { replaceState: true, noScroll: true });
	}

	onMount(() => {
		const params = new URLSearchParams(window.location.search);
		if (params.has('player_id')) return;

		const storedId = getStoredCurrentPlayerId();
		if (!storedId) return;
		if (!data.players.some((player: { id: number }) => player.id === storedId)) return;

		selectedPlayerId = String(storedId);
		applyFilters();
	});

	function percent(value: number) {
		return `${(value * 100).toFixed(1)}%`;
	}

	function percentPointDelta(primary: number, comparison: number) {
		const diff = (primary - comparison) * 100;
		const sign = diff > 0 ? '+' : '';
		return `${sign}${diff.toFixed(1)} pts`;
	}

	function fixed(value: number, digits = 0) {
		return value.toFixed(digits);
	}

	function numericDelta(primary: number, comparison: number, digits = 0) {
		const diff = primary - comparison;
		const sign = diff > 0 ? '+' : '';
		return `${sign}${diff.toFixed(digits)}`;
	}

	function playerName(team: RecentMatchTeam): string {
		return team.player?.player_name ?? `Joueur #${team.player_id}`;
	}

	function getMatchTeam(game: RecentMatch, teamNumber: 1 | 2 | null): RecentMatchTeam[] {
		if (teamNumber === null) return [];
		return game.teams.filter((team) => team.team_number === teamNumber);
	}

	function teamLabel(game: RecentMatch, teamNumber: 1 | 2 | null): string {
		const names = getMatchTeam(game, teamNumber).map(playerName);
		return names.length > 0 ? names.join(' + ') : '-';
	}

	function selectedPlayerTeam(game: RecentMatch, playerId: number): 1 | 2 | null {
		if (!Number.isFinite(playerId)) return null;
		const team = game.teams.find((item) => item.player_id === playerId);
		return team?.team_number ?? null;
	}

	function opponentTeam(teamNumber: 1 | 2 | null): 1 | 2 | null {
		if (teamNumber === 1) return 2;
		if (teamNumber === 2) return 1;
		return null;
	}

	function teamScore(game: RecentMatch, teamNumber: 1 | 2 | null): number | null {
		if (teamNumber === 1) return game.result_team1;
		if (teamNumber === 2) return game.result_team2;
		return null;
	}

	function matchOutcome(game: RecentMatch, playerId: number): RecentMatchOutcome {
		const teamNumber = selectedPlayerTeam(game, playerId);
		const otherTeamNumber = opponentTeam(teamNumber);
		const score = teamScore(game, teamNumber);
		const otherScore = teamScore(game, otherTeamNumber);
		if (score === null || otherScore === null) return 'unknown';
		if (score === otherScore) return 'draw';
		return score > otherScore ? 'win' : 'loss';
	}

	function matchOutcomeLabel(outcome: RecentMatchOutcome): string {
		if (outcome === 'win') return 'Victoire';
		if (outcome === 'loss') return 'Defaite';
		if (outcome === 'draw') return 'Nul';
		return 'Resultat';
	}

	function matchOutcomeClass(outcome: RecentMatchOutcome): string {
		if (outcome === 'win') return 'tone-positive bg-emerald-500/10';
		if (outcome === 'loss') return 'tone-negative bg-red-500/10';
		if (outcome === 'draw') return 'bg-muted text-muted-foreground';
		return 'bg-muted text-muted-foreground';
	}

	function selectedPlayerDelta(game: RecentMatch, playerId: number, scope: Scope): number | null {
		const change = game.rating_changes?.find(
			(item) => item.player_id === playerId && item.rating_type === scope
		);
		return typeof change?.delta_mu === 'number' ? change.delta_mu : null;
	}

	function formatMatchDate(value: string): string {
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return value;
		return parsed.toLocaleString(undefined, {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function teammateLabel(teammate: PlayerStats['best_teammate']) {
		return teammate ? `${teammate.player_name} (${percent(teammate.win_rate)})` : '-';
	}

	const comparisonRows = $derived.by<ComparisonRow[]>(() => {
		if (!data.stats || !data.comparisonStats) return [];

		return [
			{
				label: 'Matchs joues',
				primary: fixed(data.stats.games_played),
				comparison: fixed(data.comparisonStats.games_played),
				delta: numericDelta(data.stats.games_played, data.comparisonStats.games_played)
			},
			{
				label: 'Victoires',
				primary: fixed(data.stats.wins),
				comparison: fixed(data.comparisonStats.wins),
				delta: numericDelta(data.stats.wins, data.comparisonStats.wins)
			},
			{
				label: 'Taux de victoire',
				primary: percent(data.stats.win_rate),
				comparison: percent(data.comparisonStats.win_rate),
				delta: percentPointDelta(data.stats.win_rate, data.comparisonStats.win_rate)
			},
			{
				label: 'Score moyen equipe',
				primary: fixed(data.stats.average_team_score, 2),
				comparison: fixed(data.comparisonStats.average_team_score, 2),
				delta: numericDelta(
					data.stats.average_team_score,
					data.comparisonStats.average_team_score,
					2
				)
			},
			{
				label: 'Score moyen adversaires',
				primary: fixed(data.stats.average_opponent_score, 2),
				comparison: fixed(data.comparisonStats.average_opponent_score, 2),
				delta: numericDelta(
					data.stats.average_opponent_score,
					data.comparisonStats.average_opponent_score,
					2
				)
			},
			{
				label: 'Serie actuelle',
				primary: fixed(data.stats.current_win_streak),
				comparison: fixed(data.comparisonStats.current_win_streak),
				delta: numericDelta(data.stats.current_win_streak, data.comparisonStats.current_win_streak)
			},
			{
				label: 'Plus longue serie',
				primary: fixed(data.stats.longest_win_streak),
				comparison: fixed(data.comparisonStats.longest_win_streak),
				delta: numericDelta(data.stats.longest_win_streak, data.comparisonStats.longest_win_streak)
			},
			{
				label: 'Meilleur coequipier',
				primary: teammateLabel(data.stats.best_teammate),
				comparison: teammateLabel(data.comparisonStats.best_teammate),
				delta: '-'
			},
			{
				label: 'Pire coequipier',
				primary: teammateLabel(data.stats.worst_teammate),
				comparison: teammateLabel(data.comparisonStats.worst_teammate),
				delta: '-'
			}
		];
	});

	function muAmount(value: number) {
		return `Elo ${value.toFixed(1)}`;
	}

	function signed(value: number) {
		const sign = value > 0 ? '+' : '';
		return `${sign}${value.toFixed(1)}`;
	}

	function scopeToLabel(scope: Scope): string {
		if (scope === 'monthly') return 'Mensuel';
		if (scope === 'yearly') return 'Annuel';
		return 'General';
	}

	function formatDate(value: string): string {
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return value;
		return parsed.toLocaleDateString(undefined, {
			day: '2-digit',
			month: 'short',
			year: 'numeric'
		});
	}

	function formatTimestamp(value: number): string {
		const parsed = new Date(value);
		if (Number.isNaN(parsed.getTime())) return '';
		return parsed.toLocaleDateString(undefined, {
			day: '2-digit',
			month: 'short',
			year: 'numeric'
		});
	}

	function visibleHistory(history: PlayerRatingHistoryPoint[]) {
		const sorted = [...history]
			.filter((point): point is PlayerRatingHistoryPoint & { mu: number } => point.mu !== null)
			.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

		const baselineMu = 1000;
		const firstNonBaselineIndex = sorted.findIndex(
			(point) => Math.abs(point.mu - baselineMu) > 0.0001
		);
		return firstNonBaselineIndex > 0 ? sorted.slice(firstNonBaselineIndex) : sorted;
	}

	function buildHistoryChart(inputs: ChartSeriesInput[]): ChartModel {
		const width = 760;
		const height = 290;
		const left = 56;
		const right = 18;
		const top = 20;
		const bottom = 46;

		const visibleInputs = inputs
			.map((input) => ({ ...input, visible: visibleHistory(input.history) }))
			.filter((input) => input.visible.length > 0);

		if (visibleInputs.length === 0) {
			return {
				width,
				height,
				series: [],
				path: '',
				areaPath: '',
				points: [],
				xTicks: [],
				yTicks: [],
				minMu: 0,
				maxMu: 0,
				latestMu: 0,
				startDate: '',
				endDate: '',
				leftX: left,
				rightX: width - right,
				topY: top,
				midY: (top + (height - bottom)) / 2,
				bottomY: height - bottom
			};
		}

		const allVisiblePoints = visibleInputs.flatMap((input) => input.visible);
		const muValues = allVisiblePoints.map((point) => point.mu);
		const dateValues = allVisiblePoints.map((point) => new Date(point.date).getTime());
		const minMu = Math.min(...muValues);
		const maxMu = Math.max(...muValues);
		const axisStep = 100;
		let axisMin = Math.floor(minMu / axisStep) * axisStep;
		let axisMax = Math.ceil(maxMu / axisStep) * axisStep;
		if (axisMin === axisMax) {
			axisMin -= axisStep;
			axisMax += axisStep;
		}
		const axisSpan = axisMax - axisMin;
		const minDate = Math.min(...dateValues);
		const maxDate = Math.max(...dateValues);
		const dateSpan = maxDate - minDate || 1;

		const plotWidth = width - left - right;
		const plotHeight = height - top - bottom;

		const series: ChartSeries[] = visibleInputs.map((input) => {
			const points: ChartPoint[] = input.visible.map((point) => {
				const dateValue = new Date(point.date).getTime();
				const x = left + ((dateValue - minDate) / dateSpan) * plotWidth;
				const y = top + (1 - (point.mu - axisMin) / axisSpan) * plotHeight;
				return {
					x,
					y,
					mu: point.mu,
					dateLabel: formatDate(point.date),
					sigma: point.sigma,
					rank: point.rank,
					rankType: point.rank_type
				};
			});

			const path = points
				.map(
					(point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`
				)
				.join(' ');

			const areaPath = `${path} L ${points[points.length - 1].x.toFixed(2)} ${(
				top + plotHeight
			).toFixed(2)} L ${points[0].x.toFixed(2)} ${(top + plotHeight).toFixed(2)} Z`;

			const seriesMuValues = points.map((point) => point.mu);

			return {
				key: input.key,
				name: input.name,
				color: input.color,
				strongColor: input.strongColor,
				fillTop: input.fillTop,
				fillBottom: input.fillBottom,
				gradientId: input.gradientId,
				path,
				areaPath,
				points,
				minMu: Math.min(...seriesMuValues),
				maxMu: Math.max(...seriesMuValues),
				latestMu: points[points.length - 1].mu,
				trendDelta: points.length > 1 ? points[points.length - 1].mu - points[0].mu : 0
			};
		});

		const primarySeries = series.find((item) => item.key === 'primary') ?? series[0];
		const points = primarySeries.points;

		const yTicks: AxisYTick[] = [];
		for (let value = axisMax; value >= axisMin; value -= axisStep) {
			const ratio = (axisMax - value) / axisSpan;
			yTicks.push({
				y: top + ratio * plotHeight,
				value
			});
		}

		const xTicks: AxisXTick[] =
			minDate === maxDate
				? [{ x: left + plotWidth / 2, label: formatTimestamp(minDate) }]
				: [
						{ x: left, label: formatTimestamp(minDate) },
						{ x: left + plotWidth / 2, label: formatTimestamp(minDate + dateSpan / 2) },
						{ x: left + plotWidth, label: formatTimestamp(maxDate) }
					];

		return {
			width,
			height,
			series,
			path: primarySeries.path,
			areaPath: primarySeries.areaPath,
			points,
			xTicks,
			yTicks,
			minMu,
			maxMu,
			latestMu: primarySeries.latestMu,
			startDate: formatTimestamp(minDate),
			endDate: formatTimestamp(maxDate),
			leftX: left,
			rightX: width - right,
			topY: top,
			midY: top + plotHeight / 2,
			bottomY: height - bottom
		};
	}

	const chart = $derived.by(() =>
		buildHistoryChart([
			{
				key: 'primary',
				name: selectedPlayerName,
				history: data.ratingHistory ?? [],
				color: '#16a34a',
				strongColor: '#15803d',
				fillTop: 'rgba(34, 197, 94, 0.28)',
				fillBottom: 'rgba(34, 197, 94, 0.02)',
				gradientId: 'rating-history-primary-fill'
			},
			...(selectedComparePlayerId
				? [
						{
							key: 'comparison' as const,
							name: selectedComparePlayerName,
							history: data.comparisonRatingHistory ?? [],
							color: '#2563eb',
							strongColor: '#1d4ed8',
							fillTop: 'rgba(37, 99, 235, 0.18)',
							fillBottom: 'rgba(37, 99, 235, 0.02)',
							gradientId: 'rating-history-comparison-fill'
						}
					]
				: [])
		])
	);
	const primaryChartSeries = $derived(
		chart.series.find((series) => series.key === 'primary') ?? null
	);
	const trendDelta = $derived(primaryChartSeries?.trendDelta ?? 0);
	const recentHistory = $derived(chart.points.slice(-5));
	const pointCount = $derived(
		chart.series.reduce((total, series) => total + series.points.length, 0)
	);
	function handleChartPointerMove(event: PointerEvent) {
		const svg = event.currentTarget as SVGSVGElement | null;
		if (!svg || pointCount === 0) {
			hoveredPointRef = null;
			return;
		}

		const screenPoint = svg.createSVGPoint();
		screenPoint.x = event.clientX;
		screenPoint.y = event.clientY;

		const ctm = svg.getScreenCTM();
		if (!ctm) {
			hoveredPointRef = null;
			return;
		}

		const localPoint = screenPoint.matrixTransform(ctm.inverse());
		if (
			localPoint.x < chart.leftX ||
			localPoint.x > chart.rightX ||
			localPoint.y < chart.topY ||
			localPoint.y > chart.bottomY
		) {
			hoveredPointRef = null;
			return;
		}

		let bestRef: HoveredPointRef | null = null;
		let bestDistance = Number.POSITIVE_INFINITY;
		for (let seriesIndex = 0; seriesIndex < chart.series.length; seriesIndex += 1) {
			const series = chart.series[seriesIndex];
			for (let pointIndex = 0; pointIndex < series.points.length; pointIndex += 1) {
				const point = series.points[pointIndex];
				const distance = Math.hypot(point.x - localPoint.x, (point.y - localPoint.y) * 0.35);
				if (distance < bestDistance) {
					bestDistance = distance;
					bestRef = { seriesIndex, pointIndex };
				}
			}
		}
		hoveredPointRef = bestRef;
	}
	const hoveredSeries = $derived(
		hoveredPointRef !== null &&
			hoveredPointRef.seriesIndex >= 0 &&
			hoveredPointRef.seriesIndex < chart.series.length
			? chart.series[hoveredPointRef.seriesIndex]
			: null
	);
	const hoveredPoint = $derived(
		hoveredPointRef !== null &&
			hoveredSeries &&
			hoveredPointRef.pointIndex >= 0 &&
			hoveredPointRef.pointIndex < hoveredSeries.points.length
			? hoveredSeries.points[hoveredPointRef.pointIndex]
			: null
	);
	const hoveredDelta = $derived(
		hoveredPointRef !== null &&
			hoveredSeries &&
			hoveredPointRef.pointIndex > 0 &&
			hoveredPointRef.pointIndex < hoveredSeries.points.length
			? hoveredSeries.points[hoveredPointRef.pointIndex].mu -
					hoveredSeries.points[hoveredPointRef.pointIndex - 1].mu
			: null
	);
	const tooltipBox = $derived(
		hoveredPoint
			? (() => {
					const width = 210;
					const height = 116;
					let x = hoveredPoint.x + 12;
					if (x + width > chart.rightX) {
						x = hoveredPoint.x - width - 12;
					}
					let y = hoveredPoint.y - height - 12;
					if (y < chart.topY + 4) {
						y = hoveredPoint.y + 12;
					}
					return { x, y, width, height };
				})()
			: null
	);
</script>

<section class="space-y-6 p-8">
	<h2 class="text-3xl font-semibold">Statistiques</h2>

	{#if data.players.length === 0}
		<Card>
			<CardContent class="py-8 text-center text-muted-foreground">Aucun joueur trouve.</CardContent>
		</Card>
	{:else}
		<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
			<label class="flex flex-col gap-2">
				<span class="text-sm text-muted-foreground">Joueur</span>
				<select
					bind:value={selectedPlayerId}
					class="h-10 rounded-md border bg-background px-3 text-sm"
					onchange={applyFilters}
				>
					{#each data.players as player (player.id)}
						<option value={String(player.id)}>{player.player_name}</option>
					{/each}
				</select>
			</label>

			<label class="flex flex-col gap-2">
				<span class="text-sm text-muted-foreground">Comparer avec</span>
				<select
					bind:value={selectedComparePlayerId}
					class="h-10 rounded-md border bg-background px-3 text-sm"
					onchange={applyFilters}
				>
					<option value="">Aucun</option>
					{#each data.players as player (player.id)}
						<option value={String(player.id)} disabled={String(player.id) === selectedPlayerId}>
							{player.player_name}
						</option>
					{/each}
				</select>
			</label>

			<label class="flex flex-col gap-2">
				<span class="text-sm text-muted-foreground">Periode</span>
				<select
					bind:value={selectedScope}
					class="h-10 rounded-md border bg-background px-3 text-sm"
					onchange={applyFilters}
				>
					<option value="overall">General</option>
					<option value="monthly">Mensuel</option>
					<option value="yearly">Annuel</option>
				</select>
			</label>

			{#if selectedScope === 'monthly' || selectedScope === 'yearly'}
				<label class="flex flex-col gap-2">
					<span class="text-sm text-muted-foreground">Annee</span>
					<select
						bind:value={selectedYear}
						class="h-10 rounded-md border bg-background px-3 text-sm"
						onchange={applyFilters}
					>
						{#each data.yearOptions as year (year)}
							<option value={String(year)}>{year}</option>
						{/each}
					</select>
				</label>
			{/if}

			{#if selectedScope === 'monthly'}
				<label class="flex flex-col gap-2">
					<span class="text-sm text-muted-foreground">Mois</span>
					<select
						bind:value={selectedMonth}
						class="h-10 rounded-md border bg-background px-3 text-sm"
						onchange={applyFilters}
					>
						{#each monthOptions as month (month.value)}
							<option value={String(month.value)}>{month.label}</option>
						{/each}
					</select>
				</label>
			{/if}
		</div>

		{#if data.statsError}
			<Card>
				<CardContent class="py-6 text-sm text-destructive">
					{data.statsError}
				</CardContent>
			</Card>
		{:else if data.stats}
			<Card>
				<CardHeader>
					<CardTitle>
						{hasComparison
							? `${selectedPlayerName} vs ${selectedComparePlayerName} (${selectedScopeLabel})`
							: `${selectedPlayerName} (${selectedScopeLabel})`}
					</CardTitle>
				</CardHeader>
				<CardContent class="text-sm">
					{#if hasComparison}
						<div class="overflow-x-auto rounded-md border">
							<div class="min-w-[680px] divide-y">
								<div
									class="grid grid-cols-[1.1fr_0.9fr_0.9fr_0.55fr] gap-3 bg-muted/40 px-3 py-2 text-xs font-semibold uppercase text-muted-foreground"
								>
									<div>Stat</div>
									<div>{selectedPlayerName}</div>
									<div>{selectedComparePlayerName}</div>
									<div>Ecart</div>
								</div>
								{#each comparisonRows as row (row.label)}
									<div class="grid grid-cols-[1.1fr_0.9fr_0.9fr_0.55fr] gap-3 px-3 py-3">
										<div class="font-medium text-muted-foreground">{row.label}</div>
										<div class="break-words font-semibold">{row.primary}</div>
										<div class="break-words font-semibold">{row.comparison}</div>
										<div class="font-medium text-muted-foreground">{row.delta}</div>
									</div>
								{/each}
							</div>
						</div>
					{:else}
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Matchs joues</div>
								<div class="text-2xl font-semibold">{data.stats.games_played}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Victoires</div>
								<div class="text-2xl font-semibold">{data.stats.wins}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Taux de victoire</div>
								<div class="text-2xl font-semibold">{percent(data.stats.win_rate)}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Score moyen equipe</div>
								<div class="text-2xl font-semibold">{data.stats.average_team_score.toFixed(2)}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Score moyen adversaires</div>
								<div class="text-2xl font-semibold">
									{data.stats.average_opponent_score.toFixed(2)}
								</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Serie actuelle</div>
								<div class="text-2xl font-semibold">{data.stats.current_win_streak}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Plus longue serie</div>
								<div class="text-2xl font-semibold">{data.stats.longest_win_streak}</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Meilleur coequipier</div>
								<div class="text-base font-medium">
									{teammateLabel(data.stats.best_teammate)}
								</div>
							</div>
							<div class="rounded-md border p-3">
								<div class="text-muted-foreground">Pire coequipier</div>
								<div class="text-base font-medium">
									{teammateLabel(data.stats.worst_teammate)}
								</div>
							</div>
						</div>
					{/if}
				</CardContent>
			</Card>
		{/if}

		{#if data.recentMatchesError}
			<Card>
				<CardContent class="py-6 text-sm text-destructive">
					{data.recentMatchesError}
				</CardContent>
			</Card>
		{:else}
			<Card>
				<CardHeader class="flex flex-row items-start justify-between gap-4">
					<div class="space-y-1">
						<CardTitle>Derniers {data.recentMatchLimit} matchs de {selectedPlayerName}</CardTitle>
						<p class="text-xs text-muted-foreground">
							{data.recentMatchesTotal} match{data.recentMatchesTotal > 1 ? 's' : ''} au total
						</p>
					</div>
					{#if data.recentMatchesTotal > data.recentMatchLimit}
						<a
							href={`${resolve('/matches')}?player_id=${encodeURIComponent(selectedPlayerId)}`}
							class="rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
						>
							Voir tout
						</a>
					{/if}
				</CardHeader>
				<CardContent>
					{#if data.recentMatches.length === 0}
						<div class="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
							Aucun match recent pour ce joueur.
						</div>
					{:else}
						<div class="divide-y rounded-md border">
							{#each data.recentMatches as match (match.id)}
								{@const playerTeam = selectedPlayerTeam(match, selectedPlayerIdNumber)}
								{@const otherTeam = opponentTeam(playerTeam)}
								{@const outcome = matchOutcome(match, selectedPlayerIdNumber)}
								{@const playerScore = teamScore(match, playerTeam)}
								{@const otherScore = teamScore(match, otherTeam)}
								{@const delta = selectedPlayerDelta(match, selectedPlayerIdNumber, selectedScope)}
								<a
									href={resolve(`/matches/${match.id}`)}
									class="grid gap-3 px-4 py-3 text-sm transition-colors hover:bg-muted/50 md:grid-cols-[minmax(0,1fr)_auto]"
								>
									<div class="min-w-0 space-y-2">
										<div class="flex flex-wrap items-center gap-2">
											<span
												class="rounded-full px-2 py-0.5 text-xs font-semibold {matchOutcomeClass(
													outcome
												)}"
											>
												{matchOutcomeLabel(outcome)}
											</span>
											<span class="text-xs text-muted-foreground">{formatMatchDate(match.game_timestamp)}</span>
											<span class="text-xs text-muted-foreground">#{match.id}</span>
										</div>
										<div class="grid gap-1.5">
											<div class="min-w-0 font-medium">
												<span class="text-muted-foreground">Equipe</span>
												<span class="break-words">{teamLabel(match, playerTeam)}</span>
											</div>
											<div class="min-w-0">
												<span class="text-muted-foreground">Adversaires</span>
												<span class="break-words">{teamLabel(match, otherTeam)}</span>
											</div>
										</div>
									</div>
									<div class="flex items-center justify-between gap-4 md:justify-end">
										<div class="text-right">
											<div class="text-2xl font-semibold tabular-nums">
												{playerScore ?? '-'} - {otherScore ?? '-'}
											</div>
											<div class="text-xs text-muted-foreground">score equipe</div>
										</div>
										{#if delta !== null}
											<div
												class="min-w-16 rounded-md border px-2 py-1 text-right text-xs {delta >= 0
													? 'tone-positive'
													: 'tone-negative'}"
											>
												<div class="font-semibold">{signed(delta)}</div>
												<div class="text-muted-foreground">Elo</div>
											</div>
										{/if}
									</div>
								</a>
							{/each}
						</div>
					{/if}
				</CardContent>
			</Card>
		{/if}

		{#if data.comparisonStatsError}
			<Card>
				<CardContent class="py-6 text-sm text-destructive">
					{data.comparisonStatsError}
				</CardContent>
			</Card>
		{/if}

		{#if data.comparisonRatingHistoryError}
			<Card>
				<CardContent class="py-6 text-sm text-destructive">
					{data.comparisonRatingHistoryError}
				</CardContent>
			</Card>
		{/if}

		{#if data.ratingHistoryError}
			<Card>
				<CardContent class="py-6 text-sm text-destructive">
					{data.ratingHistoryError}
				</CardContent>
			</Card>
		{:else if pointCount === 0}
			<Card>
				<CardHeader>
					<CardTitle>Historique Elo ({selectedScopeLabel})</CardTitle>
				</CardHeader>
				<CardContent class="py-6 text-sm text-muted-foreground">
					Aucun point d'historique Elo pour cette periode.
				</CardContent>
			</Card>
		{:else}
			<Card class="bg-[hsl(var(--surface-container-low))]">
				<CardHeader class="flex flex-row items-start justify-between gap-4">
					<div class="space-y-1">
						<CardTitle>
							{chart.series.length > 1
								? `Historique Elo : ${selectedPlayerName} vs ${selectedComparePlayerName} (${selectedScopeLabel})`
								: `Historique Elo de ${selectedPlayerName} (${selectedScopeLabel})`}
						</CardTitle>
						<p class="text-xs text-muted-foreground">
							Evolution de l'Elo sur les snapshots enregistres
						</p>
						<div class="flex flex-wrap gap-3 text-xs">
							{#each chart.series as series (series.key)}
								<span class="inline-flex items-center gap-1.5 text-muted-foreground">
									<span class="h-2.5 w-2.5 rounded-full" style={`background-color: ${series.color}`}
									></span>
									{series.name}
								</span>
							{/each}
						</div>
					</div>
					<div class="tone-accent-soft rounded-full px-3 py-1 text-xs font-medium">
						{pointCount} points
					</div>
				</CardHeader>
				<CardContent class="space-y-3">
					<svg
						class="h-72 w-full"
						viewBox={`0 0 ${chart.width} ${chart.height}`}
						preserveAspectRatio="xMinYMin meet"
						role="img"
						aria-label={chart.series.length > 1
							? `Graphique d'historique Elo de ${selectedPlayerName} et ${selectedComparePlayerName}`
							: `Graphique d'historique Elo de ${selectedPlayerName}`}
						onpointermove={handleChartPointerMove}
						onpointerleave={() => (hoveredPointRef = null)}
					>
						<defs>
							{#each chart.series as series (series.key)}
								<linearGradient id={series.gradientId} x1="0" y1="0" x2="0" y2="1">
									<stop offset="0%" stop-color={series.fillTop}></stop>
									<stop offset="100%" stop-color={series.fillBottom}></stop>
								</linearGradient>
							{/each}
						</defs>
						<rect
							x={chart.leftX}
							y={chart.topY}
							width={chart.rightX - chart.leftX}
							height={chart.bottomY - chart.topY}
							rx="12"
							fill="hsl(var(--muted))"
							opacity="0.25"
						/>
						{#each chart.yTicks as tick (tick.value)}
							<line
								x1={chart.leftX}
								y1={tick.y}
								x2={chart.rightX}
								y2={tick.y}
								stroke="hsl(var(--border))"
								stroke-width="1"
								stroke-dasharray={tick.y === chart.bottomY ? undefined : '4 4'}
							/>
							<text
								x={chart.leftX - 8}
								y={tick.y + 4}
								text-anchor="end"
								fill="hsl(var(--muted-foreground))"
								class="text-[10px]"
							>
								{tick.value.toFixed(0)}
							</text>
						{/each}
						{#each chart.series as series (series.key)}
							<path
								d={series.areaPath}
								fill={`url(#${series.gradientId})`}
								stroke="none"
								opacity={chart.series.length > 1 ? '0.72' : '1'}
							/>
						{/each}
						{#each chart.series as series (series.key)}
							<path
								d={series.path}
								fill="none"
								stroke={series.color}
								stroke-width="7"
								stroke-linecap="round"
								stroke-linejoin="round"
								opacity="0.14"
							/>
							<path
								d={series.path}
								fill="none"
								stroke={series.color}
								stroke-width="3"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
						{/each}
						{#if hoveredPoint && hoveredSeries}
							<line
								x1={hoveredPoint.x}
								y1={chart.topY}
								x2={hoveredPoint.x}
								y2={chart.bottomY}
								stroke={hoveredSeries.color}
								stroke-width="1"
								stroke-dasharray="4 4"
								opacity="0.7"
							/>
							<circle
								cx={hoveredPoint.x}
								cy={hoveredPoint.y}
								r="4"
								fill={hoveredSeries.color}
								stroke="hsl(var(--background))"
								stroke-width="2"
							/>
						{/if}
						{#each chart.xTicks as tick (tick.x)}
							<text
								x={tick.x}
								y={chart.height - 14}
								text-anchor="middle"
								fill="hsl(var(--muted-foreground))"
								class="text-[10px]"
							>
								{tick.label}
							</text>
						{/each}
						{#if hoveredPoint && hoveredSeries && tooltipBox}
							<g transform={`translate(${tooltipBox.x}, ${tooltipBox.y})`}>
								<rect
									width={tooltipBox.width}
									height={tooltipBox.height}
									rx="10"
									fill="hsl(var(--background))"
									stroke={hoveredSeries.strongColor}
									stroke-width="1.5"
									opacity="0.97"
								/>
								<text x="12" y="20" fill="hsl(var(--foreground))" class="text-[11px] font-semibold">
									{hoveredSeries.name}
								</text>
								<text x="12" y="38" fill="hsl(var(--foreground))" class="text-[11px] font-semibold">
									{hoveredPoint.dateLabel}
								</text>
								<text x="12" y="56" fill="hsl(var(--muted-foreground))" class="text-[11px]">
									Valeur : {muAmount(hoveredPoint.mu)}
								</text>
								<text x="12" y="72" fill="hsl(var(--muted-foreground))" class="text-[11px]">
									Rang : {hoveredPoint.rank} ({scopeToLabel(hoveredPoint.rankType)})
								</text>
								<text x="12" y="88" fill="hsl(var(--muted-foreground))" class="text-[11px]">
									Sigma: {hoveredPoint.sigma === null ? '—' : hoveredPoint.sigma.toFixed(1)}
								</text>
								<text x="12" y="104" fill="hsl(var(--muted-foreground))" class="text-[11px]">
									Δ precedent : {hoveredDelta === null ? '—' : signed(hoveredDelta)}
								</text>
							</g>
						{/if}
					</svg>
					<div class="flex items-center justify-between text-xs text-muted-foreground">
						<span>{chart.startDate}</span>
						<span class="rounded-full border border-border/60 px-2 py-0.5">Periode</span>
						<span>{chart.endDate}</span>
					</div>
					{#if chart.series.length > 1}
						<div class="grid gap-2 text-xs md:grid-cols-2">
							{#each chart.series as series (series.key)}
								<div class="rounded-lg border border-border/60 bg-background/70 p-3">
									<div class="flex items-center gap-2 font-semibold">
										<span
											class="h-2.5 w-2.5 rounded-full"
											style={`background-color: ${series.color}`}
										></span>
										{series.name}
									</div>
									<div class="mt-3 grid grid-cols-2 gap-2">
										<div>
											<div class="text-muted-foreground">Minimum</div>
											<div class="mt-1 font-semibold">{muAmount(series.minMu)}</div>
										</div>
										<div>
											<div class="text-muted-foreground">Maximum</div>
											<div class="mt-1 font-semibold">{muAmount(series.maxMu)}</div>
										</div>
										<div>
											<div class="text-muted-foreground">Actuel</div>
											<div class="mt-1 font-semibold">{muAmount(series.latestMu)}</div>
										</div>
										<div>
											<div class="text-muted-foreground">Tendance</div>
											<div
												class="mt-1 font-semibold {series.trendDelta >= 0
													? 'tone-positive'
													: 'tone-negative'}"
											>
												{signed(series.trendDelta)}
											</div>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{:else}
						<div class="grid grid-cols-2 gap-2 text-xs lg:grid-cols-4">
							<div class="rounded-lg border border-border/60 bg-background/70 p-2">
								<div class="text-muted-foreground">Elo minimum</div>
								<div class="mt-1 font-semibold">{muAmount(chart.minMu)}</div>
							</div>
							<div class="rounded-lg border border-border/60 bg-background/70 p-2">
								<div class="text-muted-foreground">Elo maximum</div>
								<div class="mt-1 font-semibold">{muAmount(chart.maxMu)}</div>
							</div>
							<div class="tone-accent-soft rounded-lg p-2">
								<div>Actuel</div>
								<div class="mt-1 font-semibold">{muAmount(chart.latestMu)}</div>
							</div>
							<div class="tone-accent-soft rounded-lg p-2">
								<div>Tendance</div>
								<div
									class="mt-1 font-semibold {trendDelta >= 0 ? 'tone-positive' : 'tone-negative'}"
								>
									{signed(trendDelta)}
								</div>
							</div>
						</div>
						<div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
							{#each recentHistory as point (point.dateLabel)}
								<div class="tone-accent-soft rounded-lg px-2.5 py-2 text-xs">
									<div class="text-muted-foreground">{point.dateLabel}</div>
									<div class="mt-0.5 font-semibold">{muAmount(point.mu)}</div>
								</div>
							{/each}
						</div>
					{/if}
				</CardContent>
			</Card>
		{/if}
	{/if}
</section>
