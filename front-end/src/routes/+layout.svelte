<script lang="ts">
    import { Menubar, MenubarMenu, MenubarTrigger, MenubarContent } from '$lib/components/ui/menubar';
    import '../app.css';
    let { children } = $props();
    import { ModeWatcher } from "mode-watcher";
</script>





<div class="flex justify-center py-4 border-b">
    <Menubar class="flex gap-4 ">
        <a href="/" class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black">Home</a>
        <a href="/leaderboard" class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black">Leaderboard</a>
        <a href="/create" class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black">Create Match</a>
        <a href="/stats" class="px-4 py-2 hover:bg-primary rounded-md transition hover:text-black">Stats</a>
    </Menubar>
</div>

<ModeWatcher />



{@render children()}
