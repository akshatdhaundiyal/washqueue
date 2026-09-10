<script setup>
import { Plus, Activity, Edit2, Trash2, Sliders } from 'lucide-vue-next'

const props = defineProps({
  smartPlugs: {
    type: Array,
    default: () => []
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  isWsConnected: {
    type: Boolean,
    default: false
  },
  isAutoRefresh: {
    type: Boolean,
    default: true
  },
  isSyncing: {
    type: Boolean,
    default: false
  },
  pollingPlugId: {
    type: String,
    default: null
  },
  togglingSwitchId: {
    type: String,
    default: null
  }
})

const emit = defineEmits([
  'sync-cloud',
  'add-plug',
  'toggle-switch',
  'poll-instant',
  'open-graph',
  'open-tuner',
  'edit-plug',
  'delete-plug'
])
</script>

<template>
  <section class="space-y-6 animate-fadeIn">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
            IOT_TELEMETRY // LIVE_SMART_PLUG_STATISTICS
          </h2>
          <span 
            class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border flex items-center gap-1.5"
            :class="isAutoRefresh ? 'bg-emerald-500/20 text-emerald-500 border-emerald-500/40' : 'bg-zinc-800 text-zinc-400 border-zinc-700'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="isAutoRefresh ? 'bg-emerald-500 animate-ping' : 'bg-zinc-500'"></span>
            {{ isWsConnected ? '● REAL-TIME WS (LIVE)' : (isAutoRefresh ? '● LIVE STREAM (1s)' : 'STREAM PAUSED') }}
          </span>
        </div>
        <p class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Instantaneous telemetry (Watts, Volts, Current, Energy) and remote relay controls for all smart plugs.
        </p>
      </div>

      <div class="flex items-center gap-2.5 flex-wrap">
        <button 
          @click="emit('sync-cloud')"
          :disabled="isSyncing"
          class="bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-bold text-xs px-3.5 py-2 rounded-xl transition inline-flex items-center gap-1.5 active:scale-95 shadow-xs"
        >
          <span>{{ isSyncing ? 'Syncing...' : '🔄 Cloud Auto-Sync' }}</span>
        </button>
        <button 
          @click="emit('add-plug')"
          class="bg-[#10b981] hover:bg-[#4edea3] text-[#003824] font-mono font-bold text-xs px-3.5 py-2 rounded-xl transition inline-flex items-center gap-1.5 active:scale-95 shadow-xs"
        >
          <Plus class="w-3.5 h-3.5" />
          <span>Register Smart Plug</span>
        </button>
      </div>
    </div>

    <!-- Telemetry Cards Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div 
        v-for="plug in smartPlugs" 
        :key="plug.id"
        class="rounded-3xl p-5 border flex flex-col justify-between transition-all"
        :class="darkMode ? 'bg-[#121824] border-white/10 shadow-lg' : 'bg-white border-slate-200 shadow-xs'"
      >
        <div>
          <!-- Plug Header & Badges -->
          <div class="flex items-center justify-between mb-3">
            <div>
              <h3 class="font-mono font-bold text-sm" :class="darkMode ? 'text-white' : 'text-slate-900'">
                {{ plug.name || 'Wipro 16A Smart Plug' }}
              </h3>
              <span class="text-[11px] font-mono block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
                Node ID: {{ plug.device_id.slice(0, 12) }}...
              </span>
            </div>

            <div class="flex items-center gap-1.5">
              <!-- Online Status Badge -->
              <span 
                class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border flex items-center gap-1"
                :class="plug.is_online ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border-rose-500/30'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="plug.is_online ? 'bg-emerald-500' : 'bg-rose-500'"></span>
                {{ plug.is_online ? 'ONLINE' : 'OFFLINE' }}
              </span>

              <!-- Relay Switch Toggle Button -->
              <button 
                @click="emit('toggle-switch', plug.id, plug.latest_telemetry?.switch_on)"
                :disabled="togglingSwitchId === plug.id"
                class="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold border transition active:scale-95"
                :class="plug.latest_telemetry?.switch_on ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30' : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:bg-zinc-700'"
                title="Click to toggle relay power on/off"
              >
                {{ togglingSwitchId === plug.id ? '...' : (plug.latest_telemetry?.switch_on ? '⚡ SWITCH ON' : '⚪ SWITCH OFF') }}
              </button>
            </div>
          </div>

          <!-- Instantaneous Telemetry Gauges -->
          <div 
            class="rounded-2xl p-4 border my-3 transition-colors"
            :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-200 text-slate-900 shadow-2xs'"
          >
            <div class="flex items-baseline justify-between mb-2">
              <span class="text-[10px] font-mono uppercase" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Instantaneous Power</span>
              <span 
                class="text-[10px] font-mono font-bold uppercase px-1.5 py-0.2 rounded"
                :class="{
                  'bg-emerald-500/20 text-emerald-500': (plug.latest_telemetry?.power_w || 0) >= (plug.power_threshold_running || 10),
                  'bg-amber-500/20 text-amber-500': (plug.latest_telemetry?.power_w || 0) > 0 && (plug.latest_telemetry?.power_w || 0) < (plug.power_threshold_running || 10),
                  'bg-zinc-800 text-zinc-500': (plug.latest_telemetry?.power_w || 0) === 0
                }"
              >
                {{ (plug.latest_telemetry?.power_w || 0) >= (plug.power_threshold_running || 10) ? 'Motor Running' : ((plug.latest_telemetry?.power_w || 0) > 0 ? 'Idle / Soak' : 'Standby') }}
              </span>
            </div>

            <div class="flex items-baseline gap-2 mb-3">
              <span 
                class="text-3xl font-mono font-black tracking-tight tabular-nums"
                :class="(plug.latest_telemetry?.power_w || 0) >= (plug.power_threshold_running || 10) ? 'text-emerald-500' : (darkMode ? 'text-white' : 'text-slate-900')"
              >
                {{ plug.latest_telemetry?.power_w ?? 0.0 }}
              </span>
              <span class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Watts</span>
            </div>

            <!-- Instantaneous Metrics Breakdown -->
            <div class="grid grid-cols-3 gap-2 pt-2 border-t text-center font-mono" :class="darkMode ? 'border-white/10' : 'border-slate-200'">
              <div class="p-1.5 rounded-lg" :class="darkMode ? 'bg-white/[0.02]' : 'bg-white border border-slate-200/80 shadow-2xs'">
                <span class="text-[9px] uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Voltage</span>
                <span class="text-xs font-bold text-sky-500">{{ plug.latest_telemetry?.voltage_v ?? 0 }} V</span>
              </div>
              <div class="p-1.5 rounded-lg" :class="darkMode ? 'bg-white/[0.02]' : 'bg-white border border-slate-200/80 shadow-2xs'">
                <span class="text-[9px] uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Current</span>
                <span class="text-xs font-bold text-amber-500">{{ plug.latest_telemetry?.current_ma ?? 0 }} mA</span>
              </div>
              <div class="p-1.5 rounded-lg" :class="darkMode ? 'bg-white/[0.02]' : 'bg-white border border-slate-200/80 shadow-2xs'">
                <span class="text-[9px] uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Energy</span>
                <span class="text-xs font-bold text-purple-500">{{ plug.latest_telemetry?.energy_kwh ?? 0 }} kWh</span>
              </div>
            </div>
          </div>

          <!-- Hardware Metadata -->
          <div class="space-y-1 font-mono text-xs mb-3" :class="darkMode ? 'text-zinc-400' : 'text-slate-600'">
            <div class="flex justify-between">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Hardware MAC:</span>
              <span class="font-bold" :class="darkMode ? 'text-zinc-200' : 'text-slate-800'">{{ plug.mac_address || 'f8:17:2d:af:26:d8' }}</span>
            </div>
            <div class="flex justify-between">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Local IP / Port:</span>
              <span class="font-bold" :class="darkMode ? 'text-zinc-200' : 'text-slate-800'">{{ plug.ip_address }}:6668</span>
            </div>
            <div class="flex justify-between">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Protocol:</span>
              <span class="font-bold text-indigo-500">Tuya v{{ plug.protocol_version || '3.3' }}</span>
            </div>
            <div class="flex justify-between">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Last Polled:</span>
              <span class="text-[11px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
                {{ plug.latest_telemetry?.recorded_at ? new Date(plug.latest_telemetry.recorded_at).toLocaleTimeString() : 'Never' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Plug Bottom Action Bar -->
        <div class="pt-3 border-t flex items-center justify-between gap-2" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
          <div class="flex items-center gap-1.5">
            <button 
              @click="emit('poll-instant', plug.id)"
              :disabled="pollingPlugId === plug.id"
              class="px-2.5 py-1.5 rounded-xl font-mono text-xs font-bold border transition flex items-center gap-1 active:scale-95"
              :class="darkMode ? 'bg-[#0a0e17] border-white/15 text-[#10b981] hover:bg-white/5' : 'bg-slate-100 border-slate-200 text-emerald-600 hover:bg-slate-200'"
              title="Force an immediate telemetry reading"
            >
              <span>{{ pollingPlugId === plug.id ? '...' : '⚡ Poll' }}</span>
            </button>

            <!-- 4hr Power Graph Button -->
            <button 
              @click="emit('open-graph', plug)"
              class="px-2.5 py-1.5 rounded-xl font-mono text-xs font-bold border transition flex items-center gap-1.5 active:scale-95"
              :class="darkMode ? 'bg-sky-500/10 border-sky-500/30 text-sky-400 hover:bg-sky-500/20' : 'bg-sky-50 border-sky-200 text-sky-600 hover:bg-sky-100'"
              title="View 4-hour historical power curve (local vs cloud)"
            >
              <Activity class="w-3.5 h-3.5" />
              <span>4hr Graph</span>
            </button>

            <!-- Visual Threshold Tuner Button -->
            <button 
              @click="emit('open-tuner', plug)"
              class="px-2.5 py-1.5 rounded-xl font-mono text-xs font-bold border transition flex items-center gap-1.5 active:scale-95"
              :class="darkMode ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/25' : 'bg-emerald-50 border-emerald-200 text-emerald-600 hover:bg-emerald-100'"
              title="Visual graph & slider threshold calibration studio"
            >
              <Sliders class="w-3.5 h-3.5" />
              <span>Tune</span>
            </button>
          </div>

          <div class="flex items-center gap-1">
            <button 
              @click="emit('edit-plug', plug)"
              class="p-2 rounded-xl border transition"
              :class="darkMode ? 'border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100'"
              title="Edit Configuration"
            >
              <Edit2 class="w-3.5 h-3.5" />
            </button>
            <button 
              @click="emit('delete-plug', plug.id)"
              class="p-2 rounded-xl border border-rose-500/20 text-rose-400 hover:bg-rose-500/10 transition"
              title="Delete Plug"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="smartPlugs.length === 0" class="col-span-full rounded-3xl p-12 text-center border font-mono" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200'">
        <p class="text-3xl mb-2">🔌</p>
        <p class="text-sm font-bold mb-1" :class="darkMode ? 'text-white' : 'text-slate-900'">No Smart Plugs Registered</p>
        <p class="text-xs max-w-md mx-auto mb-4" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Click "Cloud Auto-Sync" to discover linked Tuya plugs, or manually register a new hardware node.</p>
        <button 
          @click="emit('sync-cloud')"
          class="bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-bold text-xs px-4 py-2 rounded-xl transition inline-flex items-center gap-1.5 shadow-xs"
        >
          🔄 Auto-Discover Plugs From Cloud
        </button>
      </div>
    </div>
  </section>
</template>
