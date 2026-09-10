<script setup>
import { ref, computed } from 'vue'

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

const emit = defineEmits(['close'])

const hoveredPointIndex = ref(null)

// 4-Hour Wall-Clock Time Ticks on X-Axis
const timeTicks = computed(() => {
  const now = new Date()
  const ticks = []
  for (let i = 4; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 60 * 60 * 1000)
    const timeStr = t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const x = 20 + ((4 - i) / 4) * (760 - 40)
    ticks.push({
      label: i === 0 ? `${timeStr} (Live)` : timeStr,
      offset: i === 0 ? 'Now' : `-${i}h`,
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
          </div>
          <h3 class="text-base font-mono font-bold mt-0.5" :class="darkMode ? 'text-white' : 'text-slate-900'">
            {{ title || plug?.name || 'Washing Machine' }}
            <span v-if="subtitle" class="font-normal text-xs" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">• {{ subtitle }}</span>
            <span v-else-if="plug?.ip_address" class="text-sky-400 font-normal text-xs">• {{ plug.ip_address }}</span>
            <span v-else-if="plug?.location" class="font-normal text-xs" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">• {{ plug.location }}</span>
          </h3>
        </div>

        <button 
          @click="emit('close')" 
          class="p-2 rounded-xl border transition"
          :class="darkMode ? 'border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100'"
        >
          ✕
        </button>
      </div>

      <!-- 4-Card Summary Metrics -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Peak Power</span>
          <span class="text-lg font-mono font-black text-emerald-500 block mt-0.5 tabular-nums">
            {{ history?.peak_power_w ?? 0 }} W
          </span>
        </div>

        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Avg Active Load</span>
          <span class="text-lg font-mono font-black text-amber-500 block mt-0.5 tabular-nums">
            {{ history?.avg_power_w ?? 0 }} W
          </span>
        </div>

        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">🟢 Local WebSocket</span>
          <span class="text-lg font-mono font-black text-emerald-500 block mt-0.5 tabular-nums">
            {{ history?.local_points_count ?? 0 }} pts
          </span>
        </div>

        <div class="p-3 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <span class="text-[10px] font-mono uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">🔷 Tuya Cloud</span>
          <span class="text-lg font-mono font-black text-sky-500 block mt-0.5 tabular-nums">
            {{ history?.cloud_points_count ?? 0 }} pts
          </span>
        </div>
      </div>

      <!-- SVG Time-Series Chart Canvas -->
      <div class="relative bg-[#070a10] border border-white/10 rounded-2xl p-4 text-white overflow-hidden">
        <!-- Legend Header -->
        <div class="flex items-center justify-between text-[11px] font-mono mb-2">
          <div class="flex items-center gap-4">
            <span class="flex items-center gap-1.5 text-emerald-400 font-bold">
              <span class="w-3 h-0.5 bg-emerald-400 inline-block"></span>
              <span>● Local Socket / WebSocket (~1s High-Res)</span>
            </span>
            <span class="flex items-center gap-1.5 text-sky-400 font-bold">
              <span class="w-3 h-0.5 border-b-2 border-dashed border-sky-400 inline-block"></span>
              <span>◆ Tuya Cloud (Fallback / Slower)</span>
            </span>
          </div>

          <span class="text-[10px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Hover points for instant telemetry readout</span>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="py-20 text-center font-mono text-xs" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Loading 4-hour telemetry time-series...
        </div>

        <!-- SVG Chart -->
        <div v-else class="relative">
          <svg 
            viewBox="0 0 760 200" 
            class="w-full h-48 overflow-visible"
          >
            <defs>
              <linearGradient id="localPowerGrad" x1="0%" y1="0%" x2="0%" y2="100%">
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
              fill="url(#localPowerGrad)" 
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

            <!-- Interactive Hover Crosshair & Point Markers -->
            <g v-for="(pt, idx) in graphMetrics.points" :key="idx">
              <circle 
                :cx="pt.x" 
                :cy="pt.y" 
                r="10" 
                fill="transparent" 
                class="cursor-pointer"
                @mouseenter="hoveredPointIndex = idx"
              />
              <circle 
                v-if="hoveredPointIndex === idx"
                :cx="pt.x" 
                :cy="pt.y" 
                r="5" 
                :fill="pt.source === 'cloud' ? '#06b6d4' : '#10b981'"
                stroke="#ffffff"
                stroke-width="2"
              />
            </g>
          </svg>

          <!-- X-Axis Time Labels (Wall-Clock Hour & Minute with Relative Offsets) -->
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

          <!-- Hover Telemetry Tooltip Box -->
          <div 
            v-if="hoveredPointIndex !== null && graphMetrics.points[hoveredPointIndex]"
            class="mt-3 p-3 rounded-xl border border-slate-700/80 bg-[#121824] flex items-center justify-between text-xs font-mono animate-fadeIn"
          >
            <div class="flex items-center gap-3">
              <span 
                class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                :class="graphMetrics.points[hoveredPointIndex].source === 'cloud' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'"
              >
                {{ graphMetrics.points[hoveredPointIndex].source === 'cloud' ? '◆ TUYA_CLOUD' : '● LOCAL_WS' }}
              </span>
              <span class="text-slate-400">
                {{ graphMetrics.points[hoveredPointIndex].timestamp ? new Date(graphMetrics.points[hoveredPointIndex].timestamp).toLocaleTimeString() : 'Recent' }}
              </span>
            </div>

            <div class="flex items-center gap-4">
              <div>
                <span class="text-[10px] text-slate-400 uppercase mr-1">Power:</span>
                <span class="font-extrabold text-emerald-400 tabular-nums">{{ graphMetrics.points[hoveredPointIndex].power_w }} W</span>
              </div>
              <div v-if="graphMetrics.points[hoveredPointIndex].voltage_v">
                <span class="text-[10px] text-slate-400 uppercase mr-1">Voltage:</span>
                <span class="font-bold text-sky-400 tabular-nums">{{ graphMetrics.points[hoveredPointIndex].voltage_v }} V</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="flex justify-between items-center pt-2 text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        <span>WebSocket Live: New readings dynamically append to this chart</span>
        <button 
          @click="emit('close')"
          class="px-4 py-2 rounded-xl font-bold uppercase bg-[#10b981] text-[#003824] hover:bg-[#4edea3] transition active:scale-95 shadow-sm"
        >
          Close Graph
        </button>
      </div>
    </div>
  </div>
</template>
