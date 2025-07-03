

export const index = 3;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/telegram/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/3.7OQIuKhx.js","_app/immutable/chunks/lklm8csK.js","_app/immutable/chunks/IHki7fMi.js","_app/immutable/chunks/BZSLDrHE.js"];
export const stylesheets = ["_app/immutable/assets/3.BZo4SgxA.css"];
export const fonts = [];
