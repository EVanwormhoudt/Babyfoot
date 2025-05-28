<script lang="ts">
    import { dndzone } from 'svelte-dnd-action';
    import { Input } from '$lib/components/ui/input';
    import { Button } from '$lib/components/ui/button';
    import * as Card from "$lib/components/ui/card/index.js";
    import * as Select from "$lib/components/ui/select/index.js";
    import { Label } from "$lib/components/ui/label/index.js";


    export let columnItems = [
        {
            id: 1,
            name: "Joueurs",
            class: "players",
            items: Array.from({ length: 30 }, (_, i) => ({ id: i + 41, name: `item${i + 41}` }))
        },
        {
            id: 2,
            name: "Equipe rouge",
            class: "team-red",
            items: []
        },
        {
            id: 3,
            name: "Equipe bleue",
            class: "team-blue",
            items: []
        }
    ];
    const totalItems = columnItems.reduce((acc, col) => acc + col.items.length, 0);

    // Apply the calculation: (total / 5) * 50
    const height = ((totalItems / 5) * 55)+ "px";


    let dropTargetStyle = {outline: 'rgba(255, 255, 255, 0.5) solid 2px'};
    let dropTargetStyleMain = {};

    let transformDraggedElement = (draggedElement:any) => {
        draggedElement.style.backgroundColor = '#e5e7eb';
        draggedElement.style.color = '#000';


    };

    const flipDurationMs = 300;

    function handleDndConsiderCards(cid: number, e: any) {
        const colIdx = columnItems.findIndex(c => c.id === cid);
        columnItems[colIdx].items = e.detail.items;
        columnItems = [...columnItems];
    }

    function handleDndFinalizeCards(cid: number, e: any) {
        const colIdx = columnItems.findIndex(c => c.id === cid);
        columnItems[colIdx].items = e.detail.items;
        columnItems = [...columnItems];
    }

    let redScore = '';
    let blueScore = '';

    function submitScore() {
        console.log(`Red Team: ${redScore}, Blue Team: ${blueScore}`);
    }
</script>
<div class="create-match">
<div class=" p-6 rounded-md shadow-md text-center mb-6 bg-card margin-top">
    <h2 class="text-2xl font-bold text-white mb-4">Joueurs</h2>
    <section class="grid  grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 justify-center  auto-rows-fixed"
            use:dndzone={{ items: columnItems[0].items, flipDurationMs,dropTargetStyle: dropTargetStyleMain, transformDraggedElement }}
            on:consider={(e) => handleDndConsiderCards(columnItems[0].id, e)}
            on:finalize={(e) => handleDndFinalizeCards(columnItems[0].id, e)}
            style="height: {height};"
    >
        {#each columnItems[0].items as item (item.id)}
            <div class="
            border-2 border-gray-300 rounded-md px-3 py-2
            text-gray-300
            flex items-center justify-between cursor-grab shadow-sm
            hover:bg-gray-300
            hover:text-black
             transition h-11 w-64">
                <span>{item.name}</span>
                <span class="ml-2 text-gray-400">⠿</span> <!-- Drag icon look -->
            </div>
        {/each}
        {#each Array(totalItems - columnItems[0].items.length) as _}
            <div class="invisible h-11 w-64"></div>
        {/each}
    </section>
</div>

    <div class="flex flex-wrap gap-4 justify-center items-center ">
        <!-- Red Team -->
        {#each columnItems.slice(1, 2) as column (column.id)}
            <section class="flex-1 team-red p-4 rounded-xl shadow-md min-h-[300px] max-w-[350px] bg-red-900/10">
                <div class="text-lg font-semibold mb-2 text-foreground">{column.name}</div>
                <div
                        class="flex flex-col gap-2 min-h-[200px] max-h-[200px] overflow-scroll"
                        use:dndzone={{ items: column.items, flipDurationMs, dropTargetStyle,transformDraggedElement }}
                        on:consider={(e) => handleDndConsiderCards(column.id, e)}
                        on:finalize={(e) => handleDndFinalizeCards(column.id, e)}
                >
                    {#each column.items as item (item.id)}
                        <div class="border-2 border-gray-300 rounded-md px-3 py-2 flex items-center justify-between cursor-grab shadow-sm hover:bg-gray-300 hover:text-black transition h-11 w-64">
                            <span>{item.name}</span>
                            <span class="ml-2 text-gray-400">⠿</span>
                        </div>
                    {/each}
                </div>
            </section>
        {/each}

        <!-- Score Input Section -->
        <Card.Root class="w-[400px]  ">
            <Card.Header >
                <Card.Title>Submit Match Score</Card.Title>
                <Card.Description>Enter the scores for each team</Card.Description>
            </Card.Header>
            <Card.Content>
                <div class="flex justify-around gap-6">
                    <div class="flex flex-col items-center gap-y-2">
                        <Label for="redScore" class="text-foreground">Red Score</Label>
                        <Input id="redScore" type="number" bind:value={redScore} class="w-24" placeholder="0" max=10 min=0/>
                    </div>
                    <div class="flex flex-col items-center">
                        <br />
                        <Label for="redScore" class="text-foreground">VS</Label>
                    </div>
                    <div class="flex flex-col items-center gap-y-2">
                        <Label for="blueScore" class="text-foreground">Blue Score</Label>
                        <Input id="blueScore" type="number" bind:value={blueScore} class="w-24" placeholder="0" max=10 min=0 />
                    </div>
                </div>
            </Card.Content>
            <Card.Footer class="flex justify-center">
                <Button on:click={submitScore}>Send Score</Button>
            </Card.Footer>
        </Card.Root>


        <!-- Blue Team -->
        {#each columnItems.slice(2, 3) as column (column.id)}
            <div class="flex-1 team-blue p-4 rounded-xl  shadow-md min-h-[300px]  max-w-[350px] bg-blue-900/10">
                <div class="text-lg font-semibold mb-2 text-foreground">{column.name}</div>
                <div
                        class="flex flex-col gap-2 min-h-[200px] max-h-[200px] overflow-scroll"
                        use:dndzone={{ items: column.items, flipDurationMs, dropTargetStyle,transformDraggedElement }}
                        on:consider={(e) => handleDndConsiderCards(column.id, e)}
                        on:finalize={(e) => handleDndFinalizeCards(column.id, e)}
                >
                    {#each column.items as item (item.id)}
                        <div class="border-2  text-foreground border-gray-300 rounded-md px-3 py-2 flex items-center justify-between cursor-grab shadow-sm hover:bg-gray-300 hover:text-black transition h-11 w-64">
                            <span>{item.name}</span>
                            <span class="ml-2 text-gray-400">⠿</span>
                        </div>
                    {/each}
                </div>
            </div>
        {/each}
    </div>


</div>

<style>

    .create-match {
        margin: 2%;

    }

    section {

        /* this will allow the dragged element to scroll the list although starting in version 0.9.41 the lib would detect any scrollable parent*/
        overflow: scroll;

    }

</style>