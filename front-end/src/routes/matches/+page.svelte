<script lang="ts">
    import type {PageData} from './$types';

    export let data: PageData;

    // shadcn-svelte components
    import * as Card from "$lib/components/ui/card/index.js";
    import {Button} from "$lib/components/ui/button/index.js";
    import * as Pagination from "$lib/components/ui/pagination/index.js";
    import {RangeCalendar} from "$lib/components/ui/range-calendar/index.js";
    import {Badge} from "$lib/components/ui/badge/index.js";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import {goto} from "$app/navigation";
    import {today, getLocalTimeZone, CalendarDate, type DateValue} from "@internationalized/date";
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

    function teamPanelClass(won: boolean) {
        return won
            ? 'border-emerald-500/30 bg-emerald-500/10'
            : 'border-border/60 bg-background/60';
    }

    function playerChipClass(won: boolean) {
        return won
            ? 'bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-400/25'
            : 'bg-muted/70 text-foreground/85 ring-1 ring-border/60';
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
        if (!r?.start || !r?.end) return "Choisir une plage de dates";
        return `${r.start.toString()} — ${r.end.toString()}`;
    }

</script>

<!-- Filters -->
<div class="mb-6 mt-3 rounded-2xl border border-border/60 bg-background/60 p-3">
    <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Filtres matchs</p>
        <div class="flex flex-wrap items-center gap-2">
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
            <Button onclick={() => setMonth(0)} variant="secondary">Ce mois-ci</Button>
            <Button onclick={() => setMonth(-1)} variant="ghost">Mois precedent</Button>
            <Button onclick={clearDates} variant="destructive">Effacer</Button>
        </div>
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
                    class="group relative overflow-hidden rounded-3xl border border-emerald-500/15 bg-gradient-to-br from-emerald-950/10 via-background to-background/90 shadow-[0_10px_32px_rgba(0,0,0,0.2)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_36px_rgba(16,185,129,0.16)]">
                <div
                        class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.15),transparent_45%)]"></div>

                <Card.Header class="relative flex flex-row items-center justify-between gap-3 pb-1">
                    <Badge variant="secondary" class="text-xs">{toLocal(game.game_timestamp)}</Badge>
                    <span class="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Match n°{game.id}</span>
                </Card.Header>

                <Card.Content class="relative pt-3">
                    <div class="grid grid-cols-1 items-stretch gap-3 md:grid-cols-[1fr_auto_1fr] md:items-center">
                        <div class="rounded-2xl border px-3 py-3 {teamPanelClass(t1Wins)}">
                            <div class="mb-2 flex items-center justify-between">
                                <span class="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Equipe 1</span>
                                {#if t1Wins}
                                    <span class="text-[10px] font-semibold uppercase tracking-[0.12em] text-emerald-300">Vainqueur</span>
                                {/if}
                            </div>
                            <div class="flex flex-wrap gap-2 md:justify-end">
                                {#each t1 as m}
                                    {@const mmrChange = getOverallChange(game, m.player_id)}
                                    <div class="inline-flex min-w-[92px] flex-col items-end gap-1">
                                        <a
                                                href={statsHref(m.player_id)}
                                                class="inline-flex max-w-full rounded-full px-3 py-1 text-sm font-medium transition hover:brightness-110 {playerChipClass(t1Wins)}"
                                        >
                                            <span class="truncate">{m.player.player_name ?? `P${m.player.id}`}</span>
                                        </a>
                                        {#if mmrChange}
                                            <div class="text-[10px] leading-none inline-flex items-center gap-1.5">
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

                        <div class="rounded-2xl border border-border/60 bg-background/80 px-5 py-4 text-center shadow-inner">
                            <div class="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Score final</div>
                            <div class="mt-1 flex items-baseline justify-center gap-2">
                                <span class="text-4xl font-black leading-none {t1Wins ? 'text-emerald-400' : 'text-foreground/90'}">{s1}</span>
                                <span class="text-muted-foreground">–</span>
                                <span class="text-4xl font-black leading-none {t2Wins ? 'text-emerald-400' : 'text-foreground/90'}">{s2}</span>
                            </div>
                        </div>

                        <div class="rounded-2xl border px-3 py-3 {teamPanelClass(t2Wins)}">
                            <div class="mb-2 flex items-center justify-between">
                                <span class="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Equipe 2</span>
                                {#if t2Wins}
                                    <span class="text-[10px] font-semibold uppercase tracking-[0.12em] text-emerald-300">Vainqueur</span>
                                {/if}
                            </div>
                            <div class="flex flex-wrap gap-2">
                                {#each t2 as m}
                                    {@const mmrChange = getOverallChange(game, m.player_id)}
                                    <div class="inline-flex min-w-[92px] flex-col items-start gap-1">
                                        <a
                                                href={statsHref(m.player_id)}
                                                class="inline-flex max-w-full rounded-full px-3 py-1 text-sm font-medium transition hover:brightness-110 {playerChipClass(t2Wins)}"
                                        >
                                            <span class="truncate">{m.player.player_name ?? `P${m.player.id}`}</span>
                                        </a>
                                        {#if mmrChange}
                                            <div class="text-[10px] leading-none inline-flex items-center gap-1.5">
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
                            aria-label="Page precedente"
                            class="px-3 py-2 rounded-md hover:bg-muted"
                            aria-disabled={data.page === 1}
                    >
                        Precedent
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
                            aria-label="Page suivante"
                            class="px-3 py-2 rounded-md hover:bg-muted"
                            aria-disabled={data.page === data.pageCount}
                    >
                        Suivant
                    </a>
                </Pagination.Item>
            </Pagination.Content>
        </Pagination.Root>
    </div>
{/if}
<div class="h-6"></div>
