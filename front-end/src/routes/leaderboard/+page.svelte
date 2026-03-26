<script lang="ts">
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Table from "$lib/components/ui/table/index.js";
    import {getStoredCurrentPlayerId, onCurrentPlayerChange} from "$lib/current-player";

    let {data} = $props<{
        data: {
            scope: "monthly" | "yearly" | "overall";
            year: number;
            month?: number;
            players: { id: number; name: string; wins: number; losses: number; elo: number }[];
        };
    }>();

    data.year ||= new Date().getFullYear();

    const scopeOptions = [
        {value: "monthly", label: "Mensuel"},
        {value: "yearly", label: "Annuel"},
        {value: "overall", label: "Global"}
    ];

    const monthNames = [
        "Janv", "Fev", "Mars", "Avr", "Mai", "Juin",
        "Juil", "Aout", "Sept", "Oct", "Nov", "Dec"
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
        scopeOptions.find((o) => o.value === scopeSel)?.label ?? "Periode"
    );
    const yearLabel = $derived(
        years.find((y) => y.value === yearSel)?.label ?? "Annee"
    );
    const monthLabel = $derived(
        months.find((m) => m.value === monthSel)?.label ?? "Mois"
    );
    const triggerClass =
        "inline-flex items-center justify-between rounded-xl bg-card/90 px-3 py-2 text-sm text-foreground shadow-sm transition hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary/40";
    const contentClass =
        "z-50 min-w-[--bits-select-trigger-width] rounded-xl bg-popover p-1 shadow-xl";
    const itemClass =
        "cursor-pointer select-none rounded-lg px-3 py-2 text-sm text-foreground hover:bg-secondary data-[state=checked]:bg-primary/15 data-[state=checked]:text-primary";
    const rankedPlayers = $derived(
        data.players.map((player: { id: number; name: string; wins: number; losses: number; elo: number }, idx: number) => ({...player, rank: idx + 1}))
    );
    let currentPlayerId = $state<number | null>(null);

    function isCurrentPlayer(player: { id: number }) {
        return currentPlayerId !== null && player.id === currentPlayerId;
    }

    onMount(() => {
        currentPlayerId = getStoredCurrentPlayerId();
        return onCurrentPlayerChange((playerId) => {
            currentPlayerId = playerId;
        });
    });

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

<section class="mx-auto max-w-[1400px] space-y-6 px-4 py-6">
    <div class="grid gap-4 lg:grid-cols-[1.3fr_1fr] lg:items-end">
        <div class="space-y-3">
            <p class="editorial-kicker">Global Leaderboard</p>
            <h2 class="font-display text-5xl font-black uppercase leading-[0.92] text-foreground">The Pitch Elite.</h2>
            <p class="max-w-lg text-sm text-muted-foreground">
                Every flick, block, and goal is recorded. Classement live de la ligue interne.
            </p>
        </div>
        <div class="grid grid-cols-3 gap-2">
            {#each rankedPlayers.slice(0, 3) as row}
                <div class={`rounded-2xl bg-card px-3 py-3 text-center shadow-[0_20px_40px_rgba(12,15,16,0.06)] ${isCurrentPlayer(row) ? 'ring-2 ring-primary/40' : ''}`}>
                    <p class="text-[10px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">#{String(row.rank).padStart(2, '0')}</p>
                    <p class="mt-1 truncate text-sm font-semibold">{row.name}</p>
                    {#if isCurrentPlayer(row)}
                        <p class="mt-1 text-[10px] font-semibold uppercase tracking-[0.13em] tone-positive">Vous</p>
                    {/if}
                    <p class="mt-2 font-display text-2xl font-bold text-primary">{row.elo}</p>
                </div>
            {/each}
        </div>
    </div>

    <div class="surface-low flex flex-wrap gap-3 rounded-2xl p-3">
        {#if scopeSel === "monthly"}
            <Select.Root type="single" bind:value={monthSel}>
                <Select.Trigger
                        class={`w-[140px] ${triggerClass}`}
                >
                    {monthLabel}
                </Select.Trigger>
                <Select.Content
                        class={contentClass}
                >
                    {#each months as m}
                        <Select.Item
                                value={m.value}
                                label={m.label}
                                showIndicator={false}
                                class={itemClass}
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
                        class={`w-[120px] ${triggerClass}`}
                >
                    {yearLabel}
                </Select.Trigger>
                <Select.Content
                        class={contentClass}
                >
                    {#each years as y}
                        <Select.Item
                                value={y.value}
                                label={y.label}
                                showIndicator={false}
                                class={itemClass}
                        >
                            {y.label}
                        </Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        {/if}

        <Select.Root bind:value={scopeSel} type="single">
            <Select.Trigger
                    class={`w-[180px] ${triggerClass}`}
            >
                {scopeLabel}
            </Select.Trigger>
            <Select.Content
                    class={contentClass}
            >
                {#each scopeOptions as s}
                    <Select.Item
                            value={s.value}
                            label={s.label}
                            showIndicator={false}
                            class={itemClass}
                    >
                        {s.label}
                    </Select.Item>
                {/each}
            </Select.Content>
        </Select.Root>
    </div>

    <div class="surface-low rounded-3xl p-2">
        <Table.Root class="border-separate [border-spacing:0_10px]">
            <Table.Header class="[&_tr]:border-0">
                <Table.Row class="border-0">
                    <Table.Head class="h-8 px-5 text-[11px] uppercase tracking-[0.16em]">Joueur</Table.Head>
                    <Table.Head class="h-8 text-[11px] uppercase tracking-[0.16em]">Joués</Table.Head>
                    <Table.Head class="h-8 text-[11px] uppercase tracking-[0.16em]">V</Table.Head>
                    <Table.Head class="h-8 text-[11px] uppercase tracking-[0.16em]">D</Table.Head>
                    <Table.Head class="h-8 text-[11px] uppercase tracking-[0.16em]">Win %</Table.Head>
                    <Table.Head class="h-8 text-right text-[11px] uppercase tracking-[0.16em]">Elo</Table.Head>
                </Table.Row>
            </Table.Header>
            <Table.Body class="[&_tr:last-child]:border-0">
                {#each rankedPlayers as player (player.rank)}
                    <Table.Row class={`border-0 bg-card hover:bg-card ${player.rank === 1 ? 'ring-1 ring-primary/35 shadow-[0_0_0_1px_hsl(var(--primary)/0.08)_inset]' : ''} ${isCurrentPlayer(player) ? 'ring-2 ring-primary/40 bg-primary/5' : ''}`}>
                        <Table.Cell class="rounded-l-xl px-5 font-medium">
                            <div class="flex items-center gap-3">
                                <span class={`inline-flex min-w-[48px] justify-center rounded-lg px-2 py-1 font-display text-sm font-bold ${
                                    player.rank === 1
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-secondary text-secondary-foreground'
                                }`}>
                                    #{String(player.rank).padStart(2, '0')}
                                </span>
                                <div class="flex items-center gap-2">
                                    <span>{player.name}</span>
                                    {#if isCurrentPlayer(player)}
                                        <span class="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] tone-positive">Vous</span>
                                    {/if}
                                </div>
                            </div>
                        </Table.Cell>
                        <Table.Cell>{player.wins + player.losses}</Table.Cell>
                        <Table.Cell>{player.wins}</Table.Cell>
                        <Table.Cell>{player.losses}</Table.Cell>
                        <Table.Cell>
                            {player.wins + player.losses > 0
                                ? ((player.wins / (player.wins + player.losses)) * 100).toFixed() + '%'
                                : '-'}
                        </Table.Cell>
                        <Table.Cell class={`rounded-r-xl text-right font-display text-2xl font-bold ${player.rank === 1 ? 'tone-positive' : ''}`}>{player.elo}</Table.Cell>
                    </Table.Row>
                {/each}
            </Table.Body>
        </Table.Root>
    </div>
</section>
