<script lang="ts">
    import {goto} from "$app/navigation";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Table from "$lib/components/ui/table/index.js";

    let {data} = $props<{
        data: {
            scope: "monthly" | "yearly" | "overall";
            year: number;
            month?: number;
            players: { name: string; wins: number; losses: number; elo: number }[];
        };
    }>();

    data.year ||= new Date().getFullYear();

    const scopeOptions = [
        {value: "monthly", label: "Monthly"},
        {value: "yearly", label: "Yearly"},
        {value: "overall", label: "Overall"}
    ];

    const monthNames = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];
    const months = monthNames.map((label, i) => ({
        value: String(i + 1),
        label
    }));

    const now = new Date();
    const currentYear = now.getFullYear();
    const base = Math.max(currentYear, data.year ?? currentYear);
    const years = Array.from(
        {length: Math.max(0, base - 2018 + 1)},
        (_, i) => {
            const y = base - i;
            return {value: String(y), label: String(y)};
        }
    );

    // --- BINDINGS ---
    let scopeSel = $state(data.scope);
    let yearSel = $state(String(data.year));
    let monthSel = $state(String(data.month ?? now.getMonth() + 1));

    // --- LABELS FOR TRIGGERS ---
    const scopeLabel = $derived(
        scopeOptions.find((o) => o.value === scopeSel)?.label ?? "Scope"
    );
    const yearLabel = $derived(
        years.find((y) => y.value === yearSel)?.label ?? "Year"
    );
    const monthLabel = $derived(
        months.find((m) => m.value === monthSel)?.label ?? "Month"
    );

    // --- URL SYNC EFFECT ---
    $effect(() => {
        if (typeof window === "undefined") return;
        const url = new URL(window.location.href);
        let changed = false;

        if (url.searchParams.get("scope") !== scopeSel) {
            url.searchParams.set("scope", scopeSel);
            changed = true;
        }

        if (scopeSel === "overall") {
            if (url.searchParams.has("year")) {
                url.searchParams.delete("year");
                changed = true;
            }
            if (url.searchParams.has("month")) {
                url.searchParams.delete("month");
                changed = true;
            }
        } else {
            if (url.searchParams.get("year") !== yearSel) {
                url.searchParams.set("year", yearSel);
                changed = true;
            }
            if (scopeSel === "monthly") {
                if (url.searchParams.get("month") !== monthSel) {
                    url.searchParams.set("month", monthSel);
                    changed = true;
                }
            } else if (url.searchParams.has("month")) {
                url.searchParams.delete("month");
                changed = true;
            }
        }

        if (changed) {
            goto(`${url.pathname}?${url.searchParams.toString()}`, {
                replaceState: true,
                noScroll: true
            });
        }
    });
</script>

<section class="p-8">
    <h2 class="text-3xl font-semibold mb-6">Leaderboard</h2>

    <div class="flex flex-wrap gap-3 justify-end mb-4 datepicker">
        {#if scopeSel === "monthly"}
            <Select.Root type="single" bind:value={monthSel}>
                <Select.Trigger
                        class="w-[140px] inline-flex items-center justify-between rounded-xl border border-neutral-700
                 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 shadow-sm hover:bg-neutral-800
                 focus:outline-none focus:ring-2 focus:ring-primary/50 transition"
                >
                    {monthLabel}
                </Select.Trigger>
                <Select.Content
                        class="z-50 min-w-[--bits-select-trigger-width] rounded-xl border border-neutral-700 bg-neutral-900 p-1 shadow-xl"
                >
                    {#each months as m}
                        <Select.Item
                                value={m.value}
                                label={m.label}
                                class="cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-neutral-100
                     hover:bg-neutral-800 data-[state=checked]:bg-primary/15 data-[state=checked]:text-primary"
                        >
                            {m.label}
                        </Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        {/if}

        {#if scopeSel !== "overall"}
            <Select.Root type="single" bind:value={yearSel}>
                <Select.Trigger
                        class="w-[120px] inline-flex items-center justify-between rounded-xl border border-neutral-700
                 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 shadow-sm hover:bg-neutral-800
                 focus:outline-none focus:ring-2 focus:ring-primary/50 transition"
                >
                    {yearLabel}
                </Select.Trigger>
                <Select.Content
                        class="z-50 min-w-[--bits-select-trigger-width] rounded-xl border border-neutral-700 bg-neutral-900 p-1 shadow-xl"
                >
                    {#each years as y}
                        <Select.Item
                                value={y.value}
                                label={y.label}
                                class="cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-neutral-100
                     hover:bg-neutral-800 data-[state=checked]:bg-primary/15 data-[state=checked]:text-primary"
                        >
                            {y.label}
                        </Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        {/if}

        <Select.Root bind:value={scopeSel} type="single">
            <Select.Trigger
                    class="w-[180px] inline-flex items-center justify-between rounded-xl border border-neutral-700
               bg-neutral-900 px-3 py-2 text-sm text-neutral-100 shadow-sm hover:bg-neutral-800
               focus:outline-none focus:ring-2 focus:ring-primary/50 transition"
            >
                {scopeLabel}
            </Select.Trigger>
            <Select.Content
                    class="z-50 min-w-[--bits-select-trigger-width] rounded-xl border border-neutral-700 bg-neutral-900 p-1 shadow-xl"
            >
                {#each scopeOptions as s}
                    <Select.Item
                            value={s.value}
                            label={s.label}
                            class="cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-neutral-100
                   hover:bg-neutral-800 data-[state=checked]:bg-primary/15 data-[state=checked]:text-primary"
                    >
                        {s.label}
                    </Select.Item>
                {/each}
            </Select.Content>
        </Select.Root>
    </div>

    <Table.Root>
        <Table.Header>
            <Table.Row>
                <Table.Head>Name</Table.Head>
                <Table.Head>Wins</Table.Head>
                <Table.Head>Losses</Table.Head>
                <Table.Head>Winrate</Table.Head>
                <Table.Head class="text-right">Elo</Table.Head>
            </Table.Row>
        </Table.Header>
        <Table.Body>
            {#each data.players as player, i (i)}
                <Table.Row>
                    <Table.Cell class="font-medium">{player.name}</Table.Cell>
                    <Table.Cell>{player.wins}</Table.Cell>
                    <Table.Cell>{player.losses}</Table.Cell>
                    <Table.Cell>
                        {player.wins + player.losses > 0
                            ? ((player.wins / (player.wins + player.losses)) * 100).toFixed() + '%'
                            : '-'}
                    </Table.Cell>
                    <Table.Cell class="text-right">{player.elo}</Table.Cell>
                </Table.Row>
            {/each}
        </Table.Body>
    </Table.Root>
</section>

<style>
    .datepicker {
        margin-right: 3%;
    }
</style>
