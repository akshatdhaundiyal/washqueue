<script setup>
const props = defineProps({
  toasts: {
    type: Array,
    default: () => []
  }
})
</script>

<template>
  <div class="fixed bottom-6 right-6 z-50 space-y-2">
    <div 
      v-for="toast in toasts" 
      :key="toast.id"
      class="px-4 py-3 rounded-2xl text-xs font-mono font-bold shadow-2xl flex items-center gap-2.5 border animate-fadeIn"
      :class="{
        'bg-emerald-950/90 text-emerald-300 border-emerald-500/40': toast.type === 'success',
        'bg-rose-950/90 text-rose-300 border-rose-500/40': toast.type === 'error',
        'bg-zinc-900/95 text-zinc-200 border-white/10': toast.type === 'info'
      }"
    >
      <span v-if="toast.type === 'success'">✓</span>
      <span v-else-if="toast.type === 'error'">✕</span>
      <span v-else>ℹ</span>
      <span>{{ toast.message }}</span>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
