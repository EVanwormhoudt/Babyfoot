<script lang="ts">
    import {goto} from '$app/navigation';
    import {onMount} from 'svelte';
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import type {PlayerRatingHistoryPoint, Scope} from '$lib/api/players';
    import type {PageData} from './$types';
    import {getStoredCurrentPlayerId, setStoredCurrentPlayerId} from '$lib/current-player';

    type ChartPoint = {
        x: number;
        y: number;
        mu: number;
        dateLabel: string;
        sigma: number | null;
        rank: number;
        rankType: Scope;
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

    let {data} = $props<{ data: PageData }>();

    let selectedPlayerId = $state(data.selectedPlayerId ? String(data.selectedPlayerId) : '');
    let selectedScope = $state<Scope>(data.scope);
    let selectedYear = $state(String(data.selectedYear));
    let selectedMonth = $state(String(data.selectedMonth));
    let hoveredPointIndex = $state<number | null>(null);

    const monthOptions = [
        {value: 1, label: 'Janvier'},
        {value: 2, label: 'Fevrier'},
        {value: 3, label: 'Mars'},
        {value: 4, label: 'Avril'},
        {value: 5, label: 'Mai'},
        {value: 6, label: 'Juin'},
        {value: 7, label: 'Juillet'},
        {value: 8, label: 'Aout'},
        {value: 9, label: 'Septembre'},
        {value: 10, label: 'Octobre'},
        {value: 11, label: 'Novembre'},
        {value: 12, label: 'Decembre'}
    ];

    const selectedPlayer = $derived(
        data.players.find((p: { id: number }) => String(p.id) === selectedPlayerId)
    );

    const selectedPlayerName = $derived(
        selectedPlayer?.player_name ?? 'Joueur'
    );
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
        if (Number.isFinite(playerIdNum) && playerIdNum > 0) {
            setStoredCurrentPlayerId(playerIdNum);
        }

        const params = new URLSearchParams();
        if (selectedPlayerId) params.set('player_id', selectedPlayerId);
        params.set('scope', selectedScope);
        if (selectedScope !== 'overall') {
            params.set('year', selectedYear);
        }
        if (selectedScope === 'monthly') {
            params.set('month', selectedMonth);
        }

        goto(`?${params.toString()}`, {replaceState: true, noScroll: true});
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

    function buildHistoryChart(history: PlayerRatingHistoryPoint[]): ChartModel {
        const width = 760;
        const height = 290;
        const left = 56;
        const right = 18;
        const top = 20;
        const bottom = 46;

        const sorted = [...history]
            .filter((point): point is PlayerRatingHistoryPoint & { mu: number } => point.mu !== null)
            .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        const baselineMu = 1000;
        const firstNonBaselineIndex = sorted.findIndex((point) => Math.abs(point.mu - baselineMu) > 0.0001);
        const visible =
            firstNonBaselineIndex > 0
                ? sorted.slice(firstNonBaselineIndex)
                : sorted;

        if (visible.length === 0) {
            return {
                width,
                height,
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

        const muValues = visible.map((point) => point.mu);
        const dateValues = visible.map((point) => new Date(point.date).getTime());
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

        const points: ChartPoint[] = visible.map((point, index) => {
            const x = left + ((dateValues[index] - minDate) / dateSpan) * plotWidth;
            const y = top + (1 - ((point.mu - axisMin) / axisSpan)) * plotHeight;
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
            .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
            .join(' ');

        const areaPath = `${path} L ${points[points.length - 1].x.toFixed(2)} ${(
            top + plotHeight
        ).toFixed(2)} L ${points[0].x.toFixed(2)} ${(top + plotHeight).toFixed(2)} Z`;

        const yTicks: AxisYTick[] = [];
        for (let value = axisMax; value >= axisMin; value -= axisStep) {
            const ratio = (axisMax - value) / axisSpan;
            yTicks.push({
                y: top + ratio * plotHeight,
                value
            });
        }

        const xTicks: AxisXTick[] = visible.length === 1
            ? [{x: points[0].x, label: points[0].dateLabel}]
            : [
                {x: left, label: formatDate(visible[0].date)},
                {x: left + plotWidth / 2, label: formatTimestamp(minDate + dateSpan / 2)},
                {x: left + plotWidth, label: formatDate(visible[visible.length - 1].date)}
            ];

        return {
            width,
            height,
            path,
            areaPath,
            points,
            xTicks,
            yTicks,
            minMu,
            maxMu,
            latestMu: points[points.length - 1].mu,
            startDate: formatDate(visible[0].date),
            endDate: formatDate(visible[visible.length - 1].date),
            leftX: left,
            rightX: width - right,
            topY: top,
            midY: top + plotHeight / 2,
            bottomY: height - bottom
        };
    }

    const chart = $derived(buildHistoryChart(data.ratingHistory ?? []));
    const chartStroke = '#16a34a';
    const chartStrokeStrong = '#15803d';
    const chartAreaTop = 'rgba(34, 197, 94, 0.28)';
    const chartAreaBottom = 'rgba(34, 197, 94, 0.02)';
    const trendDelta = $derived(
        chart.points.length > 1
            ? chart.points[chart.points.length - 1].mu - chart.points[0].mu
            : 0
    );
    const recentHistory = $derived(chart.points.slice(-5));
    const pointCount = $derived(chart.points.length);
    function handleChartPointerMove(event: PointerEvent) {
        const svg = event.currentTarget as SVGSVGElement | null;
        if (!svg || chart.points.length === 0) {
            hoveredPointIndex = null;
            return;
        }

        const screenPoint = svg.createSVGPoint();
        screenPoint.x = event.clientX;
        screenPoint.y = event.clientY;

        const ctm = svg.getScreenCTM();
        if (!ctm) {
            hoveredPointIndex = null;
            return;
        }

        const localPoint = screenPoint.matrixTransform(ctm.inverse());
        if (
            localPoint.x < chart.leftX ||
            localPoint.x > chart.rightX ||
            localPoint.y < chart.topY ||
            localPoint.y > chart.bottomY
        ) {
            hoveredPointIndex = null;
            return;
        }

        let bestIndex = 0;
        let bestDistance = Number.POSITIVE_INFINITY;
        for (let index = 0; index < chart.points.length; index += 1) {
            const distance = Math.abs(chart.points[index].x - localPoint.x);
            if (distance < bestDistance) {
                bestDistance = distance;
                bestIndex = index;
            }
        }
        hoveredPointIndex = bestIndex;
    }
    const hoveredPoint = $derived(
        hoveredPointIndex !== null && hoveredPointIndex >= 0 && hoveredPointIndex < chart.points.length
            ? chart.points[hoveredPointIndex]
            : null
    );
    const hoveredDelta = $derived(
        hoveredPointIndex !== null && hoveredPointIndex > 0 && hoveredPointIndex < chart.points.length
            ? chart.points[hoveredPointIndex].mu - chart.points[hoveredPointIndex - 1].mu
            : null
    );
    const tooltipBox = $derived(
        hoveredPoint
            ? (() => {
                const width = 190;
                const height = 100;
                let x = hoveredPoint.x + 12;
                if (x + width > chart.rightX) {
                    x = hoveredPoint.x - width - 12;
                }
                let y = hoveredPoint.y - height - 12;
                if (y < chart.topY + 4) {
                    y = hoveredPoint.y + 12;
                }
                return {x, y, width, height};
            })()
            : null
    );
</script>

<section class="p-8 space-y-6">
    <h2 class="text-3xl font-semibold">Statistiques</h2>

    {#if data.players.length === 0}
        <Card>
                <CardContent class="py-8 text-center text-muted-foreground">
                Aucun joueur trouve.
                </CardContent>
        </Card>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
            <label class="flex flex-col gap-2">
                <span class="text-sm text-muted-foreground">Joueur</span>
                <select
                        bind:value={selectedPlayerId}
                        class="h-10 rounded-md border bg-background px-3 text-sm"
                        onchange={applyFilters}
                >
                    {#each data.players as player}
                        <option value={String(player.id)}>{player.player_name}</option>
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
                        {#each data.yearOptions as year}
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
                        {#each monthOptions as month}
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
                    <CardTitle>{selectedPlayerName} ({selectedScopeLabel})</CardTitle>
                </CardHeader>
                <CardContent class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
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
                        <div class="text-2xl font-semibold">{data.stats.average_opponent_score.toFixed(2)}</div>
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
                            {data.stats.best_teammate
                                ? `${data.stats.best_teammate.player_name} (${percent(data.stats.best_teammate.win_rate)})`
                                : '—'}
                        </div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Pire coequipier</div>
                        <div class="text-base font-medium">
                            {data.stats.worst_teammate
                                ? `${data.stats.worst_teammate.player_name} (${percent(data.stats.worst_teammate.win_rate)})`
                                : '—'}
                        </div>
                    </div>
                </CardContent>
            </Card>
        {/if}

        {#if data.ratingHistoryError}
            <Card>
                <CardContent class="py-6 text-sm text-destructive">
                    {data.ratingHistoryError}
                </CardContent>
            </Card>
        {:else if chart.points.length === 0}
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
                        <CardTitle>Historique Elo de {selectedPlayerName} ({selectedScopeLabel})</CardTitle>
                        <p class="text-xs text-muted-foreground">Evolution de l'Elo sur les snapshots enregistres</p>
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
                            aria-label={`Graphique d'historique Elo de ${selectedPlayerName}`}
                            onpointermove={handleChartPointerMove}
                            onpointerleave={() => (hoveredPointIndex = null)}
                    >
                        <defs>
                            <linearGradient id="rating-history-green-fill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stop-color={chartAreaTop}></stop>
                                <stop offset="100%" stop-color={chartAreaBottom}></stop>
                            </linearGradient>
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
                        {#each chart.yTicks as tick}
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
                        <path
                                d={chart.areaPath}
                                fill="url(#rating-history-green-fill)"
                                stroke="none"
                        />
                        <path
                                d={chart.path}
                                fill="none"
                                stroke={chartStroke}
                                stroke-width="7"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                opacity="0.16"
                        />
                        <path
                                d={chart.path}
                                fill="none"
                                stroke={chartStroke}
                                stroke-width="3"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                        />
                        {#if hoveredPoint}
                            <line
                                    x1={hoveredPoint.x}
                                    y1={chart.topY}
                                    x2={hoveredPoint.x}
                                    y2={chart.bottomY}
                                    stroke="#16a34a"
                                    stroke-width="1"
                                    stroke-dasharray="4 4"
                                    opacity="0.7"
                            />
                        {/if}
                        {#each chart.xTicks as tick}
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
                        {#if hoveredPoint && tooltipBox}
                            <g transform={`translate(${tooltipBox.x}, ${tooltipBox.y})`}>
                                <rect
                                        width={tooltipBox.width}
                                        height={tooltipBox.height}
                                        rx="10"
                                        fill="hsl(var(--background))"
                                        stroke="#86efac"
                                        stroke-width="1.5"
                                        opacity="0.97"
                                />
                                <text x="12" y="20" fill="hsl(var(--foreground))" class="text-[11px] font-semibold">
                                    {hoveredPoint.dateLabel}
                                </text>
                                <text x="12" y="38" fill="hsl(var(--muted-foreground))" class="text-[11px]">
                                    Valeur : {muAmount(hoveredPoint.mu)}
                                </text>
                                <text x="12" y="54" fill="hsl(var(--muted-foreground))" class="text-[11px]">
                                    Rang : {hoveredPoint.rank} ({scopeToLabel(hoveredPoint.rankType)})
                                </text>
                                <text x="12" y="70" fill="hsl(var(--muted-foreground))" class="text-[11px]">
                                    Sigma: {hoveredPoint.sigma === null ? '—' : hoveredPoint.sigma.toFixed(1)}
                                </text>
                                <text x="12" y="86" fill="hsl(var(--muted-foreground))" class="text-[11px]">
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
                            <div class="mt-1 font-semibold {trendDelta >= 0 ? 'tone-positive' : 'tone-negative'}">
                                {signed(trendDelta)}
                            </div>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
                        {#each recentHistory as point}
                            <div class="tone-accent-soft rounded-lg px-2.5 py-2 text-xs">
                                <div class="text-muted-foreground">{point.dateLabel}</div>
                                <div class="mt-0.5 font-semibold">{muAmount(point.mu)}</div>
                            </div>
                        {/each}
                    </div>
                </CardContent>
            </Card>
        {/if}
    {/if}
</section>
