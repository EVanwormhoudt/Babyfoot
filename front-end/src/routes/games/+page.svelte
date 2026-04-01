<script lang="ts">
	import MatchesPage from '../matches/+page.svelte';
	import type { PageData } from './$types';

	export let data: PageData;
</script>

<MatchesPage {data} />
