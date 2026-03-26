<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import { cn } from "$lib/utils.js";

	type $$Props = HTMLAttributes<HTMLDivElement>;

	let className: $$Props["class"] = undefined;
	export { className as class };
</script>

<div
	class={cn("bg-card text-card-foreground rounded-2xl shadow-[0_20px_40px_rgba(12,15,16,0.06)]", className)}
	{...$$restProps}
>
	<slot />
</div>
