<script lang="ts">
    import {flip} from 'svelte/animate';
    import {dndzone} from 'svelte-dnd-action';
    import {Input} from '$lib/components/ui/input';
    import {Button} from '$lib/components/ui/button';
    import {Label} from "$lib/components/ui/label/index.js";
    import {PUBLIC_API_BASE} from "$env/static/public";
    import {toast} from "svelte-sonner";
    import * as Card from "$lib/components/ui/card/index.js";

    type PlayerLite = { id: number; player_name: string; player_color: string; active: boolean };
    type DndItem = { id: number; name: string; color?: string };

    // props (Svelte 5)
    let { data } = $props<{ data: { playersLite: PlayerLite[] } }>();
    const playersLite: PlayerLite[] = Array.isArray(data?.playersLite) ? data.playersLite : [];

    // Column IDs
    const COL_PLAYERS = 1;
    const COL_RED = 2;
    const COL_BLUE = 3;

    // DnD columns use $state so nested mutations are reactive
    let columnItems = $state<
        { id: number; name: string; class: string; items: DndItem[] }[]
    >([
        {
            id: COL_PLAYERS,
            name: "Joueurs",
            class: "players",
            items: playersLite
                .filter((p) => p.active)
                .map((p) => ({ id: p.id, name: p.player_name, color: p.player_color }))
        },
        { id: COL_RED, name: "Equipe rouge", class: "team-red", items: [] },
        { id: COL_BLUE, name: "Equipe bleue", class: "team-blue", items: [] }
    ]);

    // layout derived from current players pool (5 columns, 55px row height)
    const totalItems = $derived(columnItems[0].items.length);
    const rows = $derived(Math.max(1, Math.ceil(totalItems / 5)));
    const height = $derived(`${rows * 55}px`);

    const flipDurationMs = 180;
    const dropTargetStyle = {};
    const dropTargetStyleMain = {};
    const dropTargetClassesMain = ['ring-2', 'ring-emerald-400/70', 'bg-emerald-500/10'];
    const dropTargetClassesRed = ['ring-2', 'ring-red-400/70', 'bg-red-500/10'];
    const dropTargetClassesBlue = ['ring-2', 'ring-blue-400/70', 'bg-blue-500/10'];

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

    async function undoLastSubmission() {
        if (!lastGameId) {
            toast.error("Annulation impossible (aucun identifiant de match).");
            return;
        }
        try {
            toast.promise(
                (async () => {
                    const res = await fetch(`${GAMES_ENDPOINT}/${lastGameId}`, {method: "DELETE"});
                    if (!res.ok) {
                        const t = await res.text().catch(() => "");
                        throw new Error(t || `Echec de l'annulation (${res.status})`);
                    }
                })(),
                {
                    loading: "Annulation...",
                    success: "Enregistrement annule.",
                    error: (e: unknown) => e instanceof Error ? e.message : "Echec de l'annulation."
                }
            );
            lastGameId = null;
        } catch { /* toast.promise handled error */
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
                    const text = await res.text().catch(() => "");
                    throw new Error(text || `La requete a echoue (${res.status})`);
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
    <Card.Root class="overflow-hidden rounded-3xl border border-emerald-500/20 bg-gradient-to-br from-emerald-950/15 via-background to-background/95 shadow-[0_18px_45px_rgba(0,0,0,0.25)]">
        <Card.Header class="relative pb-2">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.15),transparent_45%)]"></div>
            <div class="relative flex flex-wrap items-center justify-between gap-3">
                <div>
                    <Card.Title class="text-3xl font-black tracking-tight">Creer un match</Card.Title>
                    <Card.Description>Glissez les joueurs dans les equipes rouge et bleue, puis validez le score.</Card.Description>
                    <p class="mt-1 text-xs text-muted-foreground">Astuce : vous pouvez aussi reordonner les joueurs a l'interieur d'une equipe.</p>
                </div>
                <div class="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs font-medium text-muted-foreground">
                    {columnItems[0].items.length} joueurs disponibles
                </div>
            </div>
        </Card.Header>
        <Card.Content class="pt-2">
            <section
                    class="grid grid-cols-2 justify-items-center gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
                    use:dndzone={{
				items: columnItems[0].items,
				type: 'player',
					flipDurationMs,
					dropTargetStyle: dropTargetStyleMain,
					dropTargetClasses: dropTargetClassesMain,
					centreDraggedOnCursor: true,
					transformDraggedElement
				}}
                    onconsider={(e) => handleDndConsiderCards(columnItems[0].id, e)}
                    onfinalize={(e) => handleDndFinalizeCards(columnItems[0].id, e)}
                    style="height: {height};"
            >
                {#each columnItems[0].items as item (item.id)}
                    <div
                            animate:flip={{duration: flipDurationMs}}
                            class="relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl border border-emerald-500/30 bg-card/95 px-3 text-[15px] font-semibold text-foreground shadow-[0_6px_16px_rgba(0,0,0,0.2)] transition hover:border-emerald-400/70 hover:bg-emerald-500/12 active:cursor-grabbing"
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
                                    class="h-6 w-6 rounded-full bg-red-700 text-white text-[10px] font-semibold grid place-items-center shadow"
                                    title="Envoyer en rouge"
                                    onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                            >R</button>
                            <button
                                    class="h-6 w-6 rounded-full bg-blue-700 text-white text-[10px] font-semibold grid place-items-center shadow"
                                    title="Envoyer en bleu"
                                    onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                            >B</button>
                        </div>
                    </div>
                {/each}
            </section>
        </Card.Content>
    </Card.Root>

    <div class="grid items-start gap-4 xl:grid-cols-[1fr_420px_1fr]">
        {#each columnItems.slice(1, 2) as column (column.id)}
            <Card.Root class="rounded-3xl border border-red-500/25 bg-gradient-to-b from-red-950/20 to-background">
                <Card.Header class="pb-2">
                    <div class="flex items-center justify-between">
                        <Card.Title class="text-xl">Equipe rouge</Card.Title>
                        <span class="rounded-full border border-red-500/30 bg-red-500/10 px-2.5 py-0.5 text-xs text-red-200">
                            {column.items.length} joueurs
                        </span>
                    </div>
                </Card.Header>
                <Card.Content>
                    <div
                            class="grid content-start justify-items-center min-h-[220px] max-h-[440px] gap-2 overflow-y-auto rounded-xl border border-border/60 bg-background/60 p-2"
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
                                    class="relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl border border-red-500/30 bg-card/95 px-3 text-[15px] font-semibold text-foreground shadow-[0_6px_16px_rgba(0,0,0,0.2)] transition hover:border-blue-500/55 hover:bg-blue-500/12 active:cursor-grabbing"
                            >
                                <div class="flex h-full items-center justify-between gap-2">
                                    <div class="flex min-w-0 items-center gap-2">
                                        <span class="truncate">{item.name}</span>
                                    </div>
                                    <span class="text-muted-foreground">⠿</span>
                                </div>

                                <div class="absolute inset-y-0 right-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
                                    <button
                                            class="h-6 w-6 rounded-full bg-blue-700 text-white text-[10px] font-semibold grid place-items-center shadow"
                                            title="Deplacer en bleu"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                                    >B</button>
                                    <button
                                            class="h-6 w-6 rounded-full bg-neutral-700 text-white text-[10px] font-semibold grid place-items-center shadow"
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

            <Card.Root class="rounded-3xl border border-emerald-500/25 bg-gradient-to-b from-emerald-950/18 to-background">
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
                <Button class="h-11 min-w-[170px] rounded-xl bg-emerald-500 text-black font-semibold hover:bg-emerald-400" onclick={submitScore} disabled={submitting}>
                    {submitting ? 'Envoi...' : 'Envoyer le score'}
                </Button>
            </Card.Footer>
        </Card.Root>

        {#each columnItems.slice(2, 3) as column (column.id)}
            <Card.Root class="rounded-3xl border border-blue-500/25 bg-gradient-to-b from-blue-950/20 to-background">
                <Card.Header class="pb-2">
                    <div class="flex items-center justify-between">
                        <Card.Title class="text-xl">Equipe bleue</Card.Title>
                        <span class="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-0.5 text-xs text-blue-200">
                            {column.items.length} joueurs
                        </span>
                    </div>
                </Card.Header>
                <Card.Content>
                    <div
                            class="grid content-start justify-items-center min-h-[220px] max-h-[440px] gap-2 overflow-y-auto rounded-xl border border-border/60 bg-background/60 p-2"
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
                                    class="relative group h-12 w-full max-w-[210px] cursor-grab select-none rounded-xl border border-blue-500/30 bg-card/95 px-3 text-[15px] font-semibold text-foreground shadow-[0_6px_16px_rgba(0,0,0,0.2)] transition hover:border-red-500/55 hover:bg-red-500/12 active:cursor-grabbing"
                            >
                                <div class="flex h-full items-center justify-between gap-2">
                                    <div class="flex min-w-0 items-center gap-2">
                                        <span class="truncate">{item.name}</span>
                                    </div>
                                    <span class="text-muted-foreground">⠿</span>
                                </div>

                                <div class="absolute inset-y-0 right-2 flex items-center gap-1 opacity-0 transition group-hover:opacity-100">
                                    <button
                                            class="h-6 w-6 rounded-full bg-red-700 text-white text-[10px] font-semibold grid place-items-center shadow"
                                            title="Deplacer en rouge"
                                            onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                                    >R</button>
                                    <button
                                            class="h-6 w-6 rounded-full bg-neutral-700 text-white text-[10px] font-semibold grid place-items-center shadow"
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
    .create-match section {
        overflow: auto;
    }
</style>
