<script lang="ts">
    import {flip} from 'svelte/animate';
    import {dndzone} from 'svelte-dnd-action';
    import {onMount} from 'svelte';
    import {Input} from '$lib/components/ui/input';
    import {Button} from '$lib/components/ui/button';
    import {Label} from "$lib/components/ui/label/index.js";
    import {PUBLIC_API_BASE} from "$env/static/public";
    import {toast} from "svelte-sonner";
    import * as Card from "$lib/components/ui/card/index.js";
    import {getStoredCurrentPlayerId, onCurrentPlayerChange} from '$lib/current-player';

    type PlayerLite = {
        id: number;
        player_name: string;
        player_color: string;
        active: boolean;
    };
    type DndItem = {
        id: number;
        name: string;
        color?: string;
    };

    // props (Svelte 5)
    let { data } = $props<{ data: { playersLite: PlayerLite[] } }>();
    const playersLite: PlayerLite[] = Array.isArray(data?.playersLite) ? data.playersLite : [];

    // Column IDs
    const COL_PLAYERS = 1;
    const COL_RED = 2;
    const COL_BLUE = 3;
    let currentPlayerId = $state<number | null>(null);

    function normalizeItem(player: PlayerLite): DndItem {
        return {
            id: player.id,
            name: player.player_name,
            color: player.player_color
        };
    }

    function sortByName(a: DndItem, b: DndItem) {
        return a.name.localeCompare(b.name, undefined, {sensitivity: 'base'});
    }

    function isCurrentPlayer(item: DndItem) {
        return currentPlayerId !== null && item.id === currentPlayerId;
    }

    // DnD columns use $state so nested mutations are reactive
    let columnItems = $state<
        { id: number; name: string; class: string; items: DndItem[] }[]
    >([
        {
            id: COL_PLAYERS,
            name: "Joueurs disponibles",
            class: "players",
            items: playersLite
                .filter((p) => p.active)
                .map(normalizeItem)
                .sort(sortByName)
        },
        { id: COL_RED, name: "Equipe rouge", class: "team-red", items: [] },
        { id: COL_BLUE, name: "Equipe bleue", class: "team-blue", items: [] }
    ]);

    const availablePool = $derived(columnItems.find((c) => c.id === COL_PLAYERS));
    const availableItems = $derived(availablePool?.items ?? []);
    const totalAvailable = $derived(availableItems.length);

    // layout derived from each pool (5 columns, 55px row height)
    const availableRows = $derived(Math.max(1, Math.ceil(availableItems.length / 5)));
    const availableHeight = $derived(`${availableRows * 55}px`);

    const flipDurationMs = 180;
    const dropTargetStyle = {};
    const dropTargetStyleMain = {};
    const dropTargetClassesMain = ['ring-2', 'ring-[hsl(var(--primary)/0.6)]', 'bg-[hsl(var(--primary-container)/0.38)]'];
    const dropTargetClassesRed = ['ring-2', 'ring-[hsl(var(--team-red)/0.65)]', 'bg-[hsl(var(--team-red-soft)/0.85)]'];
    const dropTargetClassesBlue = ['ring-2', 'ring-[hsl(var(--team-blue)/0.65)]', 'bg-[hsl(var(--team-blue-soft)/0.85)]'];

    function transformDraggedElement(el?: HTMLElement) {
        if (!el) return;
        el.style.background = 'hsl(var(--background))';
        el.style.color = 'hsl(var(--foreground))';
        el.style.border = '1px solid rgba(16,185,129,0.55)';
        el.style.borderRadius = '0.75rem';
        el.style.boxShadow = '0 14px 34px rgba(0, 0, 0, 0.28)';
        el.style.cursor = 'grabbing';
        el.style.transform = 'scale(1.02)';
    }

    function handleDndConsiderCards(cid: number, e: CustomEvent<{ items: DndItem[] }>) {
        if (!e?.detail?.items) return;
        const col = columnItems.find(c => c.id === cid);
        if (!col) return;
        col.items = e.detail.items;
    }

    function handleDndFinalizeCards(cid: number, e: CustomEvent<{ items: DndItem[] }>) {
        if (!e?.detail?.items) return;
        const col = columnItems.find(c => c.id === cid);
        if (!col) return;
        col.items = e.detail.items;
    }

    // Quick-move helpers
    function moveItemToColumn(itemId: number, targetColId: number) {
        let found: DndItem | undefined;

        // remove from current column
        for (const col of columnItems) {
            const idx = col.items.findIndex((i) => i.id === itemId);
            if (idx !== -1) {
                [found] = col.items.splice(idx, 1);
                break;
            }
        }
        if (!found) return;

        // add to target column (avoid duplicates)
        const target = columnItems.find((c) => c.id === targetColId);
        if (!target) return;
        if (!target.items.some((i) => i.id === found!.id)) {
            target.items = [...target.items, found!];
        }
    }

    // prevent click from triggering drag
    function withNoDrag(fn: () => void) {
        return (e: MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            fn();
        };
    }


    // scores as $state so updates are reactive
    let redScore = $state<number | ''>('');
    let blueScore = $state<number | ''>('');

    // backend payload types
    type TeamCreatePayload = { player_id: number; team_number: 1 | 2 };
    type GameCreatePayload = { result_team1: number; result_team2: number; teams: TeamCreatePayload[] };

    // endpoint base (public, browser-safe)
    const API_BASE = $derived((PUBLIC_API_BASE ?? '').replace(/\/$/, ''));
    const GAMES_ENDPOINT = $derived(`${API_BASE}/api/games`);

    let submitting = $state(false);
    let lastGameId = $state<number | null>(null);

    onMount(() => {
        currentPlayerId = getStoredCurrentPlayerId();
        return onCurrentPlayerChange((playerId) => {
            currentPlayerId = playerId;
        });
    });

    async function readApiError(res: Response, fallback: string): Promise<string> {
        try {
            const body = await res.json();
            if (typeof body?.detail === "string" && body.detail.trim()) return body.detail;
        } catch {
            // ignore non-JSON payloads
        }
        try {
            const text = await res.text();
            if (text.trim()) return text;
        } catch {
            // ignore empty/unreadable body
        }
        return fallback;
    }

    async function undoLastSubmission() {
        if (!lastGameId) {
            toast.error("Annulation impossible (aucun identifiant de match).");
            return;
        }
        const gameIdToCancel = lastGameId;
        const cancelPromise = (async () => {
            const res = await fetch(`${GAMES_ENDPOINT}/${gameIdToCancel}`, {method: "DELETE"});
            if (!res.ok) {
                const msg = await readApiError(res, `Echec de l'annulation (${res.status})`);
                throw new Error(msg);
            }
        })();

        toast.promise(cancelPromise, {
            loading: "Annulation...",
            success: "Enregistrement annule.",
            error: (e: unknown) => e instanceof Error ? e.message : "Echec de l'annulation."
        });

        try {
            await cancelPromise;
            if (lastGameId === gameIdToCancel) {
                lastGameId = null;
            }
        } catch {
            // toast.promise already handled error message
        }
    }


    async function submitScore() {
        const r = typeof redScore === 'number' ? redScore : Number(redScore);
        const b = typeof blueScore === 'number' ? blueScore : Number(blueScore);
        if (!Number.isFinite(r) || !Number.isFinite(b)) {
            toast.error("Veuillez entrer des scores numeriques.");
            return;
        }

        const redCol = columnItems.find(c => c.id === COL_RED);
        const blueCol = columnItems.find(c => c.id === COL_BLUE);
        if (!redCol || !blueCol) {
            toast.error('Les equipes ne sont pas initialisees.');
            return;
        }

        const redEmpty = redCol.items.length === 0;
        const blueEmpty = blueCol.items.length === 0;
        if (redEmpty && blueEmpty) {
            toast.error('Les deux equipes sont vides. Ajoutez des joueurs en rouge et en bleu.');
            return;
        }
        if (redEmpty) {
            toast.error("L'equipe rouge est vide. Glissez un joueur ou utilisez les actions rapides.");
            return;
        }
        if (blueEmpty) {
            toast.error("L'equipe bleue est vide. Glissez un joueur ou utilisez les actions rapides.");
            return;
        }
        if (r === b) {
            toast.error('Les scores ne peuvent pas etre egaux.');
            return;
        }
        if (r < 0 || b < 0) {
            toast.error('Les scores ne peuvent pas etre negatifs.');
            return;
        }

        const teams: TeamCreatePayload[] = [
            ...redCol.items.map(i => ({player_id: i.id, team_number: 1 as const})),
            ...blueCol.items.map(i => ({player_id: i.id, team_number: 2 as const}))
        ];
        const payload: GameCreatePayload = { result_team1: r, result_team2: b, teams };

        submitting = true;
        try {
            const data = await (async () => {
                const res = await fetch(GAMES_ENDPOINT, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const msg = await readApiError(res, `La requete a echoue (${res.status})`);
                    throw new Error(msg);
                }
                return await res.json().catch(() => ({}));
            })();

            // Show success with Undo action
            lastGameId = Number.isFinite(Number(data?.id)) ? Number(data.id) : null;
            toast.success(lastGameId ? `Match #${lastGameId} enregistre !` : "Match enregistre !", {
                action: {
                    label: "Annuler",
                    onClick: () => void undoLastSubmission()
                },
                // keep the toast visible a bit longer for undo
                duration: 8000
            });

        } catch (err: any) {
            toast.error(err?.message || "Impossible d'enregistrer le match.");
        } finally {
            submitting = false;
        }
    }
</script>

<div class="create-match mx-auto max-w-[1400px] space-y-6 px-4 py-4">
    <Card.Root class="create-card create-hero overflow-hidden rounded-3xl">
        <Card.Header class="relative pb-2">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.1),transparent_50%)] dark:bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.12),transparent_48%)]"></div>
            <div class="relative flex flex-wrap items-center justify-between gap-3">
                <div>
                    <Card.Title class="text-3xl font-black tracking-tight">Creer un match</Card.Title>
                    <Card.Description>Glissez les joueurs dans les equipes rouge et bleue, puis validez le score.</Card.Description>
                    <p class="mt-1 text-xs text-muted-foreground">Astuce : vous pouvez aussi reordonner les joueurs a l'interieur d'une equipe.</p>
                </div>
                <div class="rounded-full border border-border/85 bg-background/75 px-3 py-1 text-xs font-medium text-muted-foreground">
                    {totalAvailable} joueurs disponibles
                </div>
            </div>
        </Card.Header>
        <Card.Content class="space-y-4 pt-2">
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <p class="editorial-kicker">Joueurs disponibles</p>
                    <span class="rounded-full bg-card px-2.5 py-0.5 text-xs text-muted-foreground">
                        {availableItems.length}
                    </span>
                </div>
                <section
                        class="available-list grid grid-cols-2 justify-items-center gap-2 rounded-2xl p-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
                        use:dndzone={{
				items: availableItems,
				type: 'player',
					flipDurationMs,
					dropTargetStyle: dropTargetStyleMain,
					dropTargetClasses: dropTargetClassesMain,
					centreDraggedOnCursor: true,
					transformDraggedElement
				}}
                        onconsider={(e) => handleDndConsiderCards(COL_PLAYERS, e)}
                        onfinalize={(e) => handleDndFinalizeCards(COL_PLAYERS, e)}
                        style="height: {availableHeight};"
                >
                    {#each availableItems as item (item.id)}
                        <div
                                animate:flip={{duration: flipDurationMs}}
                                class={`player-chip relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl px-3 text-[15px] font-semibold text-foreground transition hover:border-primary/55 hover:bg-primary/10 active:cursor-grabbing ${isCurrentPlayer(item) ? 'whoami-chip' : ''}`}
                                title={item.name}
                        >
                            <div class="flex h-full items-center justify-between gap-2">
                                <div class="flex min-w-0 items-center gap-2">
                                    <span class="truncate">{item.name}</span>
                                </div>
                                <span class="text-muted-foreground">⠿</span>
                            </div>

                            <div class="absolute inset-y-0 right-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
                                <button
                                        class="tag-action tag-action-red"
                                        title="Envoyer en rouge"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                                >R</button>
                                <button
                                        class="tag-action tag-action-blue"
                                        title="Envoyer en bleu"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                                >B</button>
                            </div>
                        </div>
                    {/each}
                </section>
            </div>
        </Card.Content>
    </Card.Root>

    <div class="grid items-start gap-4 xl:grid-cols-[1fr_420px_1fr]">
        {#each columnItems.filter((c) => c.id === COL_RED) as column (column.id)}
            <Card.Root class="create-card create-team create-team-red rounded-3xl">
                <Card.Header class="pb-2">
                    <div class="flex items-center justify-between">
                        <Card.Title class="text-xl">Equipe rouge</Card.Title>
                        <span class="tone-team-red rounded-full px-2.5 py-0.5 text-xs">
                            {column.items.length} joueurs
                        </span>
                    </div>
                </Card.Header>
                <Card.Content>
                    <div
                            class="team-zone team-zone-red grid content-start justify-items-center min-h-[220px] max-h-[440px] gap-2 overflow-y-auto rounded-2xl p-2"
                            use:dndzone={{
							items: column.items,
							type: 'player',
							flipDurationMs,
							dropTargetStyle,
							dropTargetClasses: dropTargetClassesRed,
							centreDraggedOnCursor: true,
							transformDraggedElement
						}}
                            onconsider={(e) => handleDndConsiderCards(column.id, e)}
                            onfinalize={(e) => handleDndFinalizeCards(column.id, e)}
                    >
                        {#each column.items as item (item.id)}
                            <div
                                    animate:flip={{duration: flipDurationMs}}
                                    class={`team-chip team-chip-red relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl px-3 text-[15px] font-semibold text-foreground transition hover:border-[hsl(var(--team-blue)/0.45)] hover:bg-[hsl(var(--team-blue-soft)/0.62)] active:cursor-grabbing ${isCurrentPlayer(item) ? 'whoami-chip' : ''}`}
                            >
                                <div class="flex h-full items-center justify-between gap-2">
                                    <div class="flex min-w-0 items-center gap-2">
                                        <span class="truncate">{item.name}</span>
                                    </div>
                                    <span class="text-muted-foreground">⠿</span>
                                </div>

                                <div class="absolute inset-y-0 right-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
                                    <button
                                            class="tag-action tag-action-blue"
                                            title="Deplacer en bleu"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                                    >B</button>
                                    <button
                                            class="tag-action tag-action-neutral"
                                            title="Retour aux joueurs"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_PLAYERS))}
                                    >X</button>
                                </div>
                            </div>
                        {/each}
                    </div>
                </Card.Content>
            </Card.Root>
        {/each}

            <Card.Root class="create-card create-score rounded-3xl">
                <Card.Header>
                    <Card.Title class="text-xl">Valider le score</Card.Title>
                    <Card.Description>Entrez le score final des deux equipes.</Card.Description>
                </Card.Header>
                <Card.Content>
                    <div class="grid grid-cols-[1fr_auto_1fr] items-end gap-4">
                        <div class="space-y-2 text-center">
                            <Label class="text-foreground/90" for="redScore">Score rouge</Label>
                            <Input id="redScore" type="number" bind:value={redScore} class="h-12 text-center text-lg font-semibold" placeholder="0" max={10} min={0}/>
                        </div>
                    <div class="pb-3 text-sm font-semibold uppercase tracking-[0.16em] text-muted-foreground">VS</div>
                    <div class="space-y-2 text-center">
                        <Label class="text-foreground/90" for="blueScore">Score bleu</Label>
                        <Input id="blueScore" type="number" bind:value={blueScore} class="h-12 text-center text-lg font-semibold" placeholder="0" max={10} min={0}/>
                    </div>
                </div>
            </Card.Content>
            <Card.Footer class="flex flex-col items-center gap-2 pt-0">
                <Button class="h-11 min-w-[170px] rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90" onclick={submitScore} disabled={submitting}>
                    {submitting ? 'Envoi...' : 'Envoyer le score'}
                </Button>
            </Card.Footer>
        </Card.Root>

        {#each columnItems.filter((c) => c.id === COL_BLUE) as column (column.id)}
            <Card.Root class="create-card create-team create-team-blue rounded-3xl">
                <Card.Header class="pb-2">
                    <div class="flex items-center justify-between">
                        <Card.Title class="text-xl">Equipe bleue</Card.Title>
                        <span class="tone-team-blue rounded-full px-2.5 py-0.5 text-xs">
                            {column.items.length} joueurs
                        </span>
                    </div>
                </Card.Header>
                <Card.Content>
                    <div
                            class="team-zone team-zone-blue grid content-start justify-items-center min-h-[220px] max-h-[440px] gap-2 overflow-y-auto rounded-2xl p-2"
                            use:dndzone={{
							items: column.items,
							type: 'player',
							flipDurationMs,
							dropTargetStyle,
							dropTargetClasses: dropTargetClassesBlue,
							centreDraggedOnCursor: true,
							transformDraggedElement
						}}
                            onconsider={(e) => handleDndConsiderCards(column.id, e)}
                            onfinalize={(e) => handleDndFinalizeCards(column.id, e)}
                    >
                        {#each column.items as item (item.id)}
                            <div
                                    animate:flip={{duration: flipDurationMs}}
                                    class={`team-chip team-chip-blue relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl px-3 text-[15px] font-semibold text-foreground transition hover:border-[hsl(var(--team-red)/0.45)] hover:bg-[hsl(var(--team-red-soft)/0.62)] active:cursor-grabbing ${isCurrentPlayer(item) ? 'whoami-chip' : ''}`}
                            >
                                <div class="flex h-full items-center justify-between gap-2">
                                    <div class="flex min-w-0 items-center gap-2">
                                        <span class="truncate">{item.name}</span>
                                    </div>
                                    <span class="text-muted-foreground">⠿</span>
                                </div>

                                <div class="absolute inset-y-0 right-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
                                    <button
                                            class="tag-action tag-action-red"
                                            title="Deplacer en rouge"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                                    >R</button>
                                    <button
                                            class="tag-action tag-action-neutral"
                                            title="Retour aux joueurs"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_PLAYERS))}
                                    >X</button>
                                </div>
                            </div>
                        {/each}
                    </div>
                </Card.Content>
            </Card.Root>
        {/each}
    </div>
</div>

<style>
    .create-match {
        position: relative;
    }

    :global(.create-card) {
        background: linear-gradient(180deg, hsl(var(--card)), hsl(var(--surface-container-low) / 0.7));
        border: 1px solid hsl(var(--border) / 0.95);
        box-shadow:
            0 1px 1px rgba(15, 23, 42, 0.05),
            0 18px 32px rgba(15, 23, 42, 0.1);
    }

    :global(.create-hero) {
        background:
            linear-gradient(180deg, hsl(var(--card)), hsl(var(--surface-container-low) / 0.72)),
            radial-gradient(circle at 94% 0%, hsl(var(--accent) / 0.05), transparent 44%);
    }

    :global(.create-team-red) {
        background:
            linear-gradient(180deg, hsl(var(--card)), hsl(var(--surface-container-low) / 0.72)),
            linear-gradient(140deg, hsl(var(--team-red-soft) / 0.28), transparent 48%);
    }

    :global(.create-team-blue) {
        background:
            linear-gradient(180deg, hsl(var(--card)), hsl(var(--surface-container-low) / 0.72)),
            linear-gradient(220deg, hsl(var(--team-blue-soft) / 0.28), transparent 48%);
    }

    :global(.create-score) {
        background:
            linear-gradient(180deg, hsl(var(--card)), hsl(var(--surface-container-low) / 0.72)),
            radial-gradient(circle at 50% -8%, hsl(var(--primary-container) / 0.15), transparent 56%);
    }

    .available-list {
        border: 1px solid hsl(var(--border) / 0.9);
        background: hsl(var(--background) / 0.82);
    }

    .team-zone {
        border: 1px solid hsl(var(--border) / 0.92);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
    }

    .team-zone-red {
        background: linear-gradient(180deg, hsl(var(--team-red-soft) / 0.42), hsl(var(--background) / 0.75));
    }

    .team-zone-blue {
        background: linear-gradient(180deg, hsl(var(--team-blue-soft) / 0.42), hsl(var(--background) / 0.75));
    }

    .player-chip,
    .team-chip {
        border: 1px solid hsl(var(--border) / 0.95);
        background: hsl(var(--card) / 0.96);
        box-shadow:
            0 1px 1px rgba(15, 23, 42, 0.06),
            0 7px 16px rgba(15, 23, 42, 0.1);
    }

    .team-chip-red {
        border-color: hsl(var(--team-red) / 0.38);
    }

    .team-chip-blue {
        border-color: hsl(var(--team-blue) / 0.38);
    }

    .whoami-chip {
        border-color: hsl(var(--primary) / 0.5);
        background:
            linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--primary-container) / 0.2));
        box-shadow:
            0 0 0 1px hsl(var(--primary) / 0.22),
            0 8px 18px rgba(15, 23, 42, 0.12);
    }

    .tag-action {
        height: 1.5rem;
        width: 1.5rem;
        border-radius: 9999px;
        border: 1px solid transparent;
        display: grid;
        place-items: center;
        font-size: 0.625rem;
        font-weight: 700;
        line-height: 1;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.16);
        transition: border-color 140ms ease, background-color 140ms ease, color 140ms ease, transform 140ms ease;
    }

    .tag-action:hover {
        transform: translateY(-1px);
    }

    .tag-action:focus-visible {
        outline: 2px solid hsl(var(--ring));
        outline-offset: 1px;
    }

    .tag-action-red {
        background: hsl(var(--team-red-soft) / 0.72);
        border-color: hsl(var(--team-red) / 0.34);
        color: hsl(var(--team-red));
    }

    .tag-action-red:hover {
        background: hsl(var(--team-red-soft) / 0.9);
        border-color: hsl(var(--team-red) / 0.5);
    }

    .tag-action-blue {
        background: hsl(var(--team-blue-soft) / 0.72);
        border-color: hsl(var(--team-blue) / 0.34);
        color: hsl(var(--team-blue));
    }

    .tag-action-blue:hover {
        background: hsl(var(--team-blue-soft) / 0.9);
        border-color: hsl(var(--team-blue) / 0.5);
    }

    .tag-action-neutral {
        background: hsl(var(--secondary) / 0.8);
        border-color: hsl(var(--border) / 0.9);
        color: hsl(var(--secondary-foreground));
    }

    .tag-action-neutral:hover {
        background: hsl(var(--secondary));
        border-color: hsl(var(--border));
    }

    .create-match section {
        overflow: auto;
    }
</style>
