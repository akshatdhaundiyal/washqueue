<script setup>
import { Waves, Disc } from 'lucide-vue-next'

const props = defineProps({
  activeTab: {
    type: String,
    required: true
  },
  freeMachinesCount: {
    type: Number,
    default: 0
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:activeTab'])
</script>

<template>
  <div class="md:hidden fixed bottom-4 left-0 right-0 z-40 flex justify-center px-4 pointer-events-none">
    <div
      :class="[
        'p-1.5 rounded-full border flex items-center gap-1 shadow-xl backdrop-blur-md pointer-events-auto',
        darkMode ? 'bg-slate-900/90 border-slate-800 text-slate-300' : 'bg-white/95 border-slate-200/90 text-slate-700 shadow-slate-200/60'
      ]"
    >
      <button
        @click="emit('update:activeTab', 'home')"
        :class="[
          'px-5 py-2.5 rounded-full flex items-center gap-2 text-xs font-bold transition-all',
          activeTab === 'home'
            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
            : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
        ]"
      >
        <Waves class="w-4 h-4" />
        <span>Home</span>
      </button>

      <button
        @click="emit('update:activeTab', 'machines')"
        :class="[
          'px-5 py-2.5 rounded-full flex items-center gap-2 text-xs font-bold transition-all',
          activeTab === 'machines'
            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm'
            : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
        ]"
      >
        <Disc class="w-4 h-4" />
        <span>Appliances</span>
        <span
          v-if="freeMachinesCount > 0"
          :class="[
            'text-[10px] font-mono font-extrabold px-1.5 py-0.5 rounded-full tabular-nums',
            activeTab === 'machines'
              ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
              : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
          ]"
        >
          {{ freeMachinesCount }}
        </span>
      </button>
    </div>
  </div>
</template>
