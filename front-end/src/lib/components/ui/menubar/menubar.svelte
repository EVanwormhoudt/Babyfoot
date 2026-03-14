<script lang="ts">
	import type { Snippet } from "svelte";
	import type { HTMLAttributes } from "svelte/elements";
	import { cn } from "$lib/utils.js";

	let {
		class: className,
		children,
		...restProps
	}: HTMLAttributes<HTMLDivElement> & { children?: Snippet } = $props();
</script>

<div
	class={cn("bg-background flex h-10 items-center space-x-1 rounded-md border p-1", className)}
	{...restProps}
>
	{@render children?.()}
</div>
