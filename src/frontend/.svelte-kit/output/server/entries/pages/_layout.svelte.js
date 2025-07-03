import { c as create_ssr_component } from "../../chunks/ssr.js";
const css = {
  code: "main.svelte-1pbmxs9{width:100%;min-height:100vh;background-color:var(--background-primary);color:var(--text-primary)}",
  map: `{"version":3,"file":"+layout.svelte","sources":["+layout.svelte"],"sourcesContent":["<script lang=\\"ts\\">\\n  import { onMount } from 'svelte';\\n  import '$lib/styles/global.css';\\n\\n  onMount(() => {\\n    // Initialize any global app state here\\n    console.log('🚀 GeopolMonitor SvelteKit app initialized');\\n  });\\n<\/script>\\n\\n<main>\\n  <slot />\\n</main>\\n\\n<style>\\n  main {\\n    width: 100%;\\n    min-height: 100vh;\\n    background-color: var(--background-primary);\\n    color: var(--text-primary);\\n  }\\n</style> "],"names":[],"mappings":"AAeE,mBAAK,CACH,KAAK,CAAE,IAAI,CACX,UAAU,CAAE,KAAK,CACjB,gBAAgB,CAAE,IAAI,oBAAoB,CAAC,CAC3C,KAAK,CAAE,IAAI,cAAc,CAC3B"}`
};
const Layout = create_ssr_component(($$result, $$props, $$bindings, slots) => {
  $$result.css.add(css);
  return `<main class="svelte-1pbmxs9">${slots.default ? slots.default({}) : ``} </main>`;
});
export {
  Layout as default
};
//# sourceMappingURL=_layout.svelte.js.map
