<script setup>
import { ref } from 'vue'
import { ChevronUp, ChevronDown, Activity, Zap, Cpu, Waves } from 'lucide-vue-next'

const props = defineProps({
  darkMode: {
    type: Boolean,
    default: false
  },
  isWsConnected: {
    type: Boolean,
    default: false
  },
  totalLivePower: {
    type: [String, Number],
    default: '0.0'
  },
  averageVoltage: {
    type: [String, Number],
    default: '0.0'
  },
  onlinePlugsCount: {
    type: Number,
    default: 0
  },
  totalPlugsCount: {
    type: Number,
    default: 0
  },
  activeMachinesCount: {
    type: Number,
    default: 0
  },
  totalMachinesCount: {
    type: Number,
    default: 0
  }
})

const showMetricsBanner = ref(true)
</script>

<template>
  <div 
    class="rounded-[28px] border transition-all p-4 sm:p-6"
    :class="darkMode ? 'bg-[#151921] border-slate-800 shadow-sm' : 'bg-white border-slate-200/80 shadow-xs'"
  >
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2.5">
        <span class="text-xs font-bold uppercase tracking-wider" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Hostel System Telemetry
        </span>
        <span 
          class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border flex items-center gap-1.5"
          :class="isWsConnected ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/20' : 'bg-amber-50 text-amber-700 border-amber-200/60 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/20'"
        >
          <span class="w-1.5 h-1.5 rounded-full" :class="isWsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'"></span>
          {{ isWsConnected ? 'WebSocket Live (<10ms)' : '1s Polling' }}
        </span>
      </div>

      <button 
        @click="showMetricsBanner = !showMetricsBanner"
        class="text-xs font-semibold flex items-center gap-1 hover:underline transition-colors"
        :class="darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'"
      >
        <span>{{ showMetricsBanner ? 'Collapse' : 'Expand' }}</span>
        <ChevronUp v-if="showMetricsBanner" class="w-3.5 h-3.5" />
        <ChevronDown v-else class="w-3.5 h-3.5" />
      </button>
    </div>

    <div v-show="showMetricsBanner" class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 transition-all">
      <!-- Total Load -->
      <div class="p-4 rounded-2xl border" :class="darkMode ? 'bg-[#0c0e14] border-slate-800/80' : 'bg-slate-50/90 border-slate-200/70'">
        <span class="text-[11px] font-semibold uppercase tracking-wider block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Total Active Load</span>
        <div class="flex items-baseline gap-1.5 mt-1.5">
          <span class="text-2xl sm:text-3xl font-mono font-black text-emerald-600 dark:text-emerald-400 tabular-nums">{{ totalLivePower }}</span>
          <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">Watts</span>
        </div>
      </div>

      <!-- Average Grid Voltage -->
      <div class="p-4 rounded-2xl border" :class="darkMode ? 'bg-[#0c0e14] border-slate-800/80' : 'bg-slate-50/90 border-slate-200/70'">
        <span class="text-[11px] font-semibold uppercase tracking-wider block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Grid Voltage</span>
        <div class="flex items-baseline gap-1.5 mt-1.5">
          <span class="text-2xl sm:text-3xl font-mono font-black tabular-nums" :class="darkMode ? 'text-white' : 'text-slate-900'">{{ averageVoltage }}</span>
          <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">Volts</span>
        </div>
      </div>

      <!-- Online Smart Plugs -->
      <div class="p-4 rounded-2xl border" :class="darkMode ? 'bg-[#0c0e14] border-slate-800/80' : 'bg-slate-50/90 border-slate-200/70'">
        <span class="text-[11px] font-semibold uppercase tracking-wider block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Online Hardware</span>
        <div class="flex items-baseline gap-1.5 mt-1.5">
          <span class="text-2xl sm:text-3xl font-mono font-black text-sky-600 dark:text-sky-400 tabular-nums">
            {{ onlinePlugsCount }}
          </span>
          <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">/ {{ totalPlugsCount }} registered</span>
        </div>
      </div>

      <!-- Active Fleet -->
      <div class="p-4 rounded-2xl border" :class="darkMode ? 'bg-[#0c0e14] border-slate-800/80' : 'bg-slate-50/90 border-slate-200/70'">
        <span class="text-[11px] font-semibold uppercase tracking-wider block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Active Fleet</span>
        <div class="flex items-baseline gap-1.5 mt-1.5">
          <span class="text-2xl sm:text-3xl font-mono font-black text-indigo-600 dark:text-indigo-400 tabular-nums">
            {{ activeMachinesCount }}
          </span>
          <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">/ {{ totalMachinesCount }} units</span>
        </div>
      </div>
    </div>
  </div>
</template>
