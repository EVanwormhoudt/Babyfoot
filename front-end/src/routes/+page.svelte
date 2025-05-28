<script>
    import { Button } from '$lib/components/ui/button';
    
</script>

<section class="flex flex-col items-center justify-center h-screen text-center">
    <h1 class="text-5xl font-bold mb-6">Welcome to Foosball Arena</h1>
    <p class="mb-8 text-lg text-gray-600">Track matches, view leaderboards, and analyze stats.</p>
    <div class="space-x-4">
        <Button as="a" href="/create">Create Match</Button>
        <Button as="a" href="/leaderboard" variant="outline">View Leaderboard</Button>
    </div>
</section>