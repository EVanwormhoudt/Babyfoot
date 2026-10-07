<script lang="ts">
	import type { GameRead, GameRatingChangeRead, TeamRead } from '$lib/api/types';
	type RatingType = 'overall' | 'monthly' | 'yearly';
	let { game, class: className = '' } = $props<{ game: GameRead; class?: string }>();
	let players = $derived([...game.teams].sort((a: TeamRead, b: TeamRead) => a.team_number - b.team_number));
	const periods: Array<{ key: RatingType; label: string }> = [
		{ key: 'monthly', label: 'Mensuel' },
		{ key: 'yearly', label: 'Annuel' },
		{ key: 'overall', label: 'Général' }
	];
	function changeFor(playerId: number, ratingType: RatingType) {
		return game.rating_changes?.find((change: GameRatingChangeRead) => change.player_id === playerId && change.rating_type === ratingType);
	}
	function amount(value: number | undefined) {
		return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '—';
	}
	function delta(value: number | undefined) {
		return typeof value === 'number' && Number.isFinite(value) ? `${value > 0 ? '+' : ''}${value.toFixed(1)}` : '—';
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex (Keyboard users need to scroll the comparison on narrow screens.) -->
<div class={`rating-comparison ${className}`} role="region" aria-label="Évolution des points" tabindex="0">
	<table>
		<caption class="sr-only">Évolution des points des joueurs par classement</caption>
		<thead>
			<tr>
				<th scope="col" class="rating-period-heading">Classement</th>
				{#each players as team (team.player_id)}
					<th scope="col" class="rating-player-heading" class:rating-player-blue={team.team_number === 2}>
						<span class="rating-player-name"><span class="rating-team-dot" aria-hidden="true"></span>{team.player.player_name ?? `Joueur #${team.player_id}`}</span>
						<span class="rating-column-label">Avant → Après <span>Variation</span></span>
					</th>
				{/each}
			</tr>
		</thead>
		<tbody>
			{#each periods as period}
				<tr>
					<th scope="row">{period.label}</th>
					{#each players as team (team.player_id)}
						{@const change = changeFor(team.player_id, period.key)}
						<td><div class="rating-player-values">
							<div class="rating-transition"><span>{amount(change?.running_mu_before ?? change?.mu_before)}</span><span aria-hidden="true">→</span><strong>{amount(change?.running_mu_after ?? change?.mu_after)}</strong></div>
							<span class="rating-delta-badge" class:rating-gain={(change?.delta_mu ?? 0) > 0} class:rating-loss={(change?.delta_mu ?? 0) < 0}>{delta(change?.delta_mu)}</span>
						</div></td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
</div>
