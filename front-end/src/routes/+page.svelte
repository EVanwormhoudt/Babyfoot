<script lang="ts">
	import MatchRatingHoverPanel from '$lib/components/matches/MatchRatingHoverPanel.svelte';
	import type { GameRead } from '$lib/api/types';
	import type { LeaderboardRow, Player } from './+page';

	export let data: {
		games: GameRead[];
		lastTenZeroMatch: GameRead | null;
		top3: LeaderboardRow[];
	};

	// ——— Helpers for matches, using your actual shape ———
	const teamPlayers = (g: GameRead, n: 1 | 2): Player[] =>
		(g?.teams
			?.filter((t) => t.team_number === n)
			.map((t) => t.player)
			.filter((p) => !!p) as Player[] | undefined) ?? [];

	const nameOf = (p?: Player) => p?.player_name ?? '—';
	const teamLabel = (g: GameRead, n: 1 | 2) => {
		const names = teamPlayers(g, n)
			.map((p) => nameOf(p))
			.filter((name) => name !== '—');
		return names.length > 0 ? names.join(' / ') : `Équipe ${n}`;
	};

	const scoreA = (g: GameRead) => g.result_team1 ?? 0;
	const scoreB = (g: GameRead) => g.result_team2 ?? 0;

	const winnerTeam = (g: GameRead): 0 | 1 | 2 => {
		const a = scoreA(g);
		const b = scoreB(g);
		if (a === b) return 0;
		return a > b ? 1 : 2;
	};

	type TeamOutcome = 'winner' | 'defeated' | 'draw';
	const teamOutcome = (g: GameRead, n: 1 | 2): TeamOutcome => {
		const winner = winnerTeam(g);
		if (winner === 0) return 'draw';
		return winner === n ? 'winner' : 'defeated';
	};

	const outcomeLabel = (outcome: TeamOutcome) =>
		outcome === 'winner' ? 'Victoire' : outcome === 'defeated' ? 'Défaite' : 'Nul';
	const outcomeClass = (outcome: TeamOutcome) =>
		outcome === 'winner'
			? 'tone-positive'
			: outcome === 'defeated'
				? 'tone-negative'
				: 'text-muted-foreground';

	const getYearlyDelta = (g: GameRead, playerId: number): number | null => {
		const change = g.rating_changes?.find(
			(item) => item.player_id === playerId && item.rating_type === 'yearly'
		);
		return typeof change?.delta_mu === 'number' ? change.delta_mu : null;
	};

	const formatDelta = (delta: number | null) => {
		if (delta === null) return null;
		return `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`;
	};

	const deltaClass = (delta: number | null) => {
		if (delta === null) return 'text-muted-foreground';
		if (delta > 0) return 'tone-positive';
		if (delta < 0) return 'tone-negative';
		return 'text-muted-foreground';
	};

	type DeltaRow = {
		text: string;
		className: string;
	};

	const teamDeltaRows = (g: GameRead, players: Player[]): DeltaRow[] => {
		const deltas = players.map((player) => getYearlyDelta(g, player.id));
		const firstNumeric = deltas.find((value): value is number => value !== null);
		const allSameNumeric =
			firstNumeric !== undefined &&
			deltas.every((value) => value !== null && Math.abs(value - firstNumeric) < 1e-9);

		return deltas.map((delta, index) => {
			if (allSameNumeric && index > 0) {
				return {
					text: '',
					className: 'text-muted-foreground/65'
				};
			}

			const formatted = formatDelta(delta);
			if (formatted) {
				return {
					text: formatted,
					className: deltaClass(delta)
				};
			}

			return {
				text: '—',
				className: 'text-muted-foreground/40'
			};
		});
	};

	const dateDMY = (iso: string) =>
		new Date(iso).toLocaleDateString('fr-FR', {
			day: '2-digit',
			month: 'short',
			year: 'numeric'
		});
	const timeHHMM = (iso: string) =>
		new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

	// ——— Helpers for leaderboard ———
	const rowName = (r: LeaderboardRow) => r?.player_name ?? 'Joueur';

	const rowRating = (r: LeaderboardRow) => r?.mu ?? r?.rating?.mu_monthly;
	const rowWL = (r: LeaderboardRow) =>
		`${r.wins ?? 0}-${Math.max(0, (r.games_played ?? 0) - (r.wins ?? 0))}`;
	const ratingLabel = (r: LeaderboardRow) => {
		const rating = rowRating(r);
		return typeof rating === 'number' ? rating.toFixed(1) : '—';
	};
</script>

<svelte:head>
	<title>BabyFoot MyDso — Le club</title>
	<meta
		name="description"
		content="La vie du club MyDso : derniers matchs de babyfoot, classement mensuel et performances des joueurs."
	/>
</svelte:head>

<div class="club-home">
	<div class="club-eyebrow">
		<span>MYDSO / LE CLUB DE BABYFOOT</span><span>LE JEU. L’ÉQUIPE. LA REVANCHE.</span>
	</div>
	<section class="club-hero" aria-labelledby="club-title">
		<div class="hero-copy">
			<p class="club-kicker"><span class="club-dot"></span> La pause devient un sport.</p>
			<h1 id="club-title">À vous<br />de <em>jouer.</em></h1>
			<p class="hero-description">
				Les rivalités se jouent à la table.<br />Les belles victoires restent ici.
			</p>
			<div class="hero-actions">
				<a class="club-button" href="/create">Nouveau match <span aria-hidden="true">↗</span></a>
				<a class="hero-link" href="/leaderboard">Le classement <span aria-hidden="true">→</span></a>
			</div>
		</div>
		<div class="hero-art" aria-hidden="true">
			<div class="club-stamp">MYDSO<span>FOOSBALL CLUB</span></div>
			<svg viewBox="0 0 520 410" fill="none">
				<g transform="translate(64 32) rotate(-12 200 180)">
					<rect x="0" y="15" width="380" height="350" rx="22" fill="#292929" />
					<rect width="380" height="350" rx="22" fill="#007fb1" stroke="#b3b3b3" stroke-width="2" />
					<path d="M18 18h344v314H18zM18 175h344" stroke="#cccccc" stroke-width="2" />
					<circle cx="190" cy="175" r="49" stroke="#cccccc" stroke-width="2" />
					<path d="M126 18v48h128V18M126 332v-48h128v48" stroke="#cccccc" stroke-width="2" />
					{#each [91, 250] as y, index}
						<path d={`M-35 ${y + 5}H412`} stroke="#292929" stroke-width="9" />
						<path d={`M-35 ${y}H412`} stroke="#cccccc" stroke-width="6" />
						<rect
							x={index === 0 ? -48 : 405}
							y={y - 10}
							width="28"
							height="20"
							rx="5"
							fill="#e6e6e6"
						/>
						{#each [90, 190, 290] as x}
							<rect
								x={x - 11}
								y={y - 12}
								width="28"
								height="49"
								rx="6"
								fill="#292929"
								opacity=".4"
							/>
							<rect
								x={x - 15}
								y={y - 19}
								width="28"
								height="46"
								rx="5"
								fill={index === 0 ? '#7fcf5a' : '#f2f2f2'}
							/>
							<circle cx={x - 1} cy={y - 20} r="13" fill={index === 0 ? '#98d97a' : '#ffffff'} />
							<path
								d={`M${x - 8} ${y + 12}h14`}
								stroke="#007fb1"
								stroke-opacity=".35"
								stroke-width="3"
							/>
						{/each}
					{/each}
					<circle cx="235" cy="186" r="13" fill="#292929" opacity=".5" />
					<circle cx="232" cy="180" r="12" fill="#7fcf5a" />
					<circle cx="229" cy="177" r="4" fill="#b2e59b" />
				</g>
			</svg>
			<p>UNE TABLE. DEUX ÉQUIPES. TOUT À JOUER.</p>
		</div>
	</section>

	<div class="club-ticker">
		<span class="ticker-label">LA DERNIÈRE FANNY <span aria-hidden="true">↗</span></span>
		{#if data.lastTenZeroMatch}
			<a href={`/matches/${data.lastTenZeroMatch.id}`}
				><span>{teamLabel(data.lastTenZeroMatch, 1)}</span><strong
					>{scoreA(data.lastTenZeroMatch)} – {scoreB(data.lastTenZeroMatch)}</strong
				><span>{teamLabel(data.lastTenZeroMatch, 2)}</span><small
					>{dateDMY(data.lastTenZeroMatch.game_timestamp)}</small
				></a
			>
		{:else}
			<p>Le prochain 10–0 entrera dans l’histoire du club.</p>
		{/if}
	</div>

	<div class="club-dashboard">
		<section class="match-section" aria-labelledby="récent-title">
			<div class="section-heading">
				<div>
					<p class="club-section-label">AU BORD DU TERRAIN</p>
					<h2 id="récent-title">Derniers matchs<span>.</span></h2>
				</div>
				<a href="/matches">Tous les matchs <span aria-hidden="true">↗</span></a>
			</div>
			{#if data?.games?.length}
				<ul class="club-match-list">
					{#each data.games as g}
						<li class="club-match">
							<a
								href={`/matches/${g.id}`}
								aria-label={`Match ${g.id} : ${teamLabel(g, 1)} contre ${teamLabel(g, 2)}`}
							>
								<div class="match-meta">
									<span>MATCH / {String(g.id).padStart(3, '0')}</span><span
										>{dateDMY(g.game_timestamp)} · {timeHHMM(g.game_timestamp)}</span
									>
								</div>
								<div class="match-teams">
									{#each [1, 2] as team}
										{@const n = team as 1 | 2}
										{@const players = teamPlayers(g, n)}
										{@const deltas = teamDeltaRows(g, players)}
										<div class:team-right={n === 2} class="match-team">
											<p class={`outcome ${outcomeClass(teamOutcome(g, n))}`}>
												{outcomeLabel(teamOutcome(g, n))}
											</p>
											{#each players as player, i}<div class="player-line">
													<span>{nameOf(player)}</span><small class={deltas[i].className}
														>{deltas[i].text}</small
													>
												</div>{:else}<div class="player-line">Équipe {n}</div>{/each}
										</div>
										{#if n === 1}<div class="match-score">
												<span class:winning={winnerTeam(g) === 1}>{scoreA(g)}</span><span
													class="score-divider">:</span
												><span class:winning={winnerTeam(g) === 2}>{scoreB(g)}</span>
											</div>{/if}
									{/each}
								</div>
							</a>
							<details class="match-ratings">
								<summary>Évolution des points <span aria-hidden="true">+</span></summary
								><MatchRatingHoverPanel game={g} class="mt-3" />
							</details>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="club-empty">
					<span aria-hidden="true">01 /</span>
					<h3>Tout commence par un match.</h3>
					<p>La table vous attend. À vous d’écrire le premier score.</p>
					<a href="/create" class="club-button">Créer un match <span aria-hidden="true">↗</span></a
					>
				</div>
			{/if}
		</section>
		<aside class="club-leaderboard" aria-labelledby="leaders-title">
			<div class="section-heading">
				<div>
					<p class="club-section-label">LE PODIUM DU MOIS</p>
					<h2 id="leaders-title">Le haut du jeu<span>.</span></h2>
				</div>
				<span class="podium-symbol" aria-hidden="true">✳</span>
			</div>
			{#if data?.top3?.length}
				<ol>
					{#each data.top3 as row, idx}<li class:leader={idx === 0}>
							<a href={`/stats?player_id=${row.id}&scope=monthly`}
								><span class="rank">0{idx + 1}</span>
								<div class="rank-player">
									<strong>{rowName(row)}</strong><small
										>{row.wins ?? 0} victoires · {rowWL(row)} V–D</small
									>
								</div>
								<div class="rank-rating">
									<strong>{ratingLabel(row)}</strong><small>ELO</small>
								</div></a
							>
						</li>{/each}
				</ol>
			{:else}<div class="podium-empty">
					<p>La première place est à prendre.</p>
					<span>Jouez un match pour lancer le classement du mois.</span>
				</div>{/if}
			<a class="leaderboard-link" href="/leaderboard"
				>Explorer le classement <span aria-hidden="true">↗</span></a
			>
			<div class="club-note">
				<span aria-hidden="true">↗</span>
				<p>Un beau geste.<br />Un bon match.<br /><strong>Et la revanche.</strong></p>
				<small>L’ESPRIT MYDSO</small>
			</div>
		</aside>
	</div>
	<footer class="club-footer">
		<span>BABYFOOT / MYDSO</span><span>Les collègues d’abord. Les adversaires ensuite.</span><a
			href="/stats">Vos statistiques ↗</a
		>
	</footer>
</div>
