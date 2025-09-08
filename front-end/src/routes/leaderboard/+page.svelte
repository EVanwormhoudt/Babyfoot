<script lang="ts">
    import {goto} from "$app/navigation";

    let {data} = $props<{
        data: {
            scope: 'monthly' | 'yearly' | 'overall';
            year: number;
            month?: number;
            players: { name: string; wins: number; losses: number; elo: number }[];
        }
    }>();

    data.year ||= new Date().getFullYear();

    const scopeLabel = (v: 'monthly' | 'yearly' | 'overall') =>
        v === 'monthly' ? 'Monthly' : v === 'yearly' ? 'Yearly' : 'Overall';

    let scopeSel = $state<{ value: 'monthly' | 'yearly' | 'overall'; label: string }>({
        value: data.scope,
        label: scopeLabel(data.scope)
    });

    const now = new Date();
    const currentYear = now.getFullYear();
    const base = Math.max(currentYear, data.year ?? currentYear);
    let years = Array.from({length: Math.max(0, base - 2018 + 1)}, (_, i) => base - i);

    let yearSel = $state<{ value: string; label: string }>({
        value: String(data.year),
        label: String(data.year)
    });

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const months = Array.from({length: 12}, (_, i) => ({value: String(i + 1), label: monthNames[i]}));
    let monthSel = $state<{ value: string; label: string }>({
        value: String(data.month ?? (now.getMonth() + 1)),
        label: monthNames[(data.month ?? (now.getMonth() + 1)) - 1]
    });

    $effect(() => {
        scopeSel = {value: data.scope, label: scopeLabel(data.scope)};
        yearSel = {value: String(data.year), label: String(data.year)};
        if (data.scope === 'monthly') {
            const m = data.month ?? (now.getMonth() + 1);
            monthSel = {value: String(m), label: monthNames[m - 1]};
        }
    });

    $effect(() => {
        if (typeof window === 'undefined') return;
        const url = new URL(window.location.href);
        let changed = false;

        if (url.searchParams.get('scope') !== scopeSel.value) {
            url.searchParams.set('scope', scopeSel.value);
            changed = true;
        }

        if (scopeSel.value === 'overall') {
            if (url.searchParams.has('year')) {
                url.searchParams.delete('year');
                changed = true;
            }
            if (url.searchParams.has('month')) {
                url.searchParams.delete('month');
                changed = true;
            }
        } else {
            if (url.searchParams.get('year') !== yearSel.value) {
                url.searchParams.set('year', yearSel.value);
                changed = true;
            }
            if (scopeSel.value === 'monthly') {
                if (url.searchParams.get('month') !== monthSel.value) {
                    url.searchParams.set('month', monthSel.value);
                    changed = true;
                }
            } else if (url.searchParams.has('month')) {
                url.searchParams.delete('month');
                changed = true;
            }
        }

        if (changed) {
            goto(`${url.pathname}?${url.searchParams.toString()}`, {
                replaceState: true,
                noScroll: true,
            });
        }
    });
</script>


<section class="p-8">
    <h2 class="text-3xl font-semibold mb-6">Leaderboard</h2>

    <div class="flex flex-wrap gap-3 justify-end mb-4 datepicker">
        <!-- Month (show only when monthly) -->
        {#if scopeSel.value === 'monthly'}
            <Select.Root bind:selected={monthSel}>
                <Select.Trigger>
                    {#snippet child({props})}
                        <button class="w-[140px]" {...props}>
                            <Select.Value placeholder="Month"/>
                        </button>
                    {/snippet}
                </Select.Trigger>
                <Select.Content align="center">
                    {#each months as m}
                        <Select.Item value={m.value}>{m.label}</Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        {/if}

        <!-- Year (show when monthly or yearly) -->
        {#if scopeSel.value !== 'overall'}
            <Select.Root bind:selected={yearSel}>
                <Select.Trigger>
                    {#snippet child({props})}
                        <button class="w-[120px]" {...props}>
                            <Select.Value placeholder="Year"/>
                        </button>
                    {/snippet}
                </Select.Trigger>
                <Select.Content>
                    {#each years as y}
                        <Select.Item value={String(y)}>{y}</Select.Item>
                    {/each}
                </Select.Content>
            </Select.Root>
        {/if}

        <!-- Scope -->
        <Select.Root bind:selected={scopeSel}>
            <Select.Trigger>
                {#snippet child({props})}
                    <button class="w-[180px] border-primary" {...props}>
                        <Select.Value placeholder="Leaderboard Type"/>
                    </button>
                {/snippet}
            </Select.Trigger>
            <Select.Content>
                <Select.Item value="monthly">Monthly</Select.Item>
                <Select.Item value="yearly">Yearly</Select.Item>
                <Select.Item value="overall">Overall</Select.Item>
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
