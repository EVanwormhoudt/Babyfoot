<script lang="ts">
    // --- Types ---
    import type {PageData} from "./$types";
    // --- shadcn-svelte date range picker imports ---
    import type {DateRange} from "bits-ui";
    import {CalendarDate, DateFormatter, type DateValue, getLocalTimeZone} from "@internationalized/date";
    import {cn} from "$lib/utils";
    import {buttonVariants} from "$lib/components/ui/button";
    import {RangeCalendar} from "$lib/components/ui/range-calendar";
    import * as Popover from "$lib/components/ui/popover";
    import CalendarIcon from "@lucide/svelte/icons/calendar";

    // --- Types ---
    const {data} = $props<{
        data: PageData & {
            items: any[];
            page: number;
            hasNext: boolean;
            fromParam?: string | null; // YYYY-MM-DD
            toParam?: string | null; // YYYY-MM-DD
        };
    }>();
    console.log("Matches page data:", data.matches);

    // --- Helpers to map your provided data shape ---
    const getDate = (g: any) => g.game_timestamp as string | undefined;
    const getScore = (g: any) =>
        g.result_team1 != null && g.result_team2 != null
            ? `${g.result_team1}–${g.result_team2}`
            : "—";
    const teamNames = (g: any, teamNo: number) =>
        (g.teams || [])
            .filter((t: any) => t.team_number === teamNo)
            .map((t: any) => t.player?.player_name ?? "?")
            .join(" & ") || (teamNo === 1 ? "Team 1" : "Team 2");
    const getHome = (g: any) => teamNames(g, 1);
    const getAway = (g: any) => teamNames(g, 2);

    const fmtDate = (iso?: string) => {
        if (!iso) return "";
        const d = new Date(iso);
        return d.toLocaleDateString(undefined, {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric"
        });
    };
    const fmtTime = (iso?: string) => {
        if (!iso) return "";
        const d = new Date(iso);
        return d.toLocaleTimeString(undefined, {hour: "2-digit", minute: "2-digit"});
    };

    // --- URL param utilities ---
    function setParams(params: Record<string, string | null>) {
        const u = new URL(window.location.href);
        for (const [k, v] of Object.entries(params)) {
            if (v == null || v === "") u.searchParams.delete(k);
            else u.searchParams.set(k, v);
        }
        // Reset page when filters change
        if (Object.keys(params).some((k) => k !== "page")) u.searchParams.set("page", "1");
        window.location.search = u.searchParams.toString();
    }

    function goPage(p: number) {
        const u = new URL(window.location.href);
        u.searchParams.set("page", String(Math.max(1, p)));
        window.location.search = u.searchParams.toString();
    }

    // --- Date range picker state ---
    const df = new DateFormatter("en-US", {dateStyle: "medium"});
    let value: DateRange = $state({
        start: data.fromParam
            ? CalendarDate.fromDate(new Date(data.fromParam + "T00:00:00"))
            : undefined,
        end: data.toParam
            ? CalendarDate.fromDate(new Date(data.toParam + "T00:00:00"))
            : undefined
    });
    let startValue: DateValue | undefined = $state(undefined);

    function applyRangeToQuery(v: DateRange) {
        const from = v?.start?.toDate(getLocalTimeZone());
        const to = v?.end?.toDate(getLocalTimeZone());
        const yyyy_mm_dd = (d: Date) => d.toISOString().slice(0, 10);
        setParams({
            from: from ? yyyy_mm_dd(from) : null,
            to: to ? yyyy_mm_dd(to) : null
        });
    }
</script>

<!-- Root with DARK background -->
<div class="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-black text-slate-100">
    <div class="mx-auto max-w-6xl px-4 py-8">
        <header class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
                <h1 class="text-3xl font-bold tracking-tight">Last Matches</h1>
                <p class="text-slate-400">Filter by date range. Pagination uses limit/offset.</p>
            </div>

            <!-- shadcn date range picker -->
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
                <div class="grid gap-2">
                    <Popover.Root>
                        <Popover.Trigger
                                class={cn(
                buttonVariants({ variant: "outline" }),
                "bg-slate-900/40 border-slate-700 text-slate-200 hover:bg-slate-800/60",
                !(value && (value.start || value.end)) && "text-muted-foreground"
              )}
                        >
                            <CalendarIcon class="mr-2 size-4"/>
                            {#if value && value.start}
                                {#if value.end}
                                    {df.format(value.start.toDate(getLocalTimeZone()))} -
                                    {df.format(value.end.toDate(getLocalTimeZone()))}
                                {:else}
                                    {df.format(value.start.toDate(getLocalTimeZone()))}
                                {/if}
                            {:else if startValue}
                                {df.format(startValue.toDate(getLocalTimeZone()))}
                            {:else}
                                Pick a date range
                            {/if}
                        </Popover.Trigger>
                        <Popover.Content align="start" class="w-auto p-0">
                            <div class="rounded-xl border border-slate-700 bg-slate-900 p-2 shadow-xl">
                                <RangeCalendar
                                        bind:value
                                        numberOfMonths={2}
                                        onStartValueChange={(v) => (startValue = v)}
                                        onValueChange={applyRangeToQuery}
                                />
                                <div class="mt-2 flex justify-end gap-2 px-2 pb-2">
                                    <button
                                            class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-sm hover:bg-slate-700"
                                            onclick={() => {
                      value = { start: undefined, end: undefined } ;
                      startValue = undefined;
                      applyRangeToQuery(value);
                    }}
                                    >
                                        Clear
                                    </button>
                                </div>
                            </div>
                        </Popover.Content>
                    </Popover.Root>
                </div>
            </div>
        </header>

        <div class="mb-4 flex items-center justify-between">
            <p class="text-sm text-slate-400">
                {#if data.fromParam || data.toParam}
                    for
                    <span class="font-medium text-slate-200">
            {#if data.fromParam}{new Date(data.fromParam).toLocaleDateString()}{/if}
                        {#if data.fromParam && data.toParam} – {/if}
                        {#if data.toParam}{new Date(data.toParam).toLocaleDateString()}{/if}
          </span>
                {/if}
            </p>

            <nav aria-label="Pagination" class="hidden items-center gap-2 sm:flex">
                <button class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={data.page === 1} onclick={() => goPage(1)}>
                    « First
                </button>
                <button class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={data.page === 1} onclick={() => goPage(data.page - 1)}>
                    ‹ Prev
                </button>
                <span class="text-sm text-slate-400">Page {data.page}</span>
                <button class="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={!data.hasNext} onclick={() => goPage(data.page + 1)}>
                    Next ›
                </button>
            </nav>
        </div>

        {#if data.items.length === 0}
            <div class="rounded-2xl border border-dashed border-slate-700 p-8 text-center text-slate-400">
                No matches found for this selection.
            </div>

        {:else}
            <ul class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {#each data.items as g}
                    <li class="group">
                        <article
                                class="h-full rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-sm transition hover:shadow-md hover:border-slate-700">
                            <header class="mb-3 flex items-center justify-between">
                                <div>
                                    <div class="text-xs uppercase tracking-wide text-slate-400">—</div>
                                    <h3 class="text-base font-semibold text-slate-100">{getHome(g)} vs {getAway(g)}</h3>
                                </div>
                                <div class="text-right">
                                    <div class="text-lg font-bold text-slate-50">{getScore(g)}</div>
                                    {#if getDate(g)}
                                        <div class="text-xs text-slate-400">{fmtTime(getDate(g))}</div>
                                    {/if}
                                </div>
                            </header>

                            {#if getDate(g)}
                                <footer class="flex items-center justify-between text-sm text-slate-300">
                                    <div class="flex items-center gap-2">
                    <span class="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-slate-700 text-slate-100">
                      {new Date(getDate(g)).toLocaleDateString(undefined, {day: "2-digit"})}
                    </span>
                                        <div>
                                            <div class="font-medium">{new Date(getDate(g)).toLocaleDateString(undefined, {month: "long"})}</div>
                                            <div class="text-xs text-slate-400">{new Date(getDate(g)).toLocaleDateString(undefined, {year: "numeric"})}</div>
                                        </div>
                                    </div>
                                    <span class="rounded-full bg-slate-800 px-2 py-1 text-xs text-slate-300 border border-slate-700">{fmtDate(getDate(g))}</span>
                                </footer>
                            {/if}

                            <div class="mt-3 flex items-center gap-3 text-xs text-slate-400">
                                <!-- quick chips of players with their colors -->
                                <ul class="flex flex-wrap gap-1.5">
                                    {#each (g.teams || []) as t}
                                        <li class="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5">
                                            <span class="inline-block h-2 w-2 rounded-full"
                                                  style={`background:${t.player?.player_color || "#9ca3af"}`}></span>
                                            <span>{t.player?.player_name}</span>
                                            <span class="opacity-60">(T{t.team_number})</span>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        </article>
                    </li>
                {/each}
            </ul>
        {/if}

        <div class="mt-8 flex flex-col items-center justify-between gap-3 sm:flex-row">
            <nav aria-label="Pagination" class="flex items-center gap-2">
                <button class="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={data.page === 1} onclick={() => goPage(1)}>« First
                </button>
                <button class="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={data.page === 1} onclick={() => goPage(data.page - 1)}>‹ Prev
                </button>
                <span class="text-sm text-slate-400">Page <span
                        class="font-medium text-slate-200">{data.page}</span></span>
                <button class="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-sm disabled:opacity-40 hover:bg-slate-700"
                        disabled={!data.hasNext} onclick={() => goPage(data.page + 1)}>Next ›
                </button>
            </nav>
            <div class="text-sm text-slate-400">
                {#if data.hasNext}More results available…{/if}
            </div>
        </div>
    </div>
</div>

<style>
    /* Optional: improve focus ring contrast on dark */
    :global(:focus-visible) {
        outline: 2px solid rgb(148 163 184);
        outline-offset: 2px;
    }
</style>
