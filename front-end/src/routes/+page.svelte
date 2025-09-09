<script lang="ts">
    // Types aligned to your payload


    import {Button} from '$lib/components/ui/button';
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import {Separator} from '$lib/components/ui/separator';
    import type {GameRead, LeaderboardRow, Player} from "./+page";

    export let data: {
        games: GameRead[];
        top3: LeaderboardRow[];
    };

    // ——— Helpers for matches, using your actual shape ———
    const teamPlayers = (g: GameRead, n: 1 | 2): (Player | undefined)[] =>
        g?.teams?.filter((t) => t.team_number === n).map((t) => t.player) ?? [];

    const nameOf = (p: Player) => p?.player_name ?? '—';

    const scoreA = (g: GameRead) => g.result_team1 ?? 0;
    const scoreB = (g: GameRead) => g.result_team2 ?? 0;

    const aWon = (g: GameRead) => (scoreA(g) === scoreB(g) ? null : scoreA(g) > scoreB(g));

    const dateDMY = (iso: string) =>
        new Date(iso).toLocaleDateString(undefined, {day: '2-digit', month: 'short', year: 'numeric'});
    const timeHHMM = (iso: string) =>
        new Date(iso).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

    // ——— Helpers for leaderboard ———
    const rowName = (r: LeaderboardRow) =>
        r?.player_name ?? r?.name ?? r?.display_name ?? r?.username ?? 'Player';

    const rowRating = (r: LeaderboardRow) => r?.rating?.mu_monthly ?? r?.elo ?? r?.points ?? r?.score;
    const rowWL = (r: LeaderboardRow) =>
        typeof r?.wins === 'number' || typeof r?.losses === 'number'
            ? `${r.wins ?? 0}-${r.losses ?? 0}`
            : undefined;


</script>

<!-- HERO -->
<section class="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
    <h1 class="text-5xl font-bold mb-4 tracking-tight">Welcome to Foosball Arena</h1>
    <p class="mb-8 text-lg text-muted-foreground max-w-prose">
        Track matches, view leaderboards, and analyze stats.
    </p>
    <div class="flex gap-3">
        <Button as="a" href="/create" size="lg">Create Match</Button>
        <Button as="a" href="/leaderboard" size="lg" variant="outline">View Leaderboard</Button>
    </div>
</section>

<!-- QUICK GLANCE PANELS -->
<section class="container mx-auto px-6 pb-16">
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <!-- Recent Matches -->
        <Card class="lg:col-span-3">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle class="text-xl">Recent Matches</CardTitle>
                <Button as="a" class="h-8 px-2" href="/matches" variant="ghost">See all</Button>
            </CardHeader>
            <CardContent>
                {#if data?.games?.length}
                    <ul class="divide-y rounded-lg overflow-hidden border">
                        {#each data.games as g}
                            <li class="even:bg-muted/40">
                                <a class="block px-3 py-2.5 sm:px-4 sm:py-3" href={`/matches/${g.id}`}
                                   aria-label="Open match details">
                                    <!-- 5-col grid: time | team1 | A | B | team2 -->
                                    <div
                                            class="grid items-center gap-x-2 sm:gap-x-3
           grid-cols-[auto_minmax(0,1fr)_auto_auto_minmax(0,1fr)]">

                                        <!-- date + time -->
                                        <div class="pr-1">
                                            <p class="text-xs sm:text-sm tabular-nums leading-tight">{dateDMY(g.game_timestamp)}</p>
                                            <p class="italic text-xs text-muted-foreground tabular-nums leading-tight">
                                                {timeHHMM(g.game_timestamp)}
                                            </p>
                                        </div>

                                        <!-- team 1 (added horizontal padding) -->
                                        <div class="min-w-0 pl-20">
                                            <div class="text-sm leading-snug ">
                                                {#if teamPlayers(g, 1).length}
                                                    {#each teamPlayers(g, 1).slice(0, 2) as p}
                                                        <p class="truncate flex items-center gap-1.5">

                                                            {nameOf(p)}
                                                        </p>
                                                    {/each}
                                                    {#if teamPlayers(g, 1).length > 2}
                                                        <p class="truncate text-muted-foreground text-[11px]">
                                                            +{teamPlayers(g, 1).length - 2} more
                                                        </p>
                                                    {/if}
                                                {:else}
                                                    <p class="truncate">Team 1</p>
                                                {/if}
                                            </div>
                                        </div>

                                        <!-- score A (modern colors) -->
                                        <div class="text-right pl-1">
                                            {#if aWon(g) !== null}
                                                <p class="text-xl sm:text-2xl font-extrabold tracking-tight tabular-nums
                  {aWon(g) ? 'text-emerald-400' : 'text-white'}">
                                                    {scoreA(g)}
                                                </p>
                                            {:else}
                                                <p class="text-lg font-bold tabular-nums">{scoreA(g)}</p>
                                            {/if}
                                        </div>

                                        <!-- score B (modern colors, inverse) -->
                                        <div class="text-left pr-1">
                                            {#if aWon(g) !== null}
                                                <p class="text-xl sm:text-2xl font-extrabold tracking-tight tabular-nums
                  {aWon(g) ? 'text-white' : 'text-emerald-400'}">
                                                    {scoreB(g)}
                                                </p>
                                            {:else}
                                                <p class="text-lg font-bold tabular-nums">{scoreB(g)}</p>
                                            {/if}
                                        </div>

                                        <!-- team 2 (added horizontal padding) -->
                                        <div class="min-w-0 text-right pr-20">
                                            <div class="text-sm leading-snug">
                                                {#if teamPlayers(g, 2).length}
                                                    {#each teamPlayers(g, 2).slice(0, 2) as p}
                                                        <p class="truncate flex items-center justify-end gap-1.5">
                                                            <span class="truncate">{nameOf(p)}</span>

                                                        </p>
                                                    {/each}
                                                    {#if teamPlayers(g, 2).length > 2}
                                                        <p class="truncate text-muted-foreground text-[11px]">
                                                            +{teamPlayers(g, 2).length - 2} more
                                                        </p>
                                                    {/if}
                                                {:else}
                                                    <p class="truncate">Team 2</p>
                                                {/if}
                                            </div>
                                        </div>
                                    </div>
                                </a>
                            </li>
                        {/each}
                    </ul>
                {:else}
                    <p class="text-sm text-muted-foreground">No matches yet. Be the first to create one!</p>
                {/if}
            </CardContent>
        </Card>

        <!-- Top 3 Leaderboard -->
        <Card class="lg:col-span-2">
            <CardHeader class="pb-4">
                <CardTitle class="text-xl">Top Players (Monthly)</CardTitle>
            </CardHeader>
            <CardContent>
                {#if data?.top3?.length}
                    <ol class="space-y-4">
                        {#each data.top3 as row, idx}
                            <li class="flex items-center justify-between rounded-2xl border p-3">
                                <div class="flex items-center gap-3 min-w-0">
                                    <div class="w-9 h-9 rounded-full grid place-items-center border">
                                        <span class="text-sm font-semibold">#{idx + 1}</span>
                                    </div>
                                    <div class="min-w-0">
                                        <p class="font-medium truncate">{rowName(row)}</p>
                                        <p class="text-xs text-muted-foreground">
                                            {#if rowWL(row)}
                                                W–L: {rowWL(row)}
                                            {:else}
                                                &nbsp;
                                            {/if}
                                        </p>
                                    </div>
                                </div>
                                <div class="text-right">
                                    {#if rowRating(row) !== undefined}
                                        <p class="font-semibold tabular-nums">{rowRating(row)}</p>
                                        <p class="text-xs text-muted-foreground">Rating</p>
                                    {:else}
                                        <p class="text-xs text-muted-foreground">—</p>
                                    {/if}
                                </div>
                            </li>
                        {/each}
                    </ol>

                    <Separator class="my-4"/>
                    <div class="flex justify-end">
                        <Button as="a" href="/leaderboard" size="sm" variant="outline">Full Leaderboard</Button>
                    </div>
                {:else}
                    <p class="text-sm text-muted-foreground">No leaderboard data yet.</p>
                {/if}
            </CardContent>
        </Card>
    </div>
</section>
