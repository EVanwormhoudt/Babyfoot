<script lang="ts">
	export let eyebrow: string;
	export let title: string;
	export let description: string;
</script>

<header class="club-page-header">
	<div class="club-page-header-copy">
		<p class="club-page-eyebrow"><span aria-hidden="true"></span> MYDSO / {eyebrow}</p>
		<h1>{title}</h1>
		<p class="club-page-description">{description}</p>
	</div>
	<div class="club-page-pitch" aria-hidden="true"><span></span></div>
</header>
