<script setup>
import { Check, Waves, MessageSquare, ArrowUpRight, Activity, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  freeMachinesCount: {
    type: Number,
    default: 0
  },
  runningMachinesCount: {
    type: Number,
    default: 0
  },
  uncollectedCount: {
    type: Number,
    default: 0
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['navigate-filter', 'view-appliances'])
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
        Hostel Overview
      </h3>
      <button
        @click="emit('view-appliances')"
        class="text-xs font-bold text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300 hover:underline flex items-center gap-1"
      >
        <span>View Appliances</span>
        <ChevronRight class="w-3 h-3" />
      </button>
    </div>

    <!-- Summary Tiles (JetBrains Mono tabular figures) -->
    <div class="grid grid-cols-2 gap-3 sm:gap-4">
      <div
        @click="emit('navigate-filter', 'free')"
        :class="[
          'p-5 rounded-[24px] border cursor-pointer transition-all hover:scale-[1.02]',
          darkMode ? 'bg-[#151921] border-slate-800' : 'bg-white border-slate-200/80 shadow-xs'
        ]"
      >
        <div class="w-9 h-9 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-3 font-bold">
          <Check class="w-4 h-4" />
        </div>
        <div class="flex items-baseline gap-1.5">
          <span class="text-3xl font-black font-mono text-slate-900 dark:text-white tracking-tight tabular-nums">
            {{ freeMachinesCount }}
          </span>
          <span class="text-sm font-bold text-slate-500 dark:text-slate-400">Units</span>
        </div>
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1 block">
          Available (OFF & Free)
        </span>
      </div>

      <div
        @click="emit('navigate-filter', 'all')"
        :class="[
          'p-5 rounded-[24px] border cursor-pointer transition-all hover:scale-[1.02]',
          darkMode ? 'bg-[#151921] border-slate-800' : 'bg-white border-slate-200/80 shadow-xs'
        ]"
      >
        <div class="w-9 h-9 rounded-full bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center mb-3 font-bold">
          <Waves class="w-4 h-4" />
        </div>
        <div class="flex items-baseline gap-1.5">
          <span class="text-3xl font-black font-mono text-slate-900 dark:text-white tracking-tight tabular-nums">
            {{ runningMachinesCount }}
          </span>
          <span class="text-sm font-bold text-slate-500 dark:text-slate-400">Units</span>
        </div>
        <span class="text-xs font-medium text-slate-500 dark:text-slate-400 mt-1 block">
          Currently Running
        </span>
      </div>
    </div>

    <!-- Alert / Rush Status Card -->
    <div
      v-if="uncollectedCount > 0"
      @click="emit('navigate-filter', 'uncollected')"
      :class="[
        'p-5 rounded-[24px] border cursor-pointer transition-all hover:scale-[1.01]',
        darkMode ? 'bg-amber-500/10 border-amber-500/30' : 'bg-amber-50/90 border-amber-200/80'
      ]"
    >
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
          <MessageSquare class="w-3.5 h-3.5" />
          <span>Uncollected Laundry</span>
        </span>
        <ArrowUpRight class="w-4 h-4 text-amber-700 dark:text-amber-400" />
      </div>
      <div class="text-sm font-bold text-slate-900 dark:text-white">
        {{ uncollectedCount }} Machine with Finished Clothes
      </div>
      <p class="text-xs text-slate-600 dark:text-slate-300 mt-1 font-normal">
        Tap to send a polite reminder to clear the drum.
      </p>
    </div>

    <div
      v-else
      @click="emit('view-appliances')"
      :class="[
        'p-5 rounded-[24px] border cursor-pointer transition-all hover:scale-[1.01]',
        darkMode ? 'bg-[#151921] border-slate-800' : 'bg-white border-slate-200/80 shadow-xs'
      ]"
    >
      <div class="flex items-center justify-between mb-1">
        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Activity class="w-3.5 h-3.5 text-amber-500" />
          <span>Rush Status</span>
        </span>
        <ArrowUpRight class="w-4 h-4 text-slate-400" />
      </div>
      <div class="text-sm font-bold text-slate-900 dark:text-white">
        Normal Traffic Right Now
      </div>
      <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
        Peak hostel crowd expected between 6 PM — 9 PM tonight.
      </p>
    </div>
  </div>
</template>
