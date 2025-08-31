<script lang="ts">
    import {goto} from "$app/navigation";

    let {data} = $props<{
        data: {
            scope: 'monthly' | 'yearly' | 'overall';
            players: { name: string; wins: number; losses: number; elo: number }[];
        }
    }>();

    function scopeToLabel(v: 'monthly' | 'yearly' | 'overall') {
        return v === 'monthly' ? 'Monthly' : v === 'yearly' ? 'Yearly' : 'Overall';
    }

    // Select expects { value, label }
    let selected = $state<{ value: 'monthly' | 'yearly' | 'overall'; label: string }>({
        value: data.scope,
        label: scopeToLabel(data.scope)
    });

    // Keep the Select in sync when `data.scope` changes after navigation
    $effect(() => {
        selected = {value: data.scope, label: scopeToLabel(data.scope)};
    });

    function onScopeChange() {
        const url = new URL(window.location.href);
        url.searchParams.set('scope', selected.value);
        goto(`${url.pathname}?${url.searchParams.toString()}`, {
            replaceState: true,
            noScroll: true,
            keepfocus: true
        });
    }
</script>

<section class="p-8">
    <h2 class="text-3xl font-semibold mb-6">Leaderboard</h2>

    <div class="flex justify-end mb-4 datepicker">
        <Select.Root bind:selected onchange={onScopeChange}>
            <Select.Trigger class="w-[180px] border-primary">
                <Select.Value placeholder="Leaderboard Type" />
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
                <Table.Head class="text-right">Elo</Table.Head>
            </Table.Row>
        </Table.Header>
        <Table.Body>
            {#each data.players as player, i (i)}
                <Table.Row>
                    <Table.Cell class="font-medium">{player.name}</Table.Cell>
                    <Table.Cell>{player.wins}</Table.Cell>
                    <Table.Cell>{player.losses}</Table.Cell>
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
