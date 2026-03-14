<script lang="ts">
    import {Menubar} from '$lib/components/ui/menubar';
    import '../app.css';
    import {ModeWatcher} from "mode-watcher";
    import {Toaster} from "svelte-sonner";

    let { children } = $props<{
        data: { playersLite: { id: number; player_name: string; player_color: string }[] }
    }>();</script>





<div class="flex justify-center py-4 border-b">
    <Menubar class="flex gap-4 ">
        <a class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black" href="/">Acceuil</a>
        <a class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black" href="/leaderboard">Classement</a>
        <a class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black" href="/matches">Matchs</a>
        <a class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black" href="/create">Nouveau</a>
        <a class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black" href="/stats">Stats</a>
    </Menubar>
</div>


<ModeWatcher />

<Toaster position="top-center" theme="system" richColors />

{@render children()}
