<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;

	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import * as Pagination from '$lib/components/ui/pagination/index.js';
	import { RangeCalendar } from '$lib/components/ui/range-calendar/index.js';
	import * as Popover from '$lib/components/ui/popover/index.js';
	import { deleteGame, updateGame } from '$lib/api/matches';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { today, getLocalTimeZone, CalendarDate, type DateValue } from '@internationalized/date';
	import { page } from '$app/state';

	type MatchItem = PageData['items'][number];
	type MatchGroup = { key: string; label: string; matches: MatchItem[] };
	let groupedMatches: MatchGroup[] = [];
	let deletingId: number | null = null;
	let editingMatch: MatchItem | null = null;
	let savingEdit = false;
	let editTeam1Score = '';
	let editTeam2Score = '';

	function pushRangeToUrl(r?: { start?: DateValue; end?: DateValue }) {
		if (!r?.start || !r?.end) return;
		const start = r.start.toString();
		const end = r.end.toString();

		// Only navigate if something actually changed (prevents loops)
		const sp = new URLSearchParams(page.url.searchParams);
		if (sp.get('start_date') === start && sp.get('end_date') === end) return;

		sp.set('start_date', start);
		sp.set('end_date', end);
		sp.set('page', '1');
		goto(`?${sp.toString()}`, { replaceState: true });
	}

	function toTime(dt: string) {
		return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
	}

	// build/merge query params for navigation without losing others
	function buildQuery(updates: Record<string, string | number | undefined | null>) {
		const u = new URLSearchParams(page.url.searchParams);
		for (const [k, v] of Object.entries(updates)) {
			if (v === undefined || v === null || v === '') u.delete(k);
			else u.set(k, String(v));
		}
		return u.toString();
	}

	function dayKey(dt: string) {
		const d = new Date(dt);
		const y = d.getFullYear();
		const m = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		return `${y}-${m}-${day}`;
	}

	function dayLabel(dt: string) {
		const target = new Date(dt);
		const now = new Date();
		const targetMidnight = new Date(target.getFullYear(), target.getMonth(), target.getDate());
		const nowMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
		const diffDays = Math.round((nowMidnight.getTime() - targetMidnight.getTime()) / 86_400_000);

		if (diffDays === 0) return "Aujourd'hui";
		if (diffDays === 1) return 'Hier';

		return target.toLocaleDateString(undefined, {
			weekday: 'long',
			day: '2-digit',
			month: 'long',
			year: 'numeric'
		});
	}

	function groupMatchesByDate(items: MatchItem[]): MatchGroup[] {
		const groups = new Map<string, MatchGroup>();

		for (const match of items) {
			const key = dayKey(match.game_timestamp);
			if (!groups.has(key)) {
				groups.set(key, {
					key,
					label: dayLabel(match.game_timestamp),
					matches: []
				});
			}
			groups.get(key)?.matches.push(match);
		}

		return Array.from(groups.values());
	}

	function teamPlayers(game: MatchItem, teamNumber: 1 | 2) {
		return game.teams.filter((t) => t.team_number === teamNumber);
	}

	function getYearlyDelta(game: MatchItem, playerId: number) {
		const change = game.rating_changes?.find(
			(item) => item.player_id === playerId && item.rating_type === 'yearly'
		);
		return typeof change?.delta_mu === 'number' ? change.delta_mu : null;
	}

	function formatDelta(delta: number | null) {
		if (delta === null) return null;
		const sign = delta > 0 ? '+' : '';
		return `${sign}${delta.toFixed(1)}`;
	}

	function deltaClass(delta: number | null) {
		if (delta === null) return 'text-muted-foreground';
		if (delta > 0) return 'tone-positive';
		if (delta < 0) return 'tone-negative';
		return 'text-muted-foreground';
	}

	function winnerTeam(game: MatchItem): 0 | 1 | 2 {
		const s1 = game.result_team1 ?? 0;
		const s2 = game.result_team2 ?? 0;
		if (s1 === s2) return 0;
		return s1 > s2 ? 1 : 2;
	}

	function scoreClass(sideScore: number, otherScore: number) {
		if (sideScore > otherScore) return 'text-foreground';
		return 'text-foreground';
	}

	type DeltaRow = {
		text: string;
		className: string;
	};

	function teamDeltaRows(game: MatchItem, players: MatchItem['teams']): DeltaRow[] {
		const deltas = players.map((player) => getYearlyDelta(game, player.player_id));
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
	}

	type TeamOutcome = 'winner' | 'defeated' | 'draw';

	function teamOutcome(game: MatchItem, teamNumber: 1 | 2): TeamOutcome {
		const winner = winnerTeam(game);
		if (winner === 0) return 'draw';
		return winner === teamNumber ? 'winner' : 'defeated';
	}

	function outcomeLabel(outcome: TeamOutcome) {
		if (outcome === 'winner') return 'Victoire';
		if (outcome === 'defeated') return 'Défaite';
		return 'Nul';
	}

	function outcomeClass(outcome: TeamOutcome) {
		if (outcome === 'winner') return 'tone-positive';
		if (outcome === 'defeated') return 'tone-negative';
		return 'text-muted-foreground';
	}

	function openEditModal(game: MatchItem) {
		editingMatch = game;
		editTeam1Score = String(game.result_team1 ?? 0);
		editTeam2Score = String(game.result_team2 ?? 0);
	}

	function closeEditModal() {
		if (savingEdit) return;
		editingMatch = null;
		editTeam1Score = '';
		editTeam2Score = '';
	}

	async function handleSaveEdit(event: SubmitEvent) {
		event.preventDefault();
		if (!editingMatch) return;

		const s1 = Number(editTeam1Score);
		const s2 = Number(editTeam2Score);

		if (!Number.isInteger(s1) || !Number.isInteger(s2)) {
			toast.error('Les scores doivent etre des nombres entiers.');
			return;
		}
		if (s1 < 0 || s2 < 0) {
			toast.error('Les scores ne peuvent pas etre negatifs.');
			return;
		}
		if (s1 === s2) {
			toast.error('Les scores ne peuvent pas etre egaux.');
			return;
		}

		const gameId = editingMatch.id;
		savingEdit = true;
		try {
			await updateGame(gameId, {
				result_team1: s1,
				result_team2: s2
			});

			toast.success(`Match #${gameId} modifie.`);
			closeEditModal();
			await goto(`?${buildQuery({})}`, { replaceState: true, invalidateAll: true });
		} catch (error: unknown) {
			console.error(error);
			const message = error instanceof Error ? error.message : 'Impossible de modifier ce match.';
			toast.error(message);
		} finally {
			savingEdit = false;
		}
	}

	async function handleDeleteMatch(gameId: number) {
		if (!confirm(`Supprimer le match #${gameId} ?`)) return;
		deletingId = gameId;

		try {
			const ok = await deleteGame(gameId);
			if (!ok) throw new Error('Suppression refusée par l’API');
			await goto(`?${buildQuery({})}`, { replaceState: true, invalidateAll: true });
		} catch (error) {
			console.error(error);
			alert('Impossible de supprimer ce match.');
		} finally {
			deletingId = null;
		}
	}

	let range: any | undefined;
	$: groupedMatches = groupMatchesByDate(data.items);

	// Initialize from URL on first run (so the picker reflects current filters)
	$: if (range?.start && range?.end) {
		pushRangeToUrl(range);
	}

	async function clearDates() {
		const sp = new URLSearchParams(page.url.searchParams);
		sp.delete('start_date');
		sp.delete('end_date');
		sp.set('page', '1');

		goto(`?${sp.toString()}`, { replaceState: true });
	}

	function setMonth(offset = 0) {
		const tz = getLocalTimeZone();
		const t = today(tz); // CalendarDate for "today" in local tz
		const start = new CalendarDate(t.year, t.month, 1).add({ months: offset });
		const end = start.add({ months: 1 }).subtract({ days: 1 });
		// update both the bound calendar and the URL
		range = { start, end };
		pushRangeToUrl(range);
	}

	// simple label for the trigger button
	function labelFromRange(r?: any) {
		if (!r?.start || !r?.end) return 'Choisir une plage de dates';
		return `${r.start.toString()} — ${r.end.toString()}`;
	}
</script>

<div class="mx-auto max-w-[1400px] space-y-6 px-4 py-4">
	<section
		class="relative overflow-hidden rounded-[28px] bg-[linear-gradient(135deg,hsl(var(--primary))_0%,hsl(146_79%_24%)_100%)] text-primary-foreground shadow-[0_20px_46px_rgba(0,107,36,0.28)]"
	>
		<div
			class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,rgba(85,254,117,0.22),transparent_44%)]"
		></div>
		<div class="relative space-y-6 p-7 md:p-10">
			<div class="space-y-3">
				<p class="editorial-kicker text-white/75">Match center</p>
				<h1 class="font-display text-4xl font-black uppercase tracking-tight sm:text-5xl">
					Historique des matchs
				</h1>
				<p class="max-w-2xl text-white/80">
					Filtrez les rencontres, modifiez les scores et gardez une vue complete sur la saison.
				</p>
			</div>

			<div class="flex flex-wrap gap-3">
				<Button class="bg-white text-primary hover:bg-white/90" href="/create" size="lg">
					Nouveau Match
				</Button>
				<Button
					class="border border-white bg-white/10 text-white hover:bg-white/20 hover:text-white"
					href="/leaderboard"
					size="lg"
					variant="outline"
				>
					Voir le Classement
				</Button>
			</div>

			<div class="flex flex-wrap gap-2 text-xs">
				<span class="bg-white/12 rounded-full px-3 py-1 text-white/80">
					{data.total} matchs au total
				</span>
				<span class="bg-white/12 rounded-full px-3 py-1 text-white/80">
					Page {data.page} / {data.pageCount}
				</span>
				<span class="bg-white/12 rounded-full px-3 py-1 text-white/80">
					{data.limit} matchs par page
				</span>
				{#if data.start_date && data.end_date}
					<span class="bg-white/12 rounded-full px-3 py-1 text-white/80">
						Periode : {data.start_date} - {data.end_date}
					</span>
				{/if}
			</div>
		</div>
	</section>

	<section class="rounded-3xl bg-[hsl(var(--surface-container-low))] p-4 md:p-5">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<p class="editorial-kicker">Filtres matchs</p>
			<div class="flex flex-wrap items-center gap-2">
				<Popover.Root>
					<Popover.Trigger>
						<Button class="w-[260px] justify-start font-normal" variant="outline">
							{labelFromRange(range)}
						</Button>
					</Popover.Trigger>
					<Popover.Content class="p-0">
						<!-- bind:value fires as the user picks dates;
                             our reactive block above triggers navigation when both ends exist -->
						<RangeCalendar bind:value={range} class="rounded-md border" />
					</Popover.Content>
				</Popover.Root>
				<Button onclick={() => setMonth(0)} variant="secondary">Ce mois-ci</Button>
				<Button onclick={() => setMonth(-1)} variant="ghost">Mois precedent</Button>
				<Button
					onclick={clearDates}
					variant="ghost"
					class="border border-destructive/60 text-destructive hover:bg-destructive/10 hover:text-destructive"
				>
					Effacer
				</Button>
			</div>
		</div>
	</section>

	<section class="space-y-6">
		<div class="flex items-center justify-between px-1">
			<p class="editorial-kicker">Historique des matchs</p>
			<p class="text-xs text-muted-foreground">{data.items.length} affiches sur cette page</p>
		</div>

		{#if data.items.length === 0}
			<div
				class="rounded-3xl bg-[hsl(var(--surface-container-low))] px-6 py-12 text-center text-sm text-muted-foreground"
			>
				Pas de matchs trouves avec les filtres actuels.
			</div>
		{:else}
			{#each groupedMatches as group (group.key)}
				<section class="space-y-3">
					<div class="flex items-center gap-3 px-1">
						<h2 class="text-sm font-semibold text-muted-foreground">{group.label}</h2>
						<div class="h-px flex-1 bg-border/60"></div>
					</div>
					<div class="space-y-3">
						{#each group.matches as game (game.id)}
							{@const s1 = game.result_team1 ?? 0}
							{@const s2 = game.result_team2 ?? 0}
							{@const outcome1 = teamOutcome(game, 1)}
							{@const outcome2 = teamOutcome(game, 2)}
							{@const team1Players = teamPlayers(game, 1)}
							{@const team2Players = teamPlayers(game, 2)}
							{@const team1DeltaRows = teamDeltaRows(game, team1Players)}
							{@const team2DeltaRows = teamDeltaRows(game, team2Players)}
							<div
								class="rounded-2xl border border-border/65 bg-card/90 px-4 py-4 transition hover:border-border/90"
							>
								<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
									<div class="overflow-x-auto">
										<div
											class="grid min-w-[640px] grid-cols-[minmax(0,170px)_auto_auto_minmax(0,170px)_auto] items-center gap-x-4"
										>
											<div class="min-w-0 space-y-1.5">
												<p class={`editorial-kicker ${outcomeClass(outcome1)}`}>
													{outcomeLabel(outcome1)}
												</p>
												{#each team1Players as player}
													<p class="truncate text-[1.05rem] font-semibold">
														{player.player.player_name ?? `P${player.player_id}`}
													</p>
												{/each}
											</div>

											<div class="space-y-1.5 pt-5 text-right">
												{#each team1DeltaRows as row}
													<p class={`text-[1.05rem] font-semibold tabular-nums ${row.className}`}>
														{row.text}
													</p>
												{/each}
											</div>

											<div class="min-w-[96px] text-center">
												<div
													class="font-display text-[2rem] font-bold tabular-nums leading-none sm:text-[2.2rem]"
												>
													<span class={scoreClass(s1, s2)}>{s1}</span>
													<span class="mx-1 text-muted-foreground">-</span>
													<span class={scoreClass(s2, s1)}>{s2}</span>
												</div>
											</div>

											<div class="min-w-0 space-y-1.5">
												<p class={`editorial-kicker ${outcomeClass(outcome2)}`}>
													{outcomeLabel(outcome2)}
												</p>
												{#each team2Players as player}
													<p class="truncate text-[1.05rem] font-semibold">
														{player.player.player_name ?? `P${player.player_id}`}
													</p>
												{/each}
											</div>

											<div class="space-y-1.5 pt-5 text-right">
												{#each team2DeltaRows as row}
													<p class={`text-[1.05rem] font-semibold tabular-nums ${row.className}`}>
														{row.text}
													</p>
												{/each}
											</div>
										</div>
									</div>

									<div class="flex items-center justify-end gap-3">
										<div class="text-right text-xs text-muted-foreground">
											<p class="font-semibold text-foreground/80">{toTime(game.game_timestamp)}</p>
											<p class="uppercase tracking-[0.08em]">Match #{game.id}</p>
										</div>

										<Button
											variant="ghost"
											size="sm"
											class="rounded-full border border-border/80 px-4 font-semibold text-foreground shadow-none hover:bg-secondary/70"
											onclick={() => openEditModal(game)}
											disabled={deletingId === game.id}
										>
											Editer
										</Button>
										<Button
											variant="ghost"
											size="sm"
											class="rounded-full border border-destructive/60 px-4 font-semibold text-destructive shadow-none hover:bg-destructive/10 hover:text-destructive"
											onclick={() => handleDeleteMatch(game.id)}
											disabled={deletingId === game.id}
										>
											{deletingId === game.id ? 'Suppression...' : 'Supprimer'}
										</Button>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/each}
		{/if}
	</section>

	{#if data.pageCount > 1}
		<section class="rounded-3xl bg-[hsl(var(--surface-container-low))] p-3">
			<Pagination.Root count={data.pageCount} page={data.page}>
				<Pagination.Content>
					<Pagination.Item>
						<a
							href={'?' + buildQuery({ page: Math.max(1, data.page - 1) })}
							aria-label="Page precedente"
							class="rounded-xl px-3 py-2 hover:bg-muted"
							aria-disabled={data.page === 1}
						>
							Precedent
						</a>
					</Pagination.Item>

					{#each Array(data.pageCount) as _, i}
						{#if Math.abs(i + 1 - data.page) <= 2 || i === 0 || i + 1 === data.pageCount}
							<Pagination.Item>
								<a
									href={'?' + buildQuery({ page: i + 1 })}
									class="rounded-xl px-3 py-2 hover:bg-muted {i + 1 === data.page
										? 'bg-primary text-primary-foreground'
										: ''}"
									aria-current={i + 1 === data.page ? 'page' : undefined}
								>
									{i + 1}
								</a>
							</Pagination.Item>
						{:else if (i === 1 && data.page > 3) || (i === data.pageCount - 2 && data.page < data.pageCount - 2)}
							<Pagination.Ellipsis />
						{/if}
					{/each}

					<Pagination.Item>
						<a
							href={'?' + buildQuery({ page: Math.min(data.pageCount, data.page + 1) })}
							aria-label="Page suivante"
							class="rounded-xl px-3 py-2 hover:bg-muted"
							aria-disabled={data.page === data.pageCount}
						>
							Suivant
						</a>
					</Pagination.Item>
				</Pagination.Content>
			</Pagination.Root>
		</section>
	{/if}
</div>

{#if editingMatch}
	<div class="fixed inset-0 z-50 grid place-items-center p-4">
		<button
			type="button"
			class="absolute inset-0 bg-black/45 backdrop-blur-[1px]"
			aria-label="Fermer la fenetre d'edition"
			onclick={closeEditModal}
		></button>

		<div
			role="dialog"
			aria-modal="true"
			aria-labelledby="edit-match-title"
			class="relative w-full max-w-sm rounded-2xl border border-border bg-card p-4 shadow-[0_22px_50px_rgba(0,0,0,0.35)]"
		>
			<div class="mb-4 flex items-start justify-between gap-3">
				<div>
					<h3 id="edit-match-title" class="text-base font-semibold">
						Editer le match #{editingMatch.id}
					</h3>
					<p class="text-xs text-muted-foreground">
						{dayLabel(editingMatch.game_timestamp)} a {toTime(editingMatch.game_timestamp)}
					</p>
				</div>

				<button
					type="button"
					class="rounded-lg p-1.5 text-muted-foreground transition hover:bg-secondary hover:text-foreground"
					aria-label="Fermer"
					onclick={closeEditModal}
					disabled={savingEdit}
				>
					✕
				</button>
			</div>

			<form class="space-y-4" onsubmit={handleSaveEdit}>
				<div class="grid grid-cols-2 gap-3">
					<label class="space-y-1">
						<span class="text-[11px] uppercase tracking-[0.12em] text-muted-foreground"
							>Equipe 1</span
						>
						<Input
							type="number"
							min="0"
							step="1"
							bind:value={editTeam1Score}
							required
							disabled={savingEdit}
						/>
					</label>
					<label class="space-y-1">
						<span class="text-[11px] uppercase tracking-[0.12em] text-muted-foreground"
							>Equipe 2</span
						>
						<Input
							type="number"
							min="0"
							step="1"
							bind:value={editTeam2Score}
							required
							disabled={savingEdit}
						/>
					</label>
				</div>

				<div class="flex items-center justify-end gap-2">
					<Button type="button" variant="ghost" onclick={closeEditModal} disabled={savingEdit}>
						Annuler
					</Button>
					<Button type="submit" disabled={savingEdit}>
						{savingEdit ? 'Enregistrement...' : 'Enregistrer'}
					</Button>
				</div>
			</form>
		</div>
	</div>
{/if}
