<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: ''
  },
  subtitle: {
    type: String,
    default: ''
  },
  plug: {
    type: Object,
    default: null
  },
  history: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'refresh'])

const hoveredPointIndex = ref(null)
let autoRefreshTimer = null

// Periodic silent 3s background refresh while modal is open to stream fresh DB rows
const startPolling = () => {
  stopPolling()
  autoRefreshTimer = setInterval(() => {
    if (props.isOpen) {
      emit('refresh')
    }
  }, 3000)
}

const stopPolling = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

watch(() => props.isOpen, (open) => {
  if (open) {
    hoveredPointIndex.value = null
    startPolling()
  } else {
    stopPolling()
  }
}, { immediate: true })

onUnmounted(() => {
  stopPolling()
})

// Safe Date parser for UTC/ISO strings
const getPointDate = (pt) => {
  if (!pt?.timestamp) return null
  const ts = pt.timestamp
  const isoStr = typeof ts === 'string' && !ts.endsWith('Z') && !ts.includes('+') && !ts.slice(10).includes('-') ? ts + 'Z' : ts
  const d = new Date(isoStr)
  return isNaN(d.getTime()) ? null : d
}

// Format point timestamp cleanly with timezone resilience
const formatPointTime = (ts) => {
  if (!ts) return 'Recent'
  const isoStr = typeof ts === 'string' && !ts.endsWith('Z') && !ts.includes('+') && !ts.slice(10).includes('-') ? ts + 'Z' : ts
  const d = new Date(isoStr)
  return isNaN(d.getTime()) ? 'Recent' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// Latest database reading in the series
const latestPoint = computed(() => {
  const series = props.history?.series
  if (!series || series.length === 0) return null
  return series[series.length - 1]
})

// 4-Hour Time Ticks on X-Axis, automatically derived from the latest database record
const timeTicks = computed(() => {
  const latestDate = getPointDate(latestPoint.value) || new Date()
  const ticks = []
  for (let i = 4; i >= 0; i--) {
    const t = new Date(latestDate.getTime() - i * 60 * 60 * 1000)
    const timeStr = t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const x = 20 + ((4 - i) / 4) * (760 - 40)
    ticks.push({
      label: i === 0 ? `${timeStr} (Latest DB)` : timeStr,
      offset: i === 0 ? 'Latest' : `-${i}h`,
      x,
      isLive: i === 0
    })
  }
  return ticks
})

// Graph Coordinates & Scaled SVG Paths
const graphMetrics = computed(() => {
  if (!props.history || !props.history.series || props.history.series.length === 0) {
    return { points: [], localPath: '', localArea: '', cloudPath: '', cloudPoints: [], maxW: 100, yTicks: [0, 50, 100] }
  }

  const series = props.history.series
  const width = 760
  const height = 200
  const padX = 20
  const padY = 20

  const peak = Math.max(10, props.history.peak_power_w || 0)
  const maxW = Math.ceil((peak * 1.2) / 10) * 10
  const yTicks = [0, Math.round(maxW / 2), maxW]

  const points = series.map((pt, idx) => {
    const x = padX + (idx / Math.max(1, series.length - 1)) * (width - 2 * padX)
    const normalizedY = Math.min(1, Math.max(0, (pt.power_w || 0) / maxW))
    const y = height - padY - normalizedY * (height - 2 * padY)
    return { ...pt, x, y, idx }
  })

  let localPath = ''
  let localArea = ''

  if (points.length > 0) {
    localPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`, '')
    localArea = `${localPath} L ${points[points.length - 1].x.toFixed(1)},${height - padY} L ${points[0].x.toFixed(1)},${height - padY} Z`
  }

  const cloudPoints = points.filter(p => p.source === 'cloud')
  let cloudPath = ''
  if (cloudPoints.length > 1) {
    cloudPath = cloudPoints.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`, '')
  }

  return {
    points,
    localPath,
    localArea,
    cloudPath,
    cloudPoints,
    maxW,
    yTicks
  }
})

// 1-Click Export to CSV
const exportToCsv = () => {
  if (!props.history?.series || props.history.series.length === 0) {
    alert('No telemetry data available to export.')
    return
  }

  const series = props.history.series
  const headers = ['Timestamp_ISO', 'Power_Watts', 'Voltage_Volts', 'Current_mA', 'Source']
  const rows = series.map(pt => [
    pt.timestamp,
    pt.power_w ?? '',
    pt.voltage_v ?? '',
    pt.current_ma ?? '',
    pt.source ?? 'local'
  ])

  const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const safeName = (props.title || props.plug?.name || 'washqueue').toLowerCase().replace(/[^a-z0-9]/g, '_')
  const dateStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  link.setAttribute('href', url)
  link.setAttribute('download', `${safeName}_telemetry_${dateStr}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
    <div 
      class="rounded-[32px] p-6 max-w-3xl w-full space-y-5 border shadow-2xl transition-all animate-fadeIn"
      :class="darkMode ? 'bg-[#121824] border-white/10 text-white' : 'bg-white border-slate-200 text-slate-900'"
    >
      <!-- Modal Header -->
      <div class="flex items-center justify-between border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-bold text-[#10b981]">APPLIANCE_POWER_TELEMETRY</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-sky-500/20 text-sky-400 border-sky-500/30">
              4-Hour Horizon
            </span>
            <span class="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Auto-Sync DB (3s)
            </span>
          </div>
          <h3 class="text-base font-mono font-bold mt-0.5" :class="darkMode ? 'text-white' : 'text-slate-900'">
            {{ title || plug?.name || 'Washing Machine' }}
            <span v-if="subtitle" class="font-normal text-xs" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">• {{ subtitle }}</span>
            <span v-else-if="plug?.ip_address" class="text-sky-400 font-normal text-xs">• {{ plug.ip_address }}</span>
            <span v-else-if="plug?.location" class="font-normal text-xs" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">• {{ plug.location }}</span>
          </h3>
        </div>

        <div class="flex items-center gap-2">
          <!-- Quick CSV Export -->
          <button 
            @click="exportToCsv"
            title="Download CSV"
            class="px-2.5 py-1.5 rounded-xl border text-xs font-mono transition flex items-center gap-1.5"
            :class="darkMode ? 'border-slate-700 bg-slate-800/80 text-slate-300 hover:text-white hover:bg-slate-700' : 'border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200'"
          >
            <span>📥 Export CSV</span>
          </button>

          <!-- Close Modal -->
          <button 
            @click="emit('close')" 
            class="p-2 rounded-xl border transition"
            :class="darkMode ? 'border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100'"
          >
            ✕
          </button>
        </div>
      </div>

      <!-- Top Summary Metrics Grid (Prominently shows Latest Load, Peak Power, Avg Load & Source Counts) -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <!-- 1. Latest Power from Database -->
        <div class="p-3 rounded-2xl border relative overflow-hidden" :class="darkMode ? 'bg-[#0a0e17] border-emerald-500/30' : 'bg-emerald-50/50 border-emerald-200'">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono uppercase font-bold text-emerald-500">Latest Live Load</span>
            <span class="flex h-2 w-2 relative">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <span class="text-lg font-mono font-black text-emerald-400 block mt-0.5 tabular-nums">
            {{ latestPoint?.power_w ?? 0 }} W
          </span>
        </div>

        <!-- 2. Peak Power -->
        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Peak Power</span>
          <span class="text-lg font-mono font-black text-emerald-500 block mt-0.5 tabular-nums">
            {{ history?.peak_power_w ?? 0 }} W
          </span>
        </div>

        <!-- 3. Avg Active Load -->
        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Avg Active Load</span>
          <span class="text-lg font-mono font-black text-amber-500 block mt-0.5 tabular-nums">
            {{ history?.avg_power_w ?? 0 }} W
          </span>
        </div>

        <!-- 4. Data Samples (Local vs Cloud) -->
        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Samples In Horizon</span>
          <span class="text-xs font-mono font-bold block mt-1 tabular-nums flex items-center justify-between">
            <span class="text-emerald-400">🟢 {{ history?.local_points_count ?? 0 }} local</span>
            <span class="text-sky-400">🔷 {{ history?.cloud_points_count ?? 0 }} cloud</span>
          </span>
        </div>
      </div>

      <!-- SVG Time-Series Chart Canvas -->
      <div 
        class="relative bg-[#070a10] border border-white/10 rounded-2xl p-4 text-white overflow-hidden"
        @mouseleave="hoveredPointIndex = null"
      >
        <!-- Legend Header -->
        <div class="flex items-center justify-between text-[11px] font-mono mb-2">
          <div class="flex items-center gap-4">
            <span class="flex items-center gap-1.5 text-emerald-400 font-bold">
              <span class="w-3 h-0.5 bg-emerald-400 inline-block"></span>
              <span>● Local Socket / WebSocket (~3s)</span>
            </span>
            <span class="flex items-center gap-1.5 text-sky-400 font-bold">
              <span class="w-3 h-0.5 border-b-2 border-dashed border-sky-400 inline-block"></span>
              <span>◆ Tuya Cloud (Fallback)</span>
            </span>
          </div>

          <span class="text-[10px] text-slate-400">Hover points to inspect history • Leaves default to latest</span>
        </div>

        <!-- Loading State -->
        <div v-if="loading && (!history || !history.series || history.series.length === 0)" class="py-20 text-center font-mono text-xs text-slate-400">
          Loading 4-hour telemetry time-series from database...
        </div>

        <!-- SVG Chart -->
        <div v-else class="relative">
          <svg 
            viewBox="0 0 760 200" 
            class="w-full h-48 overflow-visible"
            @mouseleave="hoveredPointIndex = null"
          >
            <defs>
              <linearGradient id="localPowerGradAdmin" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#10b981" stop-opacity="0.35" />
                <stop offset="100%" stop-color="#10b981" stop-opacity="0.0" />
              </linearGradient>
            </defs>

            <!-- Grid Horizontal Lines -->
            <g class="stroke-white/10 stroke-[1]">
              <line x1="20" y1="20" x2="740" y2="20" stroke-dasharray="3,3" />
              <line x1="20" y1="100" x2="740" y2="100" stroke-dasharray="3,3" />
              <line x1="20" y1="180" x2="740" y2="180" />
            </g>

            <!-- Vertical Time Interval Grid Lines -->
            <g class="stroke-white/10 stroke-[1]">
              <line 
                v-for="tick in timeTicks" 
                :key="tick.offset"
                :x1="tick.x" 
                y1="20" 
                :x2="tick.x" 
                y2="180" 
                stroke-dasharray="2,3" 
                opacity="0.35"
              />
            </g>

            <!-- Y-Axis Labels -->
            <text x="18" y="24" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">{{ graphMetrics.maxW }}W</text>
            <text x="18" y="104" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">{{ Math.round(graphMetrics.maxW / 2) }}W</text>
            <text x="18" y="184" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">0W</text>

            <!-- Local Area Fill & Path -->
            <path 
              v-if="graphMetrics.localArea"
              :d="graphMetrics.localArea" 
              fill="url(#localPowerGradAdmin)" 
            />
            <path 
              v-if="graphMetrics.localPath"
              :d="graphMetrics.localPath" 
              fill="none" 
              stroke="#10b981" 
              stroke-width="2.5" 
              stroke-linejoin="round" 
            />

            <!-- Cloud Dashed Path -->
            <path 
              v-if="graphMetrics.cloudPath" 
              :d="graphMetrics.cloudPath" 
              fill="none" 
              stroke="#06b6d4" 
              stroke-width="2" 
              stroke-dasharray="4,4" 
            />

            <!-- Cloud Diamond Points -->
            <g v-for="cp in graphMetrics.cloudPoints" :key="cp.idx">
              <polygon 
                :points="`${cp.x},${cp.y - 4} ${cp.x + 4},${cp.y} ${cp.x},${cp.y + 4} ${cp.x - 4},${cp.y}`"
                fill="#06b6d4"
                stroke="#ffffff"
                stroke-width="1.2"
              />
            </g>

            <!-- Vertical Crosshair Guideline for Hovered Point -->
            <line
              v-if="hoveredPointIndex !== null && graphMetrics.points[hoveredPointIndex]"
              :x1="graphMetrics.points[hoveredPointIndex].x"
              y1="20"
              :x2="graphMetrics.points[hoveredPointIndex].x"
              y2="180"
              stroke="#38bdf8"
              stroke-width="1.5"
              stroke-dasharray="3,3"
              opacity="0.8"
            />

            <!-- Interactive Hover Hotspots & Point Markers -->
            <g v-for="(pt, idx) in graphMetrics.points" :key="idx">
              <circle 
                :cx="pt.x" 
                :cy="pt.y" 
                r="12" 
                fill="transparent" 
                class="cursor-pointer"
                @mouseenter="hoveredPointIndex = idx"
              />
              <circle 
                v-if="hoveredPointIndex === idx"
                :cx="pt.x" 
                :cy="pt.y" 
                r="6" 
                :fill="pt.source === 'cloud' ? '#06b6d4' : '#10b981'"
                stroke="#ffffff"
                stroke-width="2"
              />
            </g>

            <!-- Pulse Ring Highlighting the Latest Reading from DB -->
            <g v-if="graphMetrics.points.length > 0">
              <circle
                :cx="graphMetrics.points[graphMetrics.points.length - 1].x"
                :cy="graphMetrics.points[graphMetrics.points.length - 1].y"
                r="8"
                fill="none"
                stroke="#10b981"
                stroke-width="1.5"
                class="animate-ping opacity-75"
              />
              <circle
                :cx="graphMetrics.points[graphMetrics.points.length - 1].x"
                :cy="graphMetrics.points[graphMetrics.points.length - 1].y"
                r="4.5"
                fill="#10b981"
                stroke="#ffffff"
                stroke-width="1.5"
              />
            </g>
          </svg>

          <!-- X-Axis Time Labels (Automatically derived from the latest database record) -->
          <div class="flex justify-between text-[10px] font-mono px-3 pt-2">
            <div 
              v-for="tick in timeTicks" 
              :key="tick.offset" 
              class="text-center"
            >
              <span 
                class="block font-bold tabular-nums" 
                :class="tick.isLive ? 'text-emerald-400' : 'text-slate-300'"
              >
                {{ tick.label }}
              </span>
              <span class="text-[9px] text-slate-400 block">{{ tick.offset }}</span>
            </div>
          </div>

          <!-- Lower Power & Metric Panel (Defaults to Latest Database Reading, Reveals Inspected Point on Hover) -->
          <div 
            class="mt-3 p-3.5 rounded-2xl border transition-all duration-200"
            :class="darkMode ? 'bg-[#0e1420] border-white/10' : 'bg-slate-50 border-slate-200 text-slate-800'"
          >
            <!-- 1. Hover State: User is Inspecting a Specific Point -->
            <div v-if="hoveredPointIndex !== null && graphMetrics.points[hoveredPointIndex]" class="space-y-2 animate-fadeIn">
              <div class="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                <div class="flex items-center gap-2.5">
                  <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    🔍 POINT #{{ hoveredPointIndex + 1 }}
                  </span>
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                    :class="graphMetrics.points[hoveredPointIndex].source === 'cloud' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'"
                  >
                    {{ graphMetrics.points[hoveredPointIndex].source === 'cloud' ? '◆ TUYA_CLOUD' : '● LOCAL_SOCKET' }}
                  </span>
                  <span class="font-bold" :class="darkMode ? 'text-slate-200' : 'text-slate-700'">
                    {{ formatPointTime(graphMetrics.points[hoveredPointIndex].timestamp) }}
                  </span>
                </div>

                <div class="flex items-center gap-4">
                  <div>
                    <span class="text-[10px] uppercase text-slate-400 mr-1">Point Power:</span>
                    <span class="font-extrabold text-amber-400 tabular-nums">{{ graphMetrics.points[hoveredPointIndex].power_w }} W</span>
                  </div>
                  <div v-if="graphMetrics.points[hoveredPointIndex].voltage_v">
                    <span class="text-[10px] uppercase text-slate-400 mr-1">Voltage:</span>
                    <span class="font-bold text-sky-400 tabular-nums">{{ graphMetrics.points[hoveredPointIndex].voltage_v }} V</span>
                  </div>
                  <div v-if="graphMetrics.points[hoveredPointIndex].current_ma">
                    <span class="text-[10px] uppercase text-slate-400 mr-1">Current:</span>
                    <span class="font-bold text-emerald-400 tabular-nums">{{ graphMetrics.points[hoveredPointIndex].current_ma }} mA</span>
                  </div>
                </div>
              </div>

              <!-- Persistent Sub-row showing the Latest Database Reading for continuous context -->
              <div class="flex items-center justify-between text-[11px] font-mono pt-2 border-t border-white/10 text-slate-400">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
                  <span class="font-semibold text-emerald-400">LATEST DB METRIC:</span>
                  <span>{{ formatPointTime(latestPoint?.timestamp) }}</span>
                </div>
                <div class="flex items-center gap-3 tabular-nums">
                  <span>Power: <strong class="text-emerald-400">{{ latestPoint?.power_w ?? 0 }} W</strong></span>
                  <span v-if="latestPoint?.voltage_v">Voltage: <strong class="text-sky-400">{{ latestPoint.voltage_v }} V</strong></span>
                  <span v-if="latestPoint?.current_ma">Current: <strong class="text-slate-200">{{ latestPoint.current_ma }} mA</strong></span>
                </div>
              </div>
            </div>

            <!-- 2. Default State: Cleanly Shows the Latest Database Reading -->
            <div v-else class="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div class="flex items-center gap-3">
                <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                  <span class="relative flex h-2 w-2">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span class="text-[10px] font-black uppercase tracking-wider">LATEST DB TELEMETRY</span>
                </div>

                <span 
                  v-if="latestPoint?.source"
                  class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                  :class="latestPoint.source === 'cloud' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'"
                >
                  {{ latestPoint.source === 'cloud' ? '◆ TUYA_CLOUD' : '● LOCAL_SOCKET' }}
                </span>

                <span class="font-bold tabular-nums" :class="darkMode ? 'text-slate-200' : 'text-slate-800'">
                  {{ formatPointTime(latestPoint?.timestamp) }}
                </span>
                <span class="text-[10px] text-slate-400 hidden sm:inline">(Live Polling 3s)</span>
              </div>

              <div class="flex items-center gap-4">
                <div>
                  <span class="text-[10px] text-slate-400 uppercase mr-1">Latest Power:</span>
                  <span class="text-sm font-black text-emerald-400 tabular-nums">{{ latestPoint?.power_w ?? 0 }} W</span>
                </div>
                <div v-if="latestPoint?.voltage_v">
                  <span class="text-[10px] text-slate-400 uppercase mr-1">Voltage:</span>
                  <span class="font-bold text-sky-400 tabular-nums">{{ latestPoint.voltage_v }} V</span>
                </div>
                <div v-if="latestPoint?.current_ma">
                  <span class="text-[10px] text-slate-400 uppercase mr-1">Current:</span>
                  <span class="font-bold tabular-nums" :class="darkMode ? 'text-slate-200' : 'text-slate-700'">{{ latestPoint.current_ma }} mA</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="flex justify-between items-center pt-1 text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>Live Database Stream: Auto-polls every 3s & updates on local socket events</span>
        </div>

        <div class="flex items-center gap-2">
          <button 
            @click="emit('refresh')"
            title="Force refresh database telemetry"
            class="px-3 py-1.5 rounded-xl border text-xs font-bold uppercase transition flex items-center gap-1 active:scale-95"
            :class="darkMode ? 'border-slate-800 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700' : 'border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200'"
          >
            <span>🔄 Sync DB</span>
          </button>
          <button 
            @click="emit('close')"
            class="px-4 py-2 rounded-xl font-bold uppercase bg-[#10b981] text-[#003824] hover:bg-[#4edea3] transition active:scale-95 shadow-sm"
          >
            Close Graph
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
