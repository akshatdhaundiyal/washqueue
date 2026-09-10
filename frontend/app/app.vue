<template>
  <div class="min-h-screen font-sans antialiased selection:bg-sky-500/20 selection:text-sky-900 dark:selection:text-sky-200">
    <NuxtPage />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,600&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,600&display=swap');

html, body {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

code, kbd, samp, pre, .font-mono, [data-mono] {
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
  font-feature-settings: "tnum" 1, "zero" 1;
  font-variant-numeric: tabular-nums;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
