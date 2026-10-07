<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChartNoAxesCombined from '@lucide/svelte/icons/chart-no-axes-combined';
	import MatchRatingHoverPanel from './MatchRatingHoverPanel.svelte';
	import type { GameRead } from '$lib/api/types';
	let { game } = $props<{ game: GameRead }>();
	let expanded = $state(false);
</script>

<details class="point-evolution" ontoggle={(event) => (expanded = event.currentTarget.open)}>
	<summary>
		<ChartNoAxesCombined size={18} aria-hidden="true" />
		<span>{expanded ? 'Masquer' : 'Voir'} l'évolution des points</span>
		<ChevronDown class="point-evolution-chevron" size={18} aria-hidden="true" />
	</summary>
	<div class="point-evolution-content"><MatchRatingHoverPanel {game} /></div>
</details>
