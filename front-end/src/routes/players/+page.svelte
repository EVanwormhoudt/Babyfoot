<script lang="ts">
    import {invalidateAll} from '$app/navigation';
    import {toast} from 'svelte-sonner';
    import {Button} from '$lib/components/ui/button';
    import {Input} from '$lib/components/ui/input';
    import {Label} from '$lib/components/ui/label';
    import * as Card from '$lib/components/ui/card';
    import {createPlayer, updatePlayer, type PlayerLite} from '$lib/api/players';
    import type {PageData} from './$types';

    let {data} = $props<{ data: PageData }>();

    function sortPlayers(players: PlayerLite[]): PlayerLite[] {
        return [...players].sort((a, b) => {
            const aActive = a.active !== false;
            const bActive = b.active !== false;
            if (aActive !== bActive) return aActive ? -1 : 1;
            return a.player_name.localeCompare(b.player_name, undefined, {sensitivity: 'base'});
        });
    }

    let players = $state(sortPlayers(data.players));
    $effect(() => {
        players = sortPlayers(data.players);
    });

    let newName = $state('');
    let newColor = $state('#22c55e');
    let creating = $state(false);

    let editingId = $state<number | null>(null);
    let editName = $state('');
    let editColor = $state('#22c55e');
    let editActive = $state(true);
    let savingId = $state<number | null>(null);

    function normalizeColor(value: string) {
        const c = value.trim();
        return c.length > 0 ? c : '#22c55e';
    }

    function swatchColor(value: string | undefined) {
        const c = (value ?? '').trim();
        return c.length > 0 ? c : '#94a3b8';
    }

    function startEdit(player: PlayerLite) {
        editingId = player.id;
        editName = player.player_name;
        editColor = player.player_color || '#22c55e';
        editActive = player.active !== false;
    }

    function cancelEdit() {
        editingId = null;
        editName = '';
        editColor = '#22c55e';
        editActive = true;
    }

    async function handleCreate(event: SubmitEvent) {
        event.preventDefault();
        const name = newName.trim();
        if (!name) {
            toast.error('Le nom du joueur est requis.');
            return;
        }

        creating = true;
        try {
            await createPlayer({
                player_name: name,
                player_color: normalizeColor(newColor)
            });
            toast.success('Joueur cree.');
            newName = '';
            newColor = '#22c55e';
            await invalidateAll();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Impossible de creer le joueur.');
        } finally {
            creating = false;
        }
    }

    async function saveEdit(playerId: number) {
        const name = editName.trim();
        if (!name) {
            toast.error('Le nom du joueur est requis.');
            return;
        }

        savingId = playerId;
        try {
            await updatePlayer(playerId, {
                player_name: name,
                player_color: normalizeColor(editColor),
                active: editActive
            });
            toast.success('Joueur mis a jour.');
            cancelEdit();
            await invalidateAll();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Impossible de mettre a jour le joueur.');
        } finally {
            savingId = null;
        }
    }
</script>

<section class="mx-auto max-w-[1400px] space-y-6 px-4 py-6">
    <div class="space-y-2">
        <p class="editorial-kicker">Gestion Joueurs</p>
        <h1 class="font-display text-4xl font-black uppercase leading-[0.95]">Players Studio</h1>
        <p class="text-sm text-muted-foreground">
            Ajoutez de nouveaux joueurs et modifiez les joueurs existants.
        </p>
    </div>

    <div class="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card.Root class="rounded-3xl bg-[hsl(var(--surface-container-low))]">
            <Card.Header class="pb-2">
                <Card.Title class="text-xl">Ajouter un joueur</Card.Title>
                <Card.Description>Nom + couleur visible dans les interfaces.</Card.Description>
            </Card.Header>
            <Card.Content>
                <form class="grid gap-4 sm:grid-cols-[1fr_180px_auto]" onsubmit={handleCreate}>
                    <label class="space-y-2">
                        <Label for="new-player-name">Nom</Label>
                        <Input
                                id="new-player-name"
                                bind:value={newName}
                                placeholder="Ex: Elliot"
                                maxlength={40}
                        />
                    </label>

                    <label class="space-y-2">
                        <Label for="new-player-color">Couleur</Label>
                        <Input
                                id="new-player-color"
                                bind:value={newColor}
                                placeholder="#22c55e"
                        />
                    </label>

                    <div class="flex items-end">
                        <Button class="w-full sm:w-auto" disabled={creating} type="submit">
                            {creating ? 'Creation...' : 'Ajouter'}
                        </Button>
                    </div>
                </form>
            </Card.Content>
        </Card.Root>

        <Card.Root class="rounded-3xl bg-[hsl(var(--surface-container-low))]">
            <Card.Header class="pb-2">
                <Card.Title class="text-xl">Infos</Card.Title>
                <Card.Description>Le statut inactif retire un joueur des selections courantes.</Card.Description>
            </Card.Header>
            <Card.Content>
                <div class="text-sm text-muted-foreground">
                    {players.length} joueurs au total
                </div>
            </Card.Content>
        </Card.Root>
    </div>

    <Card.Root class="rounded-3xl bg-[hsl(var(--surface-container-low))]">
        <Card.Header class="pb-2">
            <Card.Title class="text-xl">Joueurs existants</Card.Title>
        </Card.Header>
        <Card.Content class="space-y-2">
            {#if data.loadError}
                <div class="rounded-xl bg-card p-4 text-sm text-destructive">{data.loadError}</div>
            {:else if players.length === 0}
                <div class="rounded-xl bg-card p-6 text-sm text-muted-foreground">Aucun joueur trouve.</div>
            {:else}
                {#each players as player (player.id)}
                    <div class="rounded-2xl border border-border/65 bg-card px-4 py-3">
                        {#if editingId === player.id}
                            <div class="grid gap-3 md:grid-cols-[1fr_180px_auto_auto_auto] md:items-end">
                                <label class="space-y-1.5">
                                    <Label for={`edit-name-${player.id}`}>Nom</Label>
                                    <Input id={`edit-name-${player.id}`} bind:value={editName}/>
                                </label>

                                <label class="space-y-1.5">
                                    <Label for={`edit-color-${player.id}`}>Couleur</Label>
                                    <Input id={`edit-color-${player.id}`} bind:value={editColor}/>
                                </label>

                                <label class="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-background px-3 text-sm">
                                    <input type="checkbox" bind:checked={editActive}/>
                                    <span>Actif</span>
                                </label>

                                <Button
                                        disabled={savingId === player.id}
                                        onclick={() => saveEdit(player.id)}
                                >
                                    {savingId === player.id ? 'Enregistrement...' : 'Sauver'}
                                </Button>
                                <Button variant="outline" onclick={cancelEdit}>Annuler</Button>
                            </div>
                        {:else}
                            <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px_120px_auto] md:items-center">
                                <div class="min-w-0">
                                    <p class="truncate text-sm font-semibold">{player.player_name}</p>
                                    <p class="text-xs text-muted-foreground">ID #{player.id}</p>
                                </div>

                                <div class="flex items-center gap-2">
                                    <span
                                            class="h-4 w-4 rounded-full border border-border/70"
                                            style={`background-color: ${swatchColor(player.player_color)}`}
                                    ></span>
                                    <span class="truncate text-xs text-muted-foreground">{player.player_color}</span>
                                </div>

                                <span class={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-semibold ${
                                    player.active !== false
                                        ? 'bg-primary/15 text-primary'
                                        : 'bg-muted text-muted-foreground'
                                }`}>
                                    {player.active !== false ? 'Actif' : 'Inactif'}
                                </span>

                                <div class="flex justify-end">
                                    <Button size="sm" variant="outline" onclick={() => startEdit(player)}>
                                        Modifier
                                    </Button>
                                </div>
                            </div>
                        {/if}
                    </div>
                {/each}
            {/if}
        </Card.Content>
    </Card.Root>
</section>
