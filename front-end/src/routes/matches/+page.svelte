<script lang="ts">
    import type {PageData} from './$types';

    export let data: PageData;

    // shadcn-svelte components
    import * as Card from "$lib/components/ui/card/index.js";
    import {Button} from "$lib/components/ui/button/index.js";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Pagination from "$lib/components/ui/pagination/index.js";
    import {RangeCalendar} from "$lib/components/ui/range-calendar/index.js";
    import {Badge} from "$lib/components/ui/badge/index.js";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import {goto} from "$app/navigation";
    import {parseDate, today, getLocalTimeZone, CalendarDate, type DateValue} from "@internationalized/date";
    import {page} from '$app/state';


    function pushRangeToUrl(r?: { start?: DateValue; end?: DateValue }) {
        if (!r?.start || !r?.end) return;
        const start = r.start.toString();
        const end = r.end.toString();

        // Only navigate if something actually changed (prevents loops)
        const sp = new URLSearchParams(page.url.searchParams);
        if (sp.get("start_date") === start && sp.get("end_date") === end) return;

        sp.set("start_date", start);
        sp.set("end_date", end);
        sp.set("page", "1");
        goto(`?${sp.toString()}`, {replaceState: true});
    }

    // local helpers
    function toLocal(dt: string) {
        const d = new Date(dt);
        return d.toLocaleString(undefined, {
            year: 'numeric', month: 'short', day: '2-digit',
            hour: '2-digit', minute: '2-digit'
        });
    }

    // build/merge query params for navigation without losing others
    function buildQuery(updates: Record<string, string | number | undefined | null>) {
        const u = new URLSearchParams(page.url.searchParams);
        for (const [k, v] of Object.entries(updates)) {
            if (v === undefined || v === null || v === '') u.delete(k);
            else u.set(k, String(v));
        }
        return u.toString();
    }

    function getOverallChange(game: any, playerId: number): { delta: number; muAfter: number } | null {
        const change = game.rating_changes?.find(
            (item: any) => item.player_id === playerId && item.rating_type === 'overall'
        );
        if (typeof change?.delta_mu !== 'number' || typeof change?.mu_after !== 'number') {
            return null;
        }
        return {
            delta: change.delta_mu,
            muAfter: change.mu_after
        };
    }

    function formatDelta(delta: number) {
        const sign = delta > 0 ? '+' : '';
        return `${sign}${delta.toFixed(1)}`;
    }

    function formatElo(mu: number) {
        return `Elo ${mu.toFixed(1)}`;
    }

    function statsHref(playerId: number) {
        return `/stats?player_id=${playerId}&scope=overall`;
    }

    function deltaClass(delta: number) {
        if (delta > 0) return 'text-emerald-400';
        if (delta < 0) return 'text-rose-400';
        return 'text-muted-foreground';
    }

    let range: any | undefined;

    // Initialize from URL on first run (so the picker reflects current filters)
    $: if (range?.start && range?.end) {
        pushRangeToUrl(range);
    }

    async function clearDates() {
        console.log("clearDates");
        const sp = new URLSearchParams(page.url.searchParams);
        sp.delete("start_date");
        sp.delete("end_date");
        sp.set("page", "1");

        goto(`?${sp.toString()}`, {replaceState: true});
    }

    function setMonth(offset = 0) {
        const tz = getLocalTimeZone();
        const t = today(tz); // CalendarDate for "today" in local tz
        const start = new CalendarDate(t.year, t.month, 1).add({months: offset});
        const end = start.add({months: 1}).subtract({days: 1});
        // update both the bound calendar and the URL
        range = {start, end};
        pushRangeToUrl(range);
    }


    // simple label for the trigger button
    function labelFromRange(r?: any) {
        if (!r?.start || !r?.end) return "Pick a date range";
        return `${r.start.toString()} — ${r.end.toString()}`;
    }

</script>

<!-- Filters -->
<div class="space-y-4 mb-6 mt-3 ">
    <div class="flex items-center gap-2 justify-end mr-6 ">
        <Popover.Root>
            <Popover.Trigger>
                <Button class="w-[260px] justify-start font-normal" variant="outline">
                    {labelFromRange(range)}
                </Button>
            </Popover.Trigger>
            <Popover.Content class="p-0">
                <!-- bind:value fires as the user picks dates;
                     our reactive block above triggers navigation when both ends exist -->
                <RangeCalendar bind:value={range} class="rounded-md border"/>
            </Popover.Content>
        </Popover.Root>
        <Button onclick={() => setMonth(0)} variant="secondary">Ce mois</Button>
        <Button onclick={() => setMonth(-1)} variant="ghost">Mois Précédent</Button>
        <Button onclick={clearDates} variant="destructive">Effacer</Button>
    </div>
</div>

<!-- Matches list -->
<div class="grid gap-4 sm:grid-cols-2">
    {#if data.items.length === 0}
        <Card.Root>
            <Card.Content class="py-8 text-center text-muted-foreground">
                Pas de matchs trouvés avec les filtres actuels.
            </Card.Content>
        </Card.Root>
    {:else}
        {#each data.items as game (game.id)}
            {@const s1 = game.result_team1 ?? 0}
            {@const s2 = game.result_team2 ?? 0}
            {@const t1 = game.teams.filter((t) => t.team_number === 1)}
            {@const t2 = game.teams.filter((t) => t.team_number === 2)}
            {@const t1Wins = s1 > s2}
            {@const t2Wins = s2 > s1}

            <Card.Root
                    class="relative overflow-hidden rounded-2xl border border-border/60 bg-background transition hover:shadow-lg">
                <!-- date -->
                <Card.Header class="items-center pb-0">
                    <Badge variant="secondary" class="text-xs">{toLocal(game.game_timestamp)}</Badge>
                </Card.Header>

                <Card.Content class="pt-4">
                    <!-- players flanking the score -->
                    <div class="flex items-center justify-between gap-3">
                        <!-- LEFT team chips (tight to score) -->
                        <div class="flex flex-wrap gap-2 max-w-[45%] justify-end">
                            {#each t1 as m}
                                {@const mmrChange = getOverallChange(game, m.player_id)}
                                <div class="inline-flex flex-col items-end gap-1">
                                    <Badge class="rounded-full px-3 py-1
                            {t1Wins ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-400/25' : 'bg-muted text-foreground/80 ring-1 ring-border/50'}">
                                        <a href={statsHref(m.player_id)} class="hover:underline">
                                            {m.player.player_name ?? `P${m.player.id}`}
                                        </a>
                                    </Badge>
                                    {#if mmrChange}
                                        <div class="text-[10px] leading-none inline-flex items-center gap-1">
                                            <span class="text-muted-foreground">{formatElo(mmrChange.muAfter)}</span>
                                            <span class="font-semibold {deltaClass(mmrChange.delta)}">
                                                {formatDelta(mmrChange.delta)}
                                            </span>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>

                        <!-- SCORE -->
                        <div class="flex items-baseline gap-2 shrink-0">
        <span class="text-3xl font-extrabold leading-none
                     {t1Wins ? 'text-emerald-400' : 'text-foreground/90'}">{s1}</span>
                            <span class="text-muted-foreground">–</span>
                            <span class="text-3xl font-extrabold leading-none
                     {t2Wins ? 'text-emerald-400' : 'text-foreground/90'}">{s2}</span>
                        </div>

                        <!-- RIGHT team chips (tight to score) -->
                        <div class="flex flex-wrap gap-2 max-w-[45%]">
                            {#each t2 as m}
                                {@const mmrChange = getOverallChange(game, m.player_id)}
                                <div class="inline-flex flex-col items-start gap-1">
                                    <Badge class="rounded-full px-3 py-1
                            {t2Wins ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-400/25' : 'bg-muted text-foreground/80 ring-1 ring-border/50'}">
                                        <a href={statsHref(m.player_id)} class="hover:underline">
                                            {m.player.player_name ?? `P${m.player.id}`}
                                        </a>
                                    </Badge>
                                    {#if mmrChange}
                                        <div class="text-[10px] leading-none inline-flex items-center gap-1">

                                            <span class="text-muted-foreground">{formatElo(mmrChange.muAfter)}</span>
                                            <span class="font-semibold {deltaClass(mmrChange.delta)}">
                                                {formatDelta(mmrChange.delta)}
                                            </span>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </div>
                </Card.Content>
            </Card.Root>

        {/each}


    {/if}
</div>

<!-- Pagination -->
{#if data.pageCount > 1}
    <div class="mt-6">
        <Pagination.Root count={data.pageCount} page={data.page}>
            <Pagination.Content>
                <Pagination.Item>
                    <a
                            href={"?"+buildQuery({ page: Math.max(1, data.page - 1) })}
                            aria-label="Previous page"
                            class="px-3 py-2 rounded-md hover:bg-muted"
                            aria-disabled={data.page === 1}
                    >
                        Previous
                    </a>
                </Pagination.Item>

                {#each Array(data.pageCount) as _, i}
                    {#if Math.abs(i + 1 - data.page) <= 2 || i === 0 || i + 1 === data.pageCount}
                        <Pagination.Item>
                            <a
                                    href={"?"+buildQuery({ page: i + 1 })}
                                    class="px-3 py-2 rounded-md hover:bg-muted {i + 1 === data.page ? 'bg-primary text-primary-foreground' : ''}"
                                    aria-current={i + 1 === data.page ? 'page' : undefined}
                            >
                                {i + 1}
                            </a>
                        </Pagination.Item>
                    {:else if (i === 1 && data.page > 3) || (i === data.pageCount - 2 && data.page < data.pageCount - 2)}
                        <Pagination.Ellipsis/>
                    {/if}
                {/each}

                <Pagination.Item>
                    <a
                            href={"?"+buildQuery({ page: Math.min(data.pageCount, data.page + 1) })}
                            aria-label="Next page"
                            class="px-3 py-2 rounded-md hover:bg-muted"
                            aria-disabled={data.page === data.pageCount}
                    >
                        Next
                    </a>
                </Pagination.Item>
            </Pagination.Content>
        </Pagination.Root>
    </div>
{/if}
<div class="h-6"></div>
