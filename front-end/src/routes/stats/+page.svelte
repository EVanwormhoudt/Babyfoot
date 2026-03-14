<script lang="ts">
    import {goto} from '$app/navigation';
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import type {Scope} from '$lib/api/players';
    import type {PageData} from './$types';

    let {data} = $props<{ data: PageData }>();

    let selectedPlayerId = $state(data.selectedPlayerId ? String(data.selectedPlayerId) : '');
    let selectedScope = $state<Scope>(data.scope);

    const selectedPlayer = $derived(
        data.players.find((p: { id: number }) => String(p.id) === selectedPlayerId)
    );

    const selectedPlayerName = $derived(
        selectedPlayer?.player_name ?? 'Player'
    );

    function applyFilters() {
        const params = new URLSearchParams();
        if (selectedPlayerId) params.set('player_id', selectedPlayerId);
        params.set('scope', selectedScope);

        goto(`?${params.toString()}`, {replaceState: true, noScroll: true});
    }

    function percent(value: number) {
        return `${(value * 100).toFixed(1)}%`;
    }
</script>

<section class="p-8 space-y-6">
    <h2 class="text-3xl font-semibold">Stats</h2>

    {#if data.players.length === 0}
        <Card>
            <CardContent class="py-8 text-center text-muted-foreground">
                No players found.
            </CardContent>
        </Card>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <label class="flex flex-col gap-2">
                <span class="text-sm text-muted-foreground">Who are you?</span>
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
                <span class="text-sm text-muted-foreground">Scope</span>
                <select
                        bind:value={selectedScope}
                        class="h-10 rounded-md border bg-background px-3 text-sm"
                        onchange={applyFilters}
                >
                    <option value="overall">Overall</option>
                    <option value="monthly">Monthly</option>
                    <option value="yearly">Yearly</option>
                </select>
            </label>
        </div>

        {#if data.statsError}
            <Card>
                <CardContent class="py-6 text-sm text-red-500">
                    {data.statsError}
                </CardContent>
            </Card>
        {:else if data.stats}
            <Card>
                <CardHeader>
                    <CardTitle>{selectedPlayerName} ({selectedScope})</CardTitle>
                </CardHeader>
                <CardContent class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Games played</div>
                        <div class="text-2xl font-semibold">{data.stats.games_played}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Wins</div>
                        <div class="text-2xl font-semibold">{data.stats.wins}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Win rate</div>
                        <div class="text-2xl font-semibold">{percent(data.stats.win_rate)}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Avg team score</div>
                        <div class="text-2xl font-semibold">{data.stats.average_team_score.toFixed(2)}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Avg opponent score</div>
                        <div class="text-2xl font-semibold">{data.stats.average_opponent_score.toFixed(2)}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Current streak</div>
                        <div class="text-2xl font-semibold">{data.stats.current_win_streak}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Longest streak</div>
                        <div class="text-2xl font-semibold">{data.stats.longest_win_streak}</div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Best teammate</div>
                        <div class="text-base font-medium">
                            {data.stats.best_teammate
                                ? `${data.stats.best_teammate.player_name} (${percent(data.stats.best_teammate.win_rate)})`
                                : '—'}
                        </div>
                    </div>
                    <div class="rounded-md border p-3">
                        <div class="text-muted-foreground">Worst teammate</div>
                        <div class="text-base font-medium">
                            {data.stats.worst_teammate
                                ? `${data.stats.worst_teammate.player_name} (${percent(data.stats.worst_teammate.win_rate)})`
                                : '—'}
                        </div>
                    </div>
                </CardContent>
            </Card>
        {/if}
    {/if}
</section>

