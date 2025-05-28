<script lang="ts">
    import * as Table from "$lib/components/ui/table/index.js";
    import * as Select from "$lib/components/ui/select";
    import {getLeaderboard, getPlayers} from '$lib/api/players';


    let players: {
        name: string;
        wins: number;
        losses: number;
        elo: number;
    }[] = [];

    let leaderboard: any[];


    let selected = { value: "monthly", label: "Monthly" };

    // Fetch leaderboard based on scope
    async function loadPlayers(selected:{ value: string, label: string }) {

        leaderboard =  await getPlayers(fetch);
        let filtered = leaderboard.filter((p) => p.active == true); // remove empty players
        players = filtered.map((p) => {
            const rating = p.rating;

            const mu =
                selected.value === 'monthly' ? rating.mu_monthly :
                    selected.value === 'yearly' ? rating.mu_yearly :
                        rating.mu_overall;

            const sigma =
                selected.value === 'monthly' ? rating.sigma_monthly :
                    selected.value === 'yearly' ? rating.sigma_yearly :
                        rating.sigma_overall;

            return {
                name: p.player_name,
                wins: Math.floor(mu),          // placeholder
                losses: Math.floor(sigma * 2), // placeholder
                elo: Math.round(mu * 100)      // scale for UI
            };
        });
        players.sort((a, b) => b.elo - a.elo); // sort by elo
    }

    $: loadPlayers(selected);
</script>

<section class="p-8">

    <h2 class="text-3xl font-semibold mb-6">Leaderboard</h2>

    <div class="flex justify-end mb-4 datepicker">
        <Select.Root bind:selected on:change={loadPlayers}>
            <Select.Trigger class="w-[180px] border-primary">
                <Select.Value placeholder="Leaderboard Type" />
            </Select.Trigger>
            <Select.Content >
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
            {#each players as player, i (i)}
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