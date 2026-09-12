<script setup>
import { Shield, RefreshCw, Lock, Clock } from 'lucide-vue-next'

const props = defineProps({
  currentAdminTab: {
    type: String,
    required: true
  },
  isWsConnected: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  isAutoRefresh: {
    type: Boolean,
    default: true
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh-data', 'update:isAutoRefresh', 'lock-session'])

const { selectedTimezone, getTimezoneAbbr, getTimezoneOffsetStr } = useAppTimezone()
</script>

<template>
  <div>
    <!-- MOBILE TOP HEADER (md:hidden) -->
    <header
      :class="[
        'md:hidden flex items-center justify-between px-4 py-3 border-b sticky top-0 z-30 transition-colors',
        darkMode ? 'bg-[#10131a]/95 border-slate-800 backdrop-blur-md' : 'bg-white/95 border-slate-200 backdrop-blur-md shadow-xs'
      ]"
    >
      <div class="flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-white shadow-sm">
          <Shield class="w-4 h-4" />
        </div>
        <div>
          <span class="text-sm font-bold text-slate-900 dark:text-white block leading-none">Admin Console</span>
          <span class="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">Block B Operator • {{ getTimezoneAbbr() }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button
          @click="emit('refresh-data')"
          :disabled="loading"
          class="w-9 h-9 rounded-full border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-300"
          title="Refresh"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
        </button>
        <button
          @click="emit('lock-session')"
          class="w-9 h-9 rounded-full border border-rose-200 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/40 flex items-center justify-center text-rose-600 dark:text-rose-400"
          title="Lock"
        >
          <Lock class="w-3.5 h-3.5" />
        </button>
      </div>
    </header>

    <!-- DESKTOP TOP HEADER (hidden md:flex) -->
    <header
      :class="[
        'hidden md:flex h-16 border-b shrink-0 items-center justify-between px-6 lg:px-10 sticky top-0 z-20 transition-colors',
        darkMode ? 'bg-[#0c0e14]/90 border-slate-800/80 backdrop-blur-md' : 'bg-[#f6f8fa]/95 border-slate-200/80 backdrop-blur-md'
      ]"
    >
      <!-- Left: Tab Heading & Stream Indicator -->
      <div class="flex items-center gap-2.5">
        <span class="text-xs font-extrabold uppercase tracking-wider text-slate-900 dark:text-white">
          {{ currentAdminTab === 'fleet' ? 'Fleet & Bookings Hub' : currentAdminTab === 'iot' ? 'Smart Plugs & Tuya IoT Nodes' : currentAdminTab === 'database' ? 'Database Management Portal' : 'Users & Permissions' }}
        </span>
        <span class="text-slate-300 dark:text-slate-700">•</span>
        <div class="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border bg-white dark:bg-slate-800/80 border-slate-200/80 dark:border-slate-700 shadow-2xs">
          <span class="w-2 h-2 rounded-full" :class="isWsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'" />
          <span class="text-slate-600 dark:text-slate-400">
            {{ isWsConnected ? 'Local Edge WebSocket Live (<10ms)' : 'Polling Active' }}
          </span>
        </div>
        <span class="text-slate-300 dark:text-slate-700">•</span>
        <div 
          class="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border bg-white dark:bg-slate-800/80 border-slate-200/80 dark:border-slate-700 shadow-2xs"
          :title="`Active System Timezone: ${selectedTimezone}`"
        >
          <Clock class="w-3.5 h-3.5 text-amber-500" />
          <span class="text-slate-600 dark:text-slate-400 font-mono">
            {{ getTimezoneAbbr() }} ({{ getTimezoneOffsetStr() }})
          </span>
        </div>
      </div>


      <!-- Right: Controls -->
      <div class="flex items-center gap-3">
        <!-- Manual Refresh Button -->
        <button
          @click="emit('refresh-data')"
          :disabled="loading"
          :class="[
            'px-3.5 py-1.5 rounded-full border text-xs font-bold transition-all flex items-center gap-2',
            darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 shadow-xs'
          ]"
          title="Refresh Telemetry Data"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" />
          <span>Refresh</span>
        </button>

        <!-- Auto-refresh Toggle -->
        <label class="flex items-center gap-2 text-xs font-semibold cursor-pointer select-none text-slate-600 dark:text-slate-400">
          <input
            type="checkbox"
            :checked="isAutoRefresh"
            @change="emit('update:isAutoRefresh', $event.target.checked)"
            class="accent-emerald-600 rounded"
          />
          <span>Auto-refresh (1s)</span>
        </label>

        <!-- Lock Session Button -->
        <button
          @click="emit('lock-session')"
          class="p-2 rounded-full border border-rose-200 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 hover:scale-105 transition-all"
          title="Lock Admin Session"
        >
          <Lock class="w-4 h-4" />
        </button>
      </div>
    </header>
  </div>
</template>
