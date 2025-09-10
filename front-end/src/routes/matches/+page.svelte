<script lang="ts">
    import type {DateRange} from "bits-ui";
    import {CalendarDate, DateFormatter, type DateValue, getLocalTimeZone, fromDate} from "@internationalized/date";
    import {RangeCalendar} from "$lib/components/ui/range-calendar";
    import * as Popover from "$lib/components/ui/popover";
    import CalendarIcon from "@lucide/svelte/icons/calendar";

    const {data} = $props<{
        data: {
            items: any[];
            page: number;
            hasNext: boolean;
            fromParam?: string | null;
            toParam?: string | null;
        };
    }>();

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

    function setParams(params: Record<string, string | null>) {
        const u = new URL(window.location.href);
        for (const [k, v] of Object.entries(params)) {
            if (v == null || v === "") u.searchParams.delete(k);
            else u.searchParams.set(k, v);
        }
        if (Object.keys(params).some((k) => k !== "page")) u.searchParams.set("page", "1");
        window.location.search = u.searchParams.toString();
    }

    function goPage(p: number) {
        const u = new URL(window.location.href);
        u.searchParams.set("page", String(Math.max(1, p)));
        window.location.search = u.searchParams.toString();
    }

    const df = new DateFormatter("en-US", {dateStyle: "medium"});
    let value: DateRange = $state({
        start: data.fromParam
            ? fromDate(new Date(data.fromParam + "T00:00:00"), getLocalTimeZone())
            : undefined,
        end: data.toParam
            ? fromDate(new Date(data.toParam + "T00:00:00"), getLocalTimeZone())
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

<div>
    <div>
        <header>
            <div>
                <h1>Last Matches</h1>
                <p>Filter by date range. Pagination uses limit/offset.</p>
            </div>

            <div>
                <div>
                    <Popover.Root>
                        <Popover.Trigger>
                            <CalendarIcon/>
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
                        <Popover.Content align="start">
                            <div>
                                <RangeCalendar
                                        bind:value
                                        numberOfMonths={2}
                                        onStartValueChange={(v) => (startValue = v)}
                                        onValueChange={applyRangeToQuery}
                                />
                                <div>
                                    <button
                                            onclick={() => {
                                            value = { start: undefined, end: undefined };
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

        <div>
            <p>
                {#if data.fromParam || data.toParam}
                    for
                    <span>
                        {#if data.fromParam}{new Date(data.fromParam).toLocaleDateString()}{/if}
                        {#if data.fromParam && data.toParam} – {/if}
                        {#if data.toParam}{new Date(data.toParam).toLocaleDateString()}{/if}
                    </span>
                {/if}
            </p>

            <nav aria-label="Pagination">
                <button disabled={data.page === 1} onclick={() => goPage(1)}>« First</button>
                <button disabled={data.page === 1} onclick={() => goPage(data.page - 1)}>‹ Prev</button>
                <span>Page {data.page}</span>
                <button disabled={!data.hasNext} onclick={() => goPage(data.page + 1)}>Next ›</button>
            </nav>
        </div>

        {#if data.matches.length === 0}
            <div>
                No matches found for this selection.
            </div>
        {:else}
            <ul>
                {#each data.items as g}
                    <li>
                        <article>
                            <header>
                                <div>
                                    <div>—</div>
                                    <h3>{getHome(g)} vs {getAway(g)}</h3>
                                </div>
                                <div>
                                    <div>{getScore(g)}</div>
                                    {#if getDate(g)}
                                        <div>{fmtTime(getDate(g))}</div>
                                    {/if}
                                </div>
                            </header>

                            {#if getDate(g)}
                                <footer>
                                    <div>
                                        <span>
                                            {new Date(getDate(g)).toLocaleDateString(undefined, {day: "2-digit"})}
                                        </span>
                                        <div>
                                            <div>{new Date(getDate(g)).toLocaleDateString(undefined, {month: "long"})}</div>
                                            <div>{new Date(getDate(g)).toLocaleDateString(undefined, {year: "numeric"})}</div>
                                        </div>
                                    </div>
                                    <span>{fmtDate(getDate(g))}</span>
                                </footer>
                            {/if}

                            <div>
                                <ul>
                                    {#each (g.teams || []) as t}
                                        <li>
                                            <span style={`background:${t.player?.player_color || "#9ca3af"}`}></span>
                                            <span>{t.player?.player_name}</span>
                                            <span>(T{t.team_number})</span>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        </article>
                    </li>
                {/each}
            </ul>
        {/if}

        <div>
            <nav aria-label="Pagination">
                <button disabled={data.page === 1} onclick={() => goPage(1)}>« First</button>
                <button disabled={data.page === 1} onclick={() => goPage(data.page - 1)}>‹ Prev</button>
                <span>Page {data.page}</span>
                <button disabled={!data.hasNext} onclick={() => goPage(data.page + 1)}>Next ›</button>
            </nav>
            <div>
                {#if data.hasNext}More results available…{/if}
            </div>
        </div>
    </div>
</div>
