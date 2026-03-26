<script lang="ts">
    import '../app.css';
    import {ModeWatcher, mode, toggleMode} from "mode-watcher";
    import {onDestroy, onMount} from "svelte";
    import Sun from "@lucide/svelte/icons/sun";
    import Moon from "@lucide/svelte/icons/moon";
    import {Toaster} from "$lib/components/ui/sonner";
    import {page} from '$app/state';
    import {getStoredCurrentPlayerId, setStoredCurrentPlayerId} from '$lib/current-player';

    type HeaderPlayer = {
        id: number;
        player_name: string;
        player_color: string;
        active?: boolean;
    };

    let {children, data} = $props<{
        data: { playersLite?: HeaderPlayer[] }
    }>();

    const navItems = [
        {href: '/', label: 'Accueil'},
        {href: '/leaderboard', label: 'Classement'},
        {href: '/matches', label: 'Matchs'},
        {href: '/create', label: 'Nouveau'},
        {href: '/players', label: 'Joueurs'},
        {href: '/stats', label: 'Statistiques'}
    ];

    const selectablePlayers = $derived(
        ((data.playersLite ?? []) as HeaderPlayer[])
            .filter((player: HeaderPlayer) => player.active !== false)
            .sort((a: HeaderPlayer, b: HeaderPlayer) => a.player_name.localeCompare(b.player_name, undefined, {sensitivity: 'base'}))
    );
    let mePlayerId = $state('');
    const mePlayer = $derived(
        selectablePlayers.find((player: HeaderPlayer) => String(player.id) === mePlayerId)
    );
    const statsHref = $derived(
        mePlayerId ? `/stats?player_id=${mePlayerId}` : '/stats'
    );


    function isActive(href: string) {
        const pathname = page.url.pathname;
        if (href === '/') return pathname === '/';
        return pathname === href || pathname.startsWith(`${href}/`);
    }

    function initials(name: string | undefined) {
        if (!name) return 'BF';
        const parts = name.trim().split(/\s+/).filter(Boolean);
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase();
    }

    function themeToggleLabel() {
        return mode.current === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre';
    }

    function onMeChange() {
        const parsed = Number(mePlayerId);
        if (!Number.isFinite(parsed) || parsed <= 0) return;
        setStoredCurrentPlayerId(parsed);
    }

    onMount(() => {
        if (selectablePlayers.length === 0) return;
        const storedId = getStoredCurrentPlayerId();
        const storedString = storedId ? String(storedId) : '';

        if (storedString && selectablePlayers.some((player: HeaderPlayer) => String(player.id) === storedString)) {
            mePlayerId = storedString;
            return;
        }

        mePlayerId = String(selectablePlayers[0].id);
        onMeChange();
    });

    let themeTransitionTimeout: ReturnType<typeof setTimeout> | null = null;

    function handleThemeToggle() {
        if (typeof document === 'undefined') {
            toggleMode();
            return;
        }

        const root = document.documentElement;
        root.classList.add('theme-switching');
        toggleMode();

        if (themeTransitionTimeout) {
            clearTimeout(themeTransitionTimeout);
        }

        themeTransitionTimeout = setTimeout(() => {
            root.classList.remove('theme-switching');
            themeTransitionTimeout = null;
        }, 280);
    }

    onDestroy(() => {
        if (themeTransitionTimeout) {
            clearTimeout(themeTransitionTimeout);
        }
    });
</script>



<header class="sticky top-0 z-40 bg-background/92 backdrop-blur">
    <div class="mx-auto max-w-[1400px] px-4 py-4">
        <nav class="panel-lift flex flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3">
            <div class="flex flex-wrap items-center gap-2">
                <a class="inline-flex items-center gap-2 rounded-xl px-2 py-1.5" href="/">
                    <span class="h-2.5 w-2.5 rounded-full bg-accent"></span>
                    <span class="font-display text-lg font-bold italic text-primary">BabyFoot MyDso</span>
                </a>
            </div>

            <div class="flex flex-wrap items-center gap-1">
                {#each navItems as item (item.href)}
                    <a
                            href={item.href === '/stats' ? statsHref : item.href}
                            class={`rounded-xl px-3 py-2 text-sm transition ${
                                isActive(item.href)
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-secondary-foreground hover:bg-secondary/70 hover:text-foreground'
                            }`}
                    >
                        {item.label}
                    </a>
                {/each}
            </div>

            <div class="flex items-center gap-2">
                {#if selectablePlayers.length > 0}
                    <label class="inline-flex items-center gap-2 rounded-xl bg-secondary/65 px-2 py-1.5">
                        <span class="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">Moi</span>
                        <select
                                bind:value={mePlayerId}
                                class="h-7 rounded-lg border border-border/70 bg-background px-2 text-xs text-foreground"
                                onchange={onMeChange}
                        >
                            {#each selectablePlayers as player}
                                <option value={String(player.id)}>{player.player_name}</option>
                            {/each}
                        </select>
                    </label>
                {/if}
                <button
                        type="button"
                        class="inline-flex h-9 items-center gap-2 rounded-xl border border-border bg-secondary/70 px-3 text-sm font-semibold text-secondary-foreground transition hover:bg-secondary"
                        onclick={handleThemeToggle}
                        aria-label={themeToggleLabel()}
                        title={themeToggleLabel()}
                >
                    {#if mode.current === 'dark'}
                        <Sun class="size-4"/>
                    {:else}
                        <Moon class="size-4"/>
                    {/if}
                </button>
                <a
                        href="/create"
                        class="inline-flex h-9 items-center rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-[0_10px_24px_rgba(0,107,36,0.24)]"
                >
                    Log Match
                </a>
                <div class="grid h-9 w-9 place-items-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">
                    {initials(mePlayer?.player_name ?? selectablePlayers[0]?.player_name)}
                </div>
            </div>
        </nav>
    </div>
</header>

<main class="w-full">
    {@render children()}
</main>



<Toaster position="top-center" richColors/>
<ModeWatcher />
