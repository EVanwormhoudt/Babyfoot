<script lang="ts">
    import { dndzone } from 'svelte-dnd-action';
    import { Input } from '$lib/components/ui/input';
    import { Button } from '$lib/components/ui/button';
    import * as Card from "$lib/components/ui/card/index.js";
    import { Label } from "$lib/components/ui/label/index.js";
    import { PUBLIC_API_BASE } from "$env/static/public";
    import { toast } from "svelte-sonner";

    type PlayerLite = { id: number; player_name: string; player_color: string; active: boolean };
    type DndItem = { id: number; name: string; color?: string };

    // props (Svelte 5)
    let { data } = $props<{ data: { playersLite: PlayerLite[] } }>();

    // players derived from props
    const players = $derived(Array.isArray(data?.playersLite) ? data.playersLite : []);

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
            items: players
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

    const flipDurationMs = 300;
    const dropTargetStyle = { outline: 'rgba(255, 255, 255, 0.5) solid 2px' };
    const dropTargetStyleMain = {};

    function transformDraggedElement(el: HTMLElement) {
        el.style.backgroundColor = '#e5e7eb';
        el.style.color = '#000';
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
    const API_URL = $derived(PUBLIC_API_BASE ?? '/api');

    let submitting = $state(false);

    async function submitScore() {
        const r = typeof redScore === 'number' ? redScore : Number(redScore);
        const b = typeof blueScore === 'number' ? blueScore : Number(blueScore);

        if (!Number.isFinite(r) || !Number.isFinite(b)) {
            toast.error("Please enter numeric scores.");
            return;
        }

        const redCol = columnItems.find(c => c.id === COL_RED);
        const blueCol = columnItems.find(c => c.id === COL_BLUE);
        if (!redCol || !blueCol) {
            toast.error('Teams not initialized.');
            return;
        }

        const redEmpty = redCol.items.length === 0;
        const blueEmpty = blueCol.items.length === 0;
        if (redEmpty && blueEmpty) {
            toast.error('Both teams are empty. Add players to Red and Blue.');
            return;
        }
        if (redEmpty) {
            toast.error('Red team is empty. Drag or quick-move a player.');
            return;
        }
        if (blueEmpty) {
            toast.error('Blue team is empty. Drag or quick-move a player.');
            return;
        }

        const teams: TeamCreatePayload[] = [
            ...redCol.items.map(i => ({ player_id: i.id, team_number: 1 })),
            ...blueCol.items.map(i => ({ player_id: i.id, team_number: 2 }))
        ];

        const payload: GameCreatePayload = { result_team1: r, result_team2: b, teams };

        submitting = true;
        try {
                toast.promise(
                (async () => {
                    const res = await fetch(`${API_URL}/api/games`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    if (!res.ok) {
                        const text = await res.text().catch(() => "");
                        throw new Error(text || `Request failed with ${res.status}`);
                    }
                    const data = await res.json().catch(() => null);
                    return data?.id ? `Game #${data.id} saved!` : "Game saved!";
                })(),
                {
                    loading: "Saving match…",
                    success: (msg) => msg,
                    error: (err) => err.message || "Failed to save game."
                }
            );
        } finally {
            submitting = false;
        }
    }
</script>

<div class="create-match">
    <!-- Players Pool -->
    <div class="p-6 rounded-md shadow-md text-center mb-6 bg-card margin-top">
        <h2 class="text-2xl font-bold text-white mb-4">Joueurs</h2>

        <section
                class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 justify-center auto-rows-fixed"
                use:dndzone={{
				items: columnItems[0].items,
				type: 'player',

				flipDurationMs,
				dropTargetStyle: dropTargetStyleMain,
				transformDraggedElement
			}}
                onconsider={(e) => handleDndConsiderCards(columnItems[0].id, e)}
                onfinalize={(e) => handleDndFinalizeCards(columnItems[0].id, e)}
                style="height: {height};"
        >
            {#each columnItems[0].items as item (item.id)}
                <div
                        class="relative group border-2 border-gray-300 rounded-md px-3 py-2 text-gray-300 flex items-center justify-between cursor-grab shadow-sm hover:bg-gray-300 hover:text-black transition h-11 w-64"
                        title={item.name}
                >
                    <div class="flex items-center gap-2">

                        <span>{item.name}</span>
                    </div>

                    <!-- hover quick actions -->
                    <div class="absolute inset-0 flex items-center justify-end gap-2 pr-2 opacity-0 group-hover:opacity-100 transition pointer-events-none">
                        <button
                                class="pointer-events-auto h-7 w-7 rounded-full bg-red-900 text-white text-xs font-semibold grid place-items-center shadow"
                                title="Send to Red"
                                onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                        >R</button>
                        <button
                                class="pointer-events-auto h-7 w-7 rounded-full bg-blue-900 text-white text-xs font-semibold grid place-items-center shadow"
                                title="Send to Blue"
                                onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                        >B</button>
                    </div>

                    <span class="ml-2 text-gray-400">⠿</span>
                </div>
            {/each}
        </section>
    </div>

    <div class="flex flex-wrap gap-4 justify-center items-start">
        <!-- Red Team -->
        {#each columnItems.slice(1, 2) as column (column.id)}
            <section class="flex-1 team-red p-4 rounded-xl shadow-md min-h-[300px] max-w-[350px] bg-red-900/10">
                <div class="text-lg font-semibold mb-2 text-foreground">{column.name}</div>
                <div
                        class="flex flex-col gap-2 min-h-[200px] max-h-[200px] overflow-scroll"
                        use:dndzone={{
						items: column.items,
						type: 'player',

						flipDurationMs,
						dropTargetStyle,
						transformDraggedElement
					}}
                        onconsider={(e) => handleDndConsiderCards(column.id, e)}
                        onfinalize={(e) => handleDndFinalizeCards(column.id, e)}
                >
                    {#each column.items as item (item.id)}
                        <div class="relative group border-2 border-gray-300 rounded-md px-3 py-2 flex items-center justify-between cursor-grab shadow-sm hover:bg-gray-300 hover:text-black transition h-11 w-64">
                            <div class="flex items-center gap-2">

                                <span>{item.name}</span>
                            </div>

                            <div class="absolute inset-0 flex items-center justify-end gap-2 pr-2 opacity-0 group-hover:opacity-100 transition pointer-events-none">
                                <button
                                        class="pointer-events-auto h-7 w-7 rounded-full bg-blue-600 text-white text-xs font-semibold grid place-items-center shadow"
                                        title="Move to Blue"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_BLUE))}
                                >B</button>
                                <button
                                        class="pointer-events-auto h-7 w-7 rounded-full bg-neutral-700 text-white text-xs font-semibold grid place-items-center shadow"
                                        title="Back to Joueurs"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_PLAYERS))}
                                >X</button>
                            </div>

                            <span class="ml-2 text-gray-400">⠿</span>
                        </div>
                    {/each}
                </div>
            </section>
        {/each}

        <!-- Score Input Section -->
        <Card.Root class="w-[400px]">
            <Card.Header>
                <Card.Title>Submit Match Score</Card.Title>
                <Card.Description>Enter the scores for each team</Card.Description>
            </Card.Header>
            <Card.Content>
                <div class="flex justify-around gap-6">
                    <div class="flex flex-col items-center gap-y-2">
                        <Label for="redScore" class="text-foreground">Red Score</Label>
                        <Input id="redScore" type="number" bind:value={redScore} class="w-24" placeholder="0" max={10} min={0}/>
                    </div>
                    <div class="flex flex-col items-center">
                        <br />
                        <Label class="text-foreground">VS</Label>
                    </div>
                    <div class="flex flex-col items-center gap-y-2">
                        <Label for="blueScore" class="text-foreground">Blue Score</Label>
                        <Input id="blueScore" type="number" bind:value={blueScore} class="w-24" placeholder="0" max={10} min={0}/>
                    </div>
                </div>
            </Card.Content>
            <Card.Footer class="flex flex-col items-center gap-2">
                <Button onclick={submitScore} disabled={submitting}>
                    {submitting ? 'Sending…' : 'Send Score'}
                </Button>
            </Card.Footer>
        </Card.Root>

        <!-- Blue Team -->
        {#each columnItems.slice(2, 3) as column (column.id)}
            <div class="flex-1 team-blue p-4 rounded-xl shadow-md min-h-[300px] max-w-[350px] bg-blue-900/10">
                <div class="text-lg font-semibold mb-2 text-foreground">{column.name}</div>
                <div
                        class="flex flex-col gap-2 min-h-[200px] max-h-[200px] overflow-scroll"
                        use:dndzone={{
						items: column.items,
						type: 'player',

						flipDurationMs,
						dropTargetStyle,
						transformDraggedElement
					}}
                        onconsider={(e) => handleDndConsiderCards(column.id, e)}
                        onfinalize={(e) => handleDndFinalizeCards(column.id, e)}
                >
                    {#each column.items as item (item.id)}
                        <div class="relative group border-2 text-foreground border-gray-300 rounded-md px-3 py-2 flex items-center justify-between cursor-grab shadow-sm hover:bg-gray-300 hover:text-black transition h-11 w-64">
                            <div class="flex items-center gap-2">
                                
                                <span>{item.name}</span>
                            </div>

                            <div class="absolute inset-0 flex items-center justify-end gap-2 pr-2 opacity-0 group-hover:opacity-100 transition pointer-events-none">
                                <button
                                        class="pointer-events-auto h-7 w-7 rounded-full bg-red-600 text-white text-xs font-semibold grid place-items-center shadow"
                                        title="Move to Red"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_RED))}
                                >R</button>
                                <button
                                        class="pointer-events-auto h-7 w-7 rounded-full bg-neutral-700 text-white text-xs font-semibold grid place-items-center shadow"
                                        title="Back to Joueurs"
                                        onclick={withNoDrag(() => moveItemToColumn(item.id, COL_PLAYERS))}
                                >X</button>
                            </div>

                            <span class="ml-2 text-gray-400">⠿</span>
                        </div>
                    {/each}
                </div>
            </div>
        {/each}
    </div>
</div>

<style>
    .create-match { margin: 2%; }
    section { overflow: scroll; }
</style>
