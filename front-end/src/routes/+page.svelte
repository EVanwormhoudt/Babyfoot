<script lang="ts">
    import {Button} from '$lib/components/ui/button';
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import {Separator} from '$lib/components/ui/separator';
    import type {GameRead} from "$lib/api/types";
    import type {LeaderboardRow, Player} from "./+page";

    export let data: {
        games: GameRead[];
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

    const scoreA = (g: GameRead) => g.result_team1 ?? 0;
    const scoreB = (g: GameRead) => g.result_team2 ?? 0;

    const aWon = (g: GameRead) => (scoreA(g) === scoreB(g) ? null : scoreA(g) > scoreB(g));

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
        if (idx === 0) return 'border-amber-400/45 bg-amber-500/10 text-amber-200';
        if (idx === 1) return 'border-slate-400/45 bg-slate-500/10 text-slate-200';
        return 'border-orange-400/45 bg-orange-500/10 text-orange-200';
    };

</script>

<div class="mx-auto max-w-[1400px] space-y-6 px-4 py-4">
    <section
            class="relative overflow-hidden rounded-3xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950/20 via-background to-background/90 shadow-[0_18px_45px_rgba(0,0,0,0.25)]"
    >
        <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.16),transparent_45%)]"></div>
        <div class="relative space-y-6 p-7 md:p-10">
            <div class="space-y-3">
                <p class="text-xs uppercase tracking-[0.2em] text-emerald-300/80">Tableau de bord BabyFoot</p>
                <h1 class="text-4xl font-black tracking-tight sm:text-5xl">BabyFoot MyDSO</h1>
                <p class="max-w-2xl text-muted-foreground">
                    Suivez les matchs, l'evolution du classement et les performances des joueurs.
                </p>
            </div>
            <div class="flex flex-wrap gap-3">
                <Button class="rounded-xl bg-emerald-500 font-semibold text-black hover:bg-emerald-400" href="/create" size="lg">
                    Nouveau Match
                </Button>
                <Button class="rounded-xl" href="/leaderboard" size="lg" variant="outline">
                    Voir le Classement
                </Button>
            </div>
            <div class="flex flex-wrap gap-2 text-xs">
                <span class="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-muted-foreground">
                    {data?.games?.length ?? 0} matchs recents
                </span>
                <span class="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-muted-foreground">
                    {data?.top3?.length ?? 0} meilleurs joueurs ce mois-ci
                </span>
            </div>
        </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card
                class="overflow-hidden rounded-3xl border border-emerald-500/15 bg-gradient-to-br from-emerald-950/10 via-background to-background/90 shadow-[0_12px_32px_rgba(0,0,0,0.2)]"
        >
            <CardHeader class="flex flex-row items-center justify-between gap-3 pb-2">
                <CardTitle class="text-xl font-semibold tracking-tight">Matchs Récents</CardTitle>
                <Button class="h-8 rounded-lg px-3" href="/matches" variant="ghost">Voir tous</Button>
            </CardHeader>
            <CardContent>
                {#if data?.games?.length}
                    <ul class="space-y-2">
                        {#each data.games as g}
                            <li>
                                <a
                                        class="group block rounded-2xl border border-border/60 bg-background/65 p-3 transition hover:border-emerald-500/35 hover:bg-emerald-500/10"
                                        href={`/matches/${g.id}`}
                                        aria-label="Ouvrir les details du match"
                                >
                                    <div class="flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                                        <span>{dateDMY(g.game_timestamp)}</span>
                                        <span>{timeHHMM(g.game_timestamp)}</span>
                                    </div>

                                    <div class="mt-3 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
                                        <div class="min-w-0 space-y-1 text-right">
                                            {#if teamPlayers(g, 1).length}
                                                {#each teamPlayers(g, 1).slice(0, 2) as p}
                                                    <p class="truncate text-sm">{nameOf(p)}</p>
                                                {/each}
                                                {#if teamPlayers(g, 1).length > 2}
                                                    <p class="truncate text-[11px] text-muted-foreground">
                                                        +{teamPlayers(g, 1).length - 2} de plus
                                                    </p>
                                                {/if}
                                            {:else}
                                                <p class="truncate text-sm text-muted-foreground">Equipe 1</p>
                                            {/if}
                                        </div>

                                        <div class="rounded-xl border border-border/60 bg-background/80 px-4 py-2 text-center shadow-inner">
                                            <div class="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Score</div>
                                            <div class="mt-1 flex items-baseline justify-center gap-1.5 tabular-nums">
                                                <span class="text-2xl font-black {aWon(g) === true ? 'text-emerald-400' : 'text-foreground/90'}">{scoreA(g)}</span>
                                                <span class="text-muted-foreground">-</span>
                                                <span class="text-2xl font-black {aWon(g) === false ? 'text-emerald-400' : 'text-foreground/90'}">{scoreB(g)}</span>
                                            </div>
                                        </div>

                                        <div class="min-w-0 space-y-1">
                                            {#if teamPlayers(g, 2).length}
                                                {#each teamPlayers(g, 2).slice(0, 2) as p}
                                                    <p class="truncate text-sm">{nameOf(p)}</p>
                                                {/each}
                                                {#if teamPlayers(g, 2).length > 2}
                                                    <p class="truncate text-[11px] text-muted-foreground">
                                                        +{teamPlayers(g, 2).length - 2} de plus
                                                    </p>
                                                {/if}
                                            {:else}
                                                <p class="truncate text-sm text-muted-foreground">Equipe 2</p>
                                            {/if}
                                        </div>
                                    </div>
                                </a>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <div class="rounded-2xl border border-dashed border-border/60 bg-background/40 py-10 text-center text-sm text-muted-foreground">
                        Aucun match pour l'instant. Creez-en un.
                    </div>
                {/if}
            </CardContent>
        </Card>

        <Card class="rounded-3xl border border-blue-500/20 bg-gradient-to-b from-blue-950/18 to-background shadow-[0_12px_30px_rgba(0,0,0,0.2)]">
            <CardHeader class="pb-2">
                <CardTitle class="text-xl font-semibold tracking-tight">Meilleurs joueurs (du mois)</CardTitle>
            </CardHeader>
            <CardContent>
                {#if data?.top3?.length}
                    <ol class="space-y-2">
                        {#each data.top3 as row, idx}
                            <li class="rounded-2xl border border-border/60 bg-background/70 p-3 transition hover:border-emerald-500/35 hover:bg-emerald-500/10">
                                <a class="flex items-center justify-between gap-3" href={`/stats?player_id=${row.id}&scope=overall`}>
                                    <div class="flex min-w-0 items-center gap-3">
                                        <div class="grid h-10 w-10 place-items-center rounded-xl border text-sm font-semibold {podiumClass(idx)}">
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

                    <Separator class="my-4"/>
                    <div class="flex justify-end">
                        <Button class="rounded-lg" href="/leaderboard" size="sm" variant="outline">Classement entier</Button>
                    </div>
                {:else}
                    <div class="rounded-2xl border border-dashed border-border/60 bg-background/40 py-10 text-center text-sm text-muted-foreground">
                        Pas encore de classement.
                    </div>
                {/if}
            </CardContent>
        </Card>
    </section>
</div>
