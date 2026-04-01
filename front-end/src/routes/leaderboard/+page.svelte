<script lang="ts">
    import {goto} from "$app/navigation";
    import {onMount} from "svelte";
    import * as Select from "$lib/components/ui/select/index.js";
    import * as Table from "$lib/components/ui/table/index.js";
    import {getStoredCurrentPlayerId, onCurrentPlayerChange} from "$lib/current-player";

    type LeaderboardPlayer = { id: number; name: string; wins: number; losses: number; elo: number };
    type RankedPlayer = LeaderboardPlayer & { rank: number };

    let {data} = $props<{
        data: {
            scope: "monthly" | "yearly" | "overall";
            year: number;
            month?: number;
            players: LeaderboardPlayer[];
        };
    }>();

    data.year ||= new Date().getFullYear();

    const scopeOptions = [
        {value: "monthly", label: "Mensuel"},
        {value: "yearly", label: "Annuel"},
        {value: "overall", label: "General"}
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
    const rankedPlayers = $derived<RankedPlayer[]>(
        data.players.map((player: LeaderboardPlayer, idx: number) => ({...player, rank: idx + 1}))
    );
    const podiumOrder = [2, 1, 3] as const;
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
            <p class="editorial-kicker">Classement general</p>
            <h2 class="font-display text-5xl font-black uppercase leading-[0.92] text-foreground">L'elite du
                babyfoot.</h2>
            <p class="max-w-lg text-sm text-muted-foreground">
                Chaque frappe, bloc et but est enregistre. Classement en direct de la ligue interne.
            </p>
        </div>
        <div class="surface-low grid grid-cols-3 items-end gap-2 rounded-2xl p-2">
            {#each podiumOrder as podiumRank}
                {@const row = rankedPlayers.find((player) => player.rank === podiumRank)}
                <div class="flex flex-col">
                    <div class={`rounded-t-2xl border border-border/75 bg-card px-2 text-center shadow-[0_14px_24px_rgba(12,15,16,0.06)] dark:border-white/12 dark:bg-[linear-gradient(180deg,hsl(var(--card))_0%,hsl(var(--surface-container-low))_100%)] dark:shadow-[0_16px_26px_rgba(0,0,0,0.38)] ${podiumRank === 1 ? 'min-h-[116px] py-3 dark:bg-[linear-gradient(180deg,hsl(var(--card))_0%,hsl(var(--primary)/0.2)_100%)]' : 'min-h-[96px] py-2'} ${row && isCurrentPlayer(row) ? 'ring-2 ring-primary/40 dark:ring-primary/60' : ''}`}>
                        <p class="text-[10px] font-semibold uppercase tracking-[0.13em] text-muted-foreground">#{String(podiumRank).padStart(2, '0')}</p>
                        {#if row}
                            <p class="mt-1 truncate text-sm font-semibold">{row.name}</p>
                            {#if isCurrentPlayer(row)}
                                <p class="mt-1 text-[10px] font-semibold uppercase tracking-[0.13em] tone-positive">Vous</p>
                            {/if}
                            <p class="mt-2 font-display text-2xl font-bold text-primary">{row.elo}</p>
                        {:else}
                            <p class="mt-5 text-xs text-muted-foreground">Aucun joueur</p>
                        {/if}
                    </div>
                    <div class={`flex items-center justify-center rounded-b-2xl border border-t-0 border-border/75 text-sm font-semibold uppercase tracking-[0.15em] dark:border-white/12 ${podiumRank === 1 ? 'h-20 bg-primary/14 text-primary dark:border-[hsl(var(--primary-container)/0.58)] dark:bg-[linear-gradient(180deg,hsl(var(--primary-container)/0.98),hsl(var(--primary-container)/0.82))] dark:text-[hsl(var(--primary-container-foreground))]' : podiumRank === 2 ? 'h-14 bg-secondary/80 text-secondary-foreground dark:bg-[linear-gradient(180deg,hsl(var(--surface-container-high)),hsl(var(--surface-container-low)))] dark:text-foreground' : 'h-12 bg-secondary/65 text-secondary-foreground dark:bg-[linear-gradient(180deg,hsl(var(--surface-container-high)/0.9),hsl(var(--surface-container-low)/0.95))] dark:text-foreground/90'}`}>
                        {podiumRank === 1 ? '1er' : podiumRank === 2 ? '2e' : '3e'}
                    </div>
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
                    <Table.Head class="h-8 text-[11px] uppercase tracking-[0.16em]">Taux V</Table.Head>
                    <Table.Head class="h-8 text-right text-[11px] uppercase tracking-[0.16em]">Elo</Table.Head>
                </Table.Row>
            </Table.Header>
            <Table.Body class="[&_tr:last-child]:border-0">
                {#each rankedPlayers as player (player.rank)}
                    <Table.Row class={`border-0 bg-card hover:bg-card dark:bg-[hsl(var(--surface-container-high)/0.6)] dark:hover:bg-[hsl(var(--surface-container-high)/0.82)] ${player.rank === 1 ? 'ring-1 ring-primary/35 shadow-[0_0_0_1px_hsl(var(--primary)/0.08)_inset] dark:ring-primary/50 dark:shadow-[0_0_0_1px_hsl(var(--primary)/0.24)_inset]' : ''} ${isCurrentPlayer(player) ? 'ring-2 ring-primary/40 bg-primary/5 dark:ring-primary/65 dark:bg-[hsl(var(--primary)/0.16)]' : ''}`}>
                        <Table.Cell class="rounded-l-xl px-5 font-medium">
                            <div class="flex items-center gap-3">
                                <span class={`inline-flex min-w-[48px] justify-center rounded-lg px-2 py-1 font-display text-sm font-bold ${
                                    player.rank === 1
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-secondary text-secondary-foreground dark:bg-[hsl(var(--surface-container-low))] dark:text-foreground'
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
