<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn } from "$lib/utils.js";

	type $$Props = HTMLAttributes<HTMLDivElement>;

	let className: $$Props["class"] = undefined;
	export { className as class };
</script>

<div
	class={cn("bg-card text-card-foreground rounded-2xl border border-border/90 shadow-[0_1px_1px_rgba(15,23,42,0.05),0_14px_30px_rgba(15,23,42,0.09)]", className)}
	{...$$restProps}
>
	<slot />
</div>
