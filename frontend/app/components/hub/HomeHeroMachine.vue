<script setup>
import { Disc, Power, Bell, Activity } from 'lucide-vue-next'

const props = defineProps({
  myMachine: {
    type: Object,
    required: true
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['release-machine', 'browse-machines', 'toggle-notify', 'view-history'])
</script>

<template>
  <div
    :class="[
      'rounded-[28px] sm:rounded-[32px] p-6 sm:p-8 border relative overflow-hidden transition-all',
      darkMode
        ? 'bg-gradient-to-br from-slate-900 via-[#141822] to-slate-900 border-slate-800 shadow-xl'
        : 'bg-white border-slate-200/80 shadow-[0_4px_20px_rgba(0,0,0,0.03)]'
    ]"
  >
    <!-- 3D Soft Geometric Decoration -->
    <div class="absolute -right-4 -bottom-4 w-40 h-40 opacity-20 pointer-events-none flex items-center justify-center">
      <div class="w-24 h-24 rounded-2xl bg-gradient-to-tr from-sky-400 to-indigo-500 transform rotate-45" />
      <div class="w-20 h-20 rounded-xl bg-gradient-to-br from-indigo-300 to-cyan-400 transform -rotate-12 absolute" />
    </div>

    <!-- State A: When Machine is Claimed -->
    <div v-if="myMachine.claimed">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
          <span class="text-sm font-bold text-slate-900 dark:text-white tracking-tight">
            {{ myMachine.name }}
          </span>
        </div>
        <button
          @click="emit('release-machine')"
          :class="[
            'text-xs font-bold px-3.5 py-1.5 rounded-full border transition-all hover:scale-105',
            darkMode
              ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
              : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200 hover:text-slate-900'
          ]"
        >
          Release Load
        </button>
      </div>

      <!-- Active Stopwatch Display (JetBrains Mono tabular numbers) -->
      <div class="my-7 sm:my-9">
        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">
          Active Elapsed Time
        </span>
        <div class="flex items-baseline gap-2.5">
          <span class="text-6xl sm:text-7xl font-black tracking-tight font-mono text-slate-900 dark:text-white tabular-nums">
            {{ myMachine.runningMinutes }}
          </span>
          <span class="text-xl sm:text-2xl font-bold text-slate-500 dark:text-slate-400">
            min running
          </span>
        </div>
        <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-2 font-normal flex items-center gap-2.5 flex-wrap">
          <span>Started at <span class="font-medium text-slate-700 dark:text-slate-200">{{ myMachine.startedAt }}</span> • Current draw:
          <strong class="text-slate-900 dark:text-white font-bold font-mono tabular-nums">{{ myMachine.powerDraw }}</strong></span>
          <button
            @click="emit('view-history', myMachine)"
            class="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 hover:bg-sky-500/20 transition-all flex items-center gap-1 active:scale-95 shadow-2xs"
            title="View 4-Hour Power Telemetry Graph"
          >
            <Activity class="w-3.5 h-3.5" />
            <span>4h Power Curve</span>
          </button>
        </p>
      </div>

      <!-- Status Capsule & 0W Stop Alert -->
      <div class="pt-5 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="inline-flex items-center gap-2 bg-slate-900 dark:bg-slate-800 text-white px-4 py-2 rounded-full text-xs font-bold self-start sm:self-auto shadow-xs">
          <Power class="w-3.5 h-3.5 text-emerald-400" />
          <span>Motor Active</span>
        </div>

        <button
          @click="emit('toggle-notify')"
          class="text-xs font-bold text-sky-600 dark:text-sky-400 hover:text-sky-700 dark:hover:text-sky-300 hover:underline flex items-center gap-1.5"
        >
          <Bell class="w-4 h-4" />
          <span>Notify on 0W Stop</span>
        </button>
      </div>
    </div>

    <!-- State B: When No Machine Claimed -->
    <div v-else class="py-10 text-center space-y-4">
      <div class="w-14 h-14 rounded-full bg-slate-100 dark:bg-slate-800 mx-auto flex items-center justify-center text-slate-400">
        <Disc class="w-7 h-7" />
      </div>
      <div>
        <h4 class="font-bold text-base text-slate-900 dark:text-white">No Machine Claimed</h4>
        <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-[280px] mx-auto">
          Check available machines in the Appliances tab to claim one before washing.
        </p>
      </div>
      <button
        @click="emit('browse-machines')"
        class="py-3 px-6 rounded-full text-xs sm:text-sm font-bold bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:scale-105 transition-all"
      >
        Browse & Claim Machine
      </button>
    </div>
  </div>
</template>
