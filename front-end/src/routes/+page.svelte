<script lang="ts">
    import {Button} from '$lib/components/ui/button';
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import type {GameRead} from "$lib/api/types";
    import type {LeaderboardRow, Player} from "./+page";

    export let data: {
        games: GameRead[];
        lastTenZeroMatch: GameRead | null;
        top3: LeaderboardRow[];
    };

    // ——— Helpers for matches, using your actual shape ———
    const teamPlayers = (g: GameRead, n: 1 | 2): Player[] =>
        (
            g?.teams
                ?.filter((t) => t.team_number === n)
                .map((t) => t.player)
                .filter((p) => !!p) as Player[] | undefined
        ) ?? [];

    const nameOf = (p?: Player) => p?.player_name ?? '—';
    const teamLabel = (g: GameRead, n: 1 | 2) => {
        const names = teamPlayers(g, n).map((p) => nameOf(p)).filter((name) => name !== '—');
        return names.length > 0 ? names.join(' / ') : `Equipe ${n}`;
    };

    const scoreA = (g: GameRead) => g.result_team1 ?? 0;
    const scoreB = (g: GameRead) => g.result_team2 ?? 0;

    const winnerTeam = (g: GameRead): 0 | 1 | 2 => {
        const a = scoreA(g);
        const b = scoreB(g);
        if (a === b) return 0;
        return a > b ? 1 : 2;
    };

    type TeamOutcome = 'winner' | 'defeated' | 'draw';
    const teamOutcome = (g: GameRead, n: 1 | 2): TeamOutcome => {
        const winner = winnerTeam(g);
        if (winner === 0) return 'draw';
        return winner === n ? 'winner' : 'defeated';
    };

    const outcomeLabel = (outcome: TeamOutcome) =>
        outcome === 'winner' ? 'Winner' : outcome === 'defeated' ? 'Defeated' : 'Draw';
    const outcomeClass = (outcome: TeamOutcome) =>
        outcome === 'winner' ? 'tone-positive' : outcome === 'defeated' ? 'tone-negative' : 'text-muted-foreground';

    const scoreClass = (left: number, right: number) => (left > right ? 'tone-positive' : 'text-foreground');

    const getOverallDelta = (g: GameRead, playerId: number): number | null => {
        const change = g.rating_changes?.find((item) => item.player_id === playerId && item.rating_type === 'overall');
        return typeof change?.delta_mu === 'number' ? change.delta_mu : null;
    };

    const formatDelta = (delta: number | null) => {
        if (delta === null) return null;
        return `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`;
    };

    const deltaClass = (delta: number | null) => {
        if (delta === null) return 'text-muted-foreground';
        if (delta > 0) return 'tone-positive';
        if (delta < 0) return 'tone-negative';
        return 'text-muted-foreground';
    };

    const dateDMY = (iso: string) =>
        new Date(iso).toLocaleDateString(undefined, {day: '2-digit', month: 'short', year: 'numeric'});
    const timeHHMM = (iso: string) =>
        new Date(iso).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

    // ——— Helpers for leaderboard ———
    const rowName = (r: LeaderboardRow) => r?.player_name ?? 'Joueur';

    const rowRating = (r: LeaderboardRow) => r?.mu ?? r?.rating?.mu_monthly;
    const rowWL = (r: LeaderboardRow) => `${r.wins ?? 0}-${Math.max(0, (r.games_played ?? 0) - (r.wins ?? 0))}`;
    const ratingLabel = (r: LeaderboardRow) => {
        const rating = rowRating(r);
        return typeof rating === 'number' ? rating.toFixed(1) : '—';
    };
    const podiumClass = (idx: number) => {
        if (idx === 0) return 'bg-[hsl(var(--primary-container))] text-[hsl(var(--primary-container-foreground))]';
        if (idx === 1) return 'bg-secondary text-secondary-foreground';
        return 'bg-muted text-muted-foreground';
    };

</script>

<div class="mx-auto max-w-[1400px] space-y-6 px-4 py-4">
    <section
            class="relative overflow-hidden rounded-[28px] bg-[linear-gradient(135deg,hsl(var(--primary))_0%,hsl(146_79%_24%)_100%)] text-primary-foreground shadow-[0_20px_46px_rgba(0,107,36,0.28)]"
    >
        <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,rgba(85,254,117,0.22),transparent_44%)]"></div>
        <div class="relative space-y-6 p-7 md:p-10">
            <div class="space-y-3">
                <p class="editorial-kicker text-white/75">Player Dashboard</p>
                <h1 class="font-display text-4xl font-black uppercase tracking-tight sm:text-5xl">Welcome Back, Champ.</h1>
                <p class="max-w-2xl text-white/80">
                    Suivez les matchs, l'evolution du classement et les performances des joueurs.
                </p>
            </div>
            <div class="flex flex-wrap gap-3">
                <Button class="bg-white text-primary hover:bg-white/90" href="/create" size="lg">
                    Nouveau Match
                </Button>
                <Button class="border border-white/20 bg-white/10 text-white hover:bg-white/20 hover:text-white" href="/leaderboard" size="lg" variant="outline">
                    Voir le Classement
                </Button>
            </div>
            <div class="flex flex-wrap gap-2 text-xs">
                <span class="rounded-full bg-white/12 px-3 py-1 text-white/80">
                    {data?.games?.length ?? 0} matchs recents
                </span>
                <span class="rounded-full bg-white/12 px-3 py-1 text-white/80">
                    {data?.top3?.length ?? 0} meilleurs joueurs ce mois-ci
                </span>
            </div>
            {#if data.lastTenZeroMatch}
                <span
                        class="inline-flex max-w-full items-center gap-2 rounded-xl bg-white/14 px-3 py-2 text-xs text-white"
                >
                    <span class="font-semibold uppercase tracking-[0.12em] text-[hsl(var(--primary-container))]">Derniere Fanny</span>
                    <span class="truncate">
                        {dateDMY(data.lastTenZeroMatch.game_timestamp)}
                        :
                        {teamLabel(data.lastTenZeroMatch, 1)}
                        {data.lastTenZeroMatch.result_team1}-{data.lastTenZeroMatch.result_team2}
                        {teamLabel(data.lastTenZeroMatch, 2)}
                    </span>
                </span>
            {:else}
                <span class="inline-flex items-center rounded-xl bg-white/12 px-3 py-2 text-xs text-white/80">
                    Aucun match 10-0 enregistre pour le moment.
                </span>
            {/if}
        </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card
                class="overflow-hidden rounded-3xl bg-[hsl(var(--surface-container-low))]"
        >
            <CardHeader class="flex flex-row items-center justify-between gap-3 pb-2">
                <CardTitle class="font-display text-3xl font-bold uppercase tracking-tight">Recent Matches</CardTitle>
                <Button class="h-8 rounded-lg px-3" href="/matches" variant="ghost">Voir tous</Button>
            </CardHeader>
            <CardContent>
                {#if data?.games?.length}
                    <ul class="space-y-2">
                        {#each data.games as g}
                            {@const outcome1 = teamOutcome(g, 1)}
                            {@const outcome2 = teamOutcome(g, 2)}
                            {@const team1Players = teamPlayers(g, 1)}
                            {@const team2Players = teamPlayers(g, 2)}
                            <li>
                                <a
                                        class="group block rounded-2xl border border-border/65 bg-card/90 px-4 py-4 transition hover:border-border"
                                        href={`/matches/${g.id}`}
                                        aria-label="Ouvrir les details du match"
                                >
                                    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                                        <div class="overflow-x-auto">
                                            <div class="grid min-w-[640px] grid-cols-[minmax(0,170px)_auto_auto_minmax(0,170px)_auto] items-center gap-x-4">
                                                <div class="min-w-0 space-y-1.5">
                                                    <p class={`editorial-kicker ${outcomeClass(outcome1)}`}>{outcomeLabel(outcome1)}</p>
                                                    {#if team1Players.length}
                                                        {#each team1Players as p}
                                                            <p class="truncate text-[1.05rem] font-semibold">{nameOf(p)}</p>
                                                        {/each}
                                                    {:else}
                                                        <p class="truncate text-[1.05rem] text-muted-foreground">Equipe 1</p>
                                                    {/if}
                                                </div>

                                                <div class="space-y-1.5 pt-5 text-right">
                                                    {#if team1Players.length}
                                                        {#each team1Players as p}
                                                            {@const deltaValue = getOverallDelta(g, p.id)}
                                                            {@const deltaLabel = formatDelta(deltaValue)}
                                                            {#if deltaLabel}
                                                                <p class={`text-[1.05rem] font-semibold tabular-nums ${deltaClass(deltaValue)}`}>{deltaLabel}</p>
                                                            {:else}
                                                                <p class="text-[1.05rem] tabular-nums text-muted-foreground/40">—</p>
                                                            {/if}
                                                        {/each}
                                                    {/if}
                                                </div>

                                                <div class="min-w-[96px] text-center">
                                                    <div class="font-display text-[2rem] font-bold leading-none tabular-nums sm:text-[2.2rem]">
                                                        <span class={scoreClass(scoreA(g), scoreB(g))}>{scoreA(g)}</span>
                                                        <span class="mx-1 text-muted-foreground">-</span>
                                                        <span class={scoreClass(scoreB(g), scoreA(g))}>{scoreB(g)}</span>
                                                    </div>
                                                    <p class="mt-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground/80">Final score</p>
                                                </div>

                                                <div class="min-w-0 space-y-1.5">
                                                    <p class={`editorial-kicker ${outcomeClass(outcome2)}`}>{outcomeLabel(outcome2)}</p>
                                                    {#if team2Players.length}
                                                        {#each team2Players as p}
                                                            <p class="truncate text-[1.05rem] font-semibold">{nameOf(p)}</p>
                                                        {/each}
                                                    {:else}
                                                        <p class="truncate text-[1.05rem] text-muted-foreground">Equipe 2</p>
                                                    {/if}
                                                </div>

                                                <div class="space-y-1.5 pt-5 text-right">
                                                    {#if team2Players.length}
                                                        {#each team2Players as p}
                                                            {@const deltaValue = getOverallDelta(g, p.id)}
                                                            {@const deltaLabel = formatDelta(deltaValue)}
                                                            {#if deltaLabel}
                                                                <p class={`text-[1.05rem] font-semibold tabular-nums ${deltaClass(deltaValue)}`}>{deltaLabel}</p>
                                                            {:else}
                                                                <p class="text-[1.05rem] tabular-nums text-muted-foreground/40">—</p>
                                                            {/if}
                                                        {/each}
                                                    {/if}
                                                </div>
                                            </div>
                                        </div>

                                        <div class="text-right text-xs text-muted-foreground">
                                            <p class="font-semibold text-foreground/80">{timeHHMM(g.game_timestamp)}</p>
                                            <p class="uppercase tracking-[0.08em]">{dateDMY(g.game_timestamp)}</p>
                                        </div>
                                    </div>
                                </a>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <div class="rounded-2xl bg-card py-10 text-center text-sm text-muted-foreground">
                        Aucun match pour l'instant. Creez-en un.
                    </div>
                {/if}
            </CardContent>
        </Card>

        <Card class="rounded-3xl bg-[hsl(var(--surface-container-low))]">
            <CardHeader class="pb-2">
                <CardTitle class="font-display text-2xl font-bold uppercase tracking-tight">Top Contenders</CardTitle>
            </CardHeader>
            <CardContent>
                {#if data?.top3?.length}
                    <ol class="space-y-2">
                        {#each data.top3 as row, idx}
                            <li class="rounded-2xl bg-card p-3">
                                <a class="flex items-center justify-between gap-3" href={`/stats?player_id=${row.id}&scope=overall`}>
                                    <div class="flex min-w-0 items-center gap-3">
                                        <div class="grid h-10 w-10 place-items-center rounded-xl text-sm font-semibold {podiumClass(idx)}">
                                            #{idx + 1}
                                        </div>
                                        <div class="min-w-0">
                                            <p class="truncate font-medium">{rowName(row)}</p>
                                            <p class="text-xs text-muted-foreground">V-D : {rowWL(row)}</p>
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <p class="font-semibold tabular-nums">{ratingLabel(row)}</p>
                                        <p class="text-xs text-muted-foreground">Elo</p>
                                    </div>
                                </a>
                            </li>
                        {/each}
                    </ol>

                    <div class="flex justify-end">
                        <Button class="rounded-lg" href="/leaderboard" size="sm" variant="outline">Classement entier</Button>
                    </div>
                {:else}
                    <div class="rounded-2xl bg-card py-10 text-center text-sm text-muted-foreground">
                        Pas encore de classement.
                    </div>
                {/if}
            </CardContent>
        </Card>
    </section>
</div>
