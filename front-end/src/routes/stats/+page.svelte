<script>
    import { Card, CardHeader, CardContent } from '$lib/components/ui/card';
    const stats = [
        { title: 'Total Matches', value: 42 },
        { title: 'Average Score', value: '5.2' },
        // Add more stats as needed
    ];
</script>

<section class="p-8">
    <h2 class="text-3xl font-semibold mb-6">Statistics</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 h-">
        {#each stats as stat}
            <Card>
                <CardHeader>{stat.title}</CardHeader>
                <CardContent>{stat.value}</CardContent>
            </Card>
        {/each}
    </div>
</section>



