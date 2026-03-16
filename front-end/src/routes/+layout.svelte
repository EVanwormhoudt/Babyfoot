<script lang="ts">
    import '../app.css';
    import {ModeWatcher} from "mode-watcher";
    import {Toaster} from "svelte-sonner";
    import {page} from '$app/state';

    let {children} = $props<{
        data: { playersLite: { id: number; player_name: string; player_color: string }[] }
    }>();

    const navItems = [
        {href: '/', label: 'Accueil'},
        {href: '/leaderboard', label: 'Classement'},
        {href: '/matches', label: 'Matchs'},
        {href: '/create', label: 'Nouveau'},
        {href: '/stats', label: 'Stats'}
    ];

    function isActive(href: string) {
        const pathname = page.url.pathname;
        if (href === '/') return pathname === '/';
        return pathname === href || pathname.startsWith(`${href}/`);
    }
</script>

<header class="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur">
    <div class="mx-auto max-w-[1400px] px-4 py-3">
        <nav
                class="relative overflow-hidden rounded-2xl border border-emerald-500/20 bg-gradient-to-r from-emerald-950/20 via-background to-background/90 shadow-[0_8px_24px_rgba(0,0,0,0.18)]"
        >
            <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(16,185,129,0.14),transparent_46%)]"></div>
            <div class="relative flex flex-col gap-3 p-3 md:flex-row md:items-center md:justify-between">
                <a class="inline-flex items-center gap-2 rounded-xl px-3 py-2" href="/">
                    <span class="h-2.5 w-2.5 rounded-full bg-emerald-400"></span>
                    <span class="text-sm font-semibold tracking-tight">BabyFoot MyDSO</span>
                </a>

                <div class="flex flex-wrap items-center gap-1.5">
                    {#each navItems as item (item.href)}
                        <a
                                href={item.href}
                                class={`rounded-xl px-3 py-2 text-sm transition ${
                                    isActive(item.href)
                                        ? 'bg-emerald-500 text-black font-semibold shadow-sm'
                                        : 'text-foreground/80 hover:bg-emerald-500/10 hover:text-foreground'
                                }`}
                        >
                            {item.label}
                        </a>
                    {/each}
                </div>
            </div>
        </nav>
    </div>
</header>

<main class="w-full">
    {@render children()}
</main>

<Toaster position="top-center" theme="system" richColors/>
<ModeWatcher />
