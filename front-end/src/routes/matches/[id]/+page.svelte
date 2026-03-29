<script lang="ts">
    import {Card, CardContent, CardHeader, CardTitle} from '$lib/components/ui/card';
    import type {GameRatingChangeRead, GameRead, TeamRead} from '$lib/api/types';
    import type {PageData} from './$types';

    type RatingType = 'overall' | 'monthly' | 'yearly';

    let {data} = $props<{ data: PageData }>();
    const game = $derived<GameRead>(data.game);
    const ratingTypes: RatingType[] = ['overall', 'monthly', 'yearly'];

    function teamPlayers(teamNumber: 1 | 2) {
        return game.teams.filter((team: TeamRead) => team.team_number === teamNumber);
    }

    function teamLabel(teamNumber: 1 | 2) {
        const names = teamPlayers(teamNumber)
            .map((team: TeamRead) => team.player.player_name ?? `P${team.player_id}`);
        return names.length ? names.join(' / ') : `Equipe ${teamNumber}`;
    }

    function winnerTeam() {
        if (game.result_team1 === game.result_team2) return 0;
        return game.result_team1 > game.result_team2 ? 1 : 2;
    }

    function teamOutcome(teamNumber: 1 | 2) {
        const winner = winnerTeam();
        if (winner === 0) return 'Nul';
        return winner === teamNumber ? 'Victoire' : 'Défaite';
    }

    function outcomeClass(teamNumber: 1 | 2) {
        const winner = winnerTeam();
        if (winner === 0) return 'text-muted-foreground';
        return winner === teamNumber ? 'tone-positive' : 'tone-negative';
    }

    function scoreClass(left: number, right: number) {
        return left > right ? 'tone-positive' : 'text-foreground';
    }

    function formatDate(iso: string) {
        return new Date(iso).toLocaleDateString(undefined, {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric'
        });
    }

    function formatTime(iso: string) {
        return new Date(iso).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    }

    function deltaFor(playerId: number, ratingType: RatingType) {
        const change = game.rating_changes?.find(
            (item: GameRatingChangeRead) => item.player_id === playerId && item.rating_type === ratingType
        );
        return typeof change?.delta_mu === 'number' ? change.delta_mu : null;
    }

    function deltaLabel(value: number | null) {
        if (value === null) return '—';
        const sign = value > 0 ? '+' : '';
        return `${sign}${value.toFixed(1)}`;
    }

    function deltaClass(value: number | null) {
        if (value === null) return 'text-muted-foreground';
        if (value > 0) return 'tone-positive';
        if (value < 0) return 'tone-negative';
        return 'text-muted-foreground';
    }
</script>

<section class="mx-auto max-w-[1100px] space-y-4 px-4 py-6">
    <a
            href="/matches"
            class="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition hover:bg-secondary"
    >
        ← Retour aux matchs
    </a>

    <Card class="rounded-3xl bg-[hsl(var(--surface-container-low))]">
        <CardHeader class="space-y-2">
            <p class="editorial-kicker">Match #{game.id}</p>
            <CardTitle class="font-display text-3xl font-bold uppercase tracking-tight">Détails du match</CardTitle>
            <p class="text-sm text-muted-foreground">
                {formatDate(game.game_timestamp)} a {formatTime(game.game_timestamp)}
            </p>
        </CardHeader>
        <CardContent class="space-y-5">
            <div class="grid gap-3 rounded-2xl border border-border/70 bg-card p-4 text-center sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                <div class="space-y-1">
                    <p class={`editorial-kicker ${outcomeClass(1)}`}>{teamOutcome(1)}</p>
                    <p class="text-base font-semibold">{teamLabel(1)}</p>
                </div>

                <div class="font-display text-[2.4rem] font-bold leading-none tabular-nums">
                    <span class={scoreClass(game.result_team1, game.result_team2)}>{game.result_team1}</span>
                    <span class="mx-2 text-muted-foreground">-</span>
                    <span class={scoreClass(game.result_team2, game.result_team1)}>{game.result_team2}</span>
                </div>

                <div class="space-y-1">
                    <p class={`editorial-kicker ${outcomeClass(2)}`}>{teamOutcome(2)}</p>
                    <p class="text-base font-semibold">{teamLabel(2)}</p>
                </div>
            </div>

            <div class="overflow-x-auto rounded-2xl border border-border/70 bg-card">
                <table class="min-w-full text-sm">
                    <thead class="bg-secondary/55 text-left text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
                    <tr>
                        <th class="px-4 py-3 font-semibold">Joueur</th>
                        <th class="px-4 py-3 font-semibold">Equipe</th>
                        <th class="px-4 py-3 font-semibold">General</th>
                        <th class="px-4 py-3 font-semibold">Mensuel</th>
                        <th class="px-4 py-3 font-semibold">Annuel</th>
                    </tr>
                    </thead>
                    <tbody>
                    {#each game.teams as team (team.player_id)}
                        <tr class="border-t border-border/60">
                            <td class="px-4 py-3 font-medium">{team.player.player_name ?? `P${team.player_id}`}</td>
                            <td class="px-4 py-3 text-muted-foreground">Equipe {team.team_number}</td>
                            {#each ratingTypes as ratingType}
                                {@const delta = deltaFor(team.player_id, ratingType)}
                                <td class={`px-4 py-3 font-semibold tabular-nums ${deltaClass(delta)}`}>{deltaLabel(delta)}</td>
                            {/each}
                        </tr>
                    {/each}
                    </tbody>
                </table>
            </div>
        </CardContent>
    </Card>
</section>
