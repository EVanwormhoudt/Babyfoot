<script lang="ts">
	import type { GameRatingChangeRead, GameRead, TeamRead } from '$lib/api/types';

	type RatingType = 'overall' | 'monthly' | 'yearly';
	type TeamNumber = 1 | 2;

	let { game, class: className = '' } = $props<{ game: GameRead; class?: string }>();

	const ratingTypes: Array<{ key: RatingType; label: string }> = [
		{ key: 'overall', label: 'General' },
		{ key: 'monthly', label: 'Mensuel' },
		{ key: 'yearly', label: 'Annuel' }
	];
	const teamNumbers: TeamNumber[] = [1, 2];

	function teamPlayers(teamNumber: TeamNumber): TeamRead[] {
		return game.teams.filter((team: TeamRead) => team.team_number === teamNumber);
	}

	function teamName(team: TeamRead) {
		return team.player.player_name ?? `P${team.player_id}`;
	}

	function changeFor(playerId: number, ratingType: RatingType) {
		return game.rating_changes?.find(
			(item: GameRatingChangeRead) => item.player_id === playerId && item.rating_type === ratingType
		);
	}

	function deltaLabel(value: number | null) {
		if (value === null) return '—';
		const sign = value > 0 ? '+' : '';
		return `${sign}${value.toFixed(1)}`;
	}

	function ratingLabel(value: number | null) {
		if (value === null) return '—';
		return value.toFixed(1);
	}

	function deltaClass(value: number | null) {
		if (value === null) return 'text-muted-foreground';
		if (value > 0) return 'tone-positive';
		if (value < 0) return 'tone-negative';
		return 'text-muted-foreground';
	}

	function teamHeading(teamNumber: TeamNumber) {
		return teamNumber === 1 ? 'Equipe rouge' : 'Equipe bleue';
	}

	function teamTone(teamNumber: TeamNumber) {
		return teamNumber === 1
			? 'border-[hsl(var(--team-red)/0.3)] bg-[hsl(var(--team-red-soft)/0.45)]'
			: 'border-[hsl(var(--team-blue)/0.3)] bg-[hsl(var(--team-blue-soft)/0.45)]';
	}

	function playerCountLabel(count: number) {
		return `${count} joueur${count > 1 ? 's' : ''}`;
	}
</script>

<div
	class={`grid gap-3 rounded-2xl border border-border/70 bg-[hsl(var(--surface-container-low)/0.78)] p-3 sm:p-4 lg:grid-cols-2 ${className}`}
>
	{#each teamNumbers as teamNumber}
		{@const players = teamPlayers(teamNumber)}
		<section class={`rounded-xl border p-3 ${teamTone(teamNumber)}`}>
			<div class="mb-3 flex items-start justify-between gap-3">
				<div class="min-w-0">
					<p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
						{teamHeading(teamNumber)}
					</p>
					<p class="truncate text-sm font-semibold text-foreground">
						{players.length
							? players.map((team) => teamName(team)).join(' / ')
							: `Equipe ${teamNumber}`}
					</p>
				</div>
				<span
					class={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${teamNumber === 1 ? 'tone-team-red' : 'tone-team-blue'}`}
				>
					{playerCountLabel(players.length)}
				</span>
			</div>

			{#if players.length}
				<div class="overflow-x-auto">
					<table class="min-w-full text-xs sm:text-sm">
						<thead class="text-left text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
							<tr>
								<th class="pb-2 pr-4 font-semibold">Joueur</th>
								{#each ratingTypes as ratingType}
									<th class="pb-2 pr-4 font-semibold tabular-nums">{ratingType.label}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each players as team (team.player_id)}
								<tr class="border-t border-border/35 first:border-t-0">
									<td class="py-2 pr-4 font-medium text-foreground">{teamName(team)}</td>
									{#each ratingTypes as ratingType}
										{@const change = changeFor(team.player_id, ratingType.key)}
										{@const delta = typeof change?.delta_mu === 'number' ? change.delta_mu : null}
										{@const rating = typeof change?.mu_after === 'number' ? change.mu_after : null}
										<td class="py-2 pr-4">
											<div class="flex min-w-[5rem] flex-col gap-0.5">
												<span class={`font-semibold tabular-nums ${deltaClass(delta)}`}>
													{deltaLabel(delta)}
												</span>
												<span class="text-[11px] tabular-nums text-muted-foreground">
													{ratingLabel(rating)}
												</span>
											</div>
										</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{:else}
				<p class="text-sm text-muted-foreground">Aucune variation disponible pour cette equipe.</p>
			{/if}
		</section>
	{/each}
</div>
