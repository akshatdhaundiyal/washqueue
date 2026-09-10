<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Sliders, Sparkles, Check, Info } from 'lucide-vue-next'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  plug: {
    type: Object,
    default: null
  },
  history: {
    type: Object,
    default: null
  },
  historyLoading: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'save-calibration', 'simulate-cycle'])

// Calibration Form State
const runningThreshold = ref(10.0)
const idleThreshold = ref(5.0)
const debounceSeconds = ref(120)
const applyToSimilar = ref(false)
const selectedPreset = ref('custom')
const isSaving = ref(false)
const isSimulating = ref(false)
const detectedProfile = ref('')

// Presets for real-world washing machine & appliance profiles
const PRESETS = [
  { id: 'top_load', name: 'Top-Load (Deep Soak)', icon: '🌀', run: 12.0, idle: 4.0, soak: 240, desc: '4-min soak buffer to eliminate false completion alerts' },
  { id: 'front_load', name: 'Front-Load Inverter', icon: '🌊', run: 8.0, idle: 3.5, soak: 90, desc: 'Smooth sinusoidal tumbling direct-drive motor' },
  { id: 'heated', name: 'Front-Load Heated', icon: '🔥', run: 10.0, idle: 4.0, soak: 120, desc: 'Handles high-power internal water heater & steam wash' },
  { id: 'compact', name: 'Compact / Quick', icon: '⚡', run: 6.0, idle: 2.5, soak: 60, desc: 'Low-draw mini washers & short 15-min cycles' },
  { id: 'dryer', name: 'Commercial Dryer', icon: '💨', run: 25.0, idle: 10.0, soak: 60, desc: 'High-power continuous tumbling commercial dryers' },
  { id: 'custom', name: 'Custom Tuning', icon: '🛠️', run: null, idle: null, soak: null, desc: 'Manual slider and graph line fine-tuning' }
]

const applyPreset = (presetId) => {
  selectedPreset.value = presetId
  const p = PRESETS.find(item => item.id === presetId)
  if (p && p.id !== 'custom') {
    runningThreshold.value = p.run
    idleThreshold.value = p.idle
    debounceSeconds.value = p.soak
  }
}

// Auto-Detect Optimal Thresholds directly from loaded telemetry curve
const runAutoCalibrate = () => {
  if (!props.history?.series || props.history.series.length < 5) {
    alert('Not enough telemetry points on graph yet. Run a real wash cycle or click "Simulate Test Cycle" first.')
    return
  }

  const series = props.history.series
  const powers = series.map(pt => pt.power_w || 0.0)
  const peak = Math.max(...powers)
  const sortedP = [...powers].sort((a, b) => a - b)
  const tenPct = Math.max(1, Math.floor(sortedP.length / 10))
  const baseline = sortedP.slice(0, tenPct).reduce((a, b) => a + b, 0) / tenPct

  // Detect low-power pauses
  let inPause = false
  let pauseDuration = 0
  let maxPause = 0
  let hasStarted = false

  const activeRef = baseline + 5.0
  const idleRef = baseline + 2.0

  for (let i = 1; i < series.length; i++) {
    const p = series[i].power_w || 0.0
    const dt = (new Date(series[i].timestamp) - new Date(series[i - 1].timestamp)) / 1000.0

    if (p >= activeRef) {
      hasStarted = true
      if (inPause) {
        maxPause = Math.max(maxPause, pauseDuration)
        inPause = false
        pauseDuration = 0
      }
    } else if (hasStarted && p < idleRef) {
      inPause = true
      pauseDuration += (dt > 0 && dt < 60) ? dt : 2.0
    }
  }
  if (inPause) {
    maxPause = Math.max(maxPause, pauseDuration)
  }

  // Set tuned values
  runningThreshold.value = Math.round(Math.max(8.0, baseline + 5.0) * 10) / 10
  idleThreshold.value = Math.round(Math.max(3.0, baseline + 2.0) * 10) / 10
  debounceSeconds.value = maxPause > 0 ? Math.max(90, Math.round((maxPause * 1.25) + 15)) : 120
  selectedPreset.value = 'custom'

  if (peak > 1200) {
    detectedProfile.value = '🔥 Front-Load with Internal Heater'
  } else if (maxPause >= 150) {
    detectedProfile.value = '🌀 Top-Load with Deep Soak Cycle'
  } else if (maxPause < 90 && peak <= 600) {
    detectedProfile.value = '🌊 Direct-Drive Inverter Front-Load'
  } else {
    detectedProfile.value = '🧺 Standard Automatic Washer'
  }
}

const handleSimulateCycle = () => {
  emit('simulate-cycle', props.plug?.id)
}

// Watch plug prop to initialize values
watch(() => props.plug, (newPlug) => {
  if (newPlug) {
    runningThreshold.value = newPlug.power_threshold_running || 10.0
    idleThreshold.value = newPlug.power_threshold_idle || 5.0
    debounceSeconds.value = newPlug.debounce_seconds || 120
    applyToSimilar.value = false
    selectedPreset.value = 'custom'
  }
}, { immediate: true })

// Simulated state based on latest power and active thresholds
const currentPowerW = computed(() => {
  if (!props.plug?.latest_telemetry?.power_w) return 0.0
  return props.plug.latest_telemetry.power_w
})

const simulatedState = computed(() => {
  const p = currentPowerW.value
  if (p >= runningThreshold.value) {
    return {
      status: 'in_use',
      label: 'ACTIVE WASH (MOTOR RUNNING)',
      color: 'text-emerald-400 bg-emerald-500/20 border-emerald-500/40',
      description: `Power (${p}W) is above the ${runningThreshold.value}W active threshold. Status: in_use.`
    }
  } else if (p >= idleThreshold.value && p < runningThreshold.value) {
    return {
      status: 'soak',
      label: `SOAKING (DEBOUNCING: ${debounceSeconds.value}s)`,
      color: 'text-amber-400 bg-amber-500/20 border-amber-500/40',
      description: `Power (${p}W) is in soak range. Waiting ${debounceSeconds.value}s before declaring wash complete.`
    }
  } else {
    return {
      status: 'available',
      label: 'CYCLE COMPLETE / STANDBY',
      color: 'text-zinc-400 bg-zinc-800 border-zinc-700',
      description: `Power (${p}W) is below the ${idleThreshold.value}W idle threshold. Machine is free / empty.`
    }
  }
})

// Graph Metrics & Coordinate Calculations
const graphWidth = 760
const graphHeight = 220
const padX = 20
const padY = 20

const graphMetrics = computed(() => {
  if (!props.history || !props.history.series || props.history.series.length === 0) {
    const maxW = 50.0
    const yRun = graphHeight - padY - (runningThreshold.value / maxW) * (graphHeight - 2 * padY)
    const yIdle = graphHeight - padY - (idleThreshold.value / maxW) * (graphHeight - 2 * padY)
    return { points: [], localPath: '', localArea: '', maxW, yRun, yIdle, yTicks: [0, 25, 50] }
  }

  const series = props.history.series
  const peak = Math.max(20, props.history.peak_power_w || 0, runningThreshold.value * 1.3)
  const maxW = Math.ceil((peak * 1.15) / 10) * 10
  const yTicks = [0, Math.round(maxW / 2), maxW]

  const points = series.map((pt, idx) => {
    const x = padX + (idx / Math.max(1, series.length - 1)) * (graphWidth - 2 * padX)
    const normalizedY = Math.min(1, Math.max(0, (pt.power_w || 0) / maxW))
    const y = graphHeight - padY - normalizedY * (graphHeight - 2 * padY)
    return { ...pt, x, y, idx }
  })

  let localPath = ''
  let localArea = ''

  if (points.length > 0) {
    localPath = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)},${p.y.toFixed(1)}`, '')
    localArea = `${localPath} L ${points[points.length - 1].x.toFixed(1)},${graphHeight - padY} L ${points[0].x.toFixed(1)},${graphHeight - padY} Z`
  }

  // Calculate Y coordinates for the threshold guide lines
  const normalizedRun = Math.min(1, Math.max(0, runningThreshold.value / maxW))
  const yRun = graphHeight - padY - normalizedRun * (graphHeight - 2 * padY)

  const normalizedIdle = Math.min(1, Math.max(0, idleThreshold.value / maxW))
  const yIdle = graphHeight - padY - normalizedIdle * (graphHeight - 2 * padY)

  return {
    points,
    localPath,
    localArea,
    maxW,
    yRun,
    yIdle,
    yTicks
  }
})

// Dragging Guide Lines on SVG
const isDraggingRun = ref(false)
const isDraggingIdle = ref(false)

const startDrag = (lineType) => {
  selectedPreset.value = 'custom'
  if (lineType === 'run') isDraggingRun.value = true
  if (lineType === 'idle') isDraggingIdle.value = true
}

const onSvgMouseMove = (e) => {
  if (!isDraggingRun.value && !isDraggingIdle.value) return
  const svgEl = e.currentTarget
  const rect = svgEl.getBoundingClientRect()
  const offsetY = e.clientY - rect.top
  const normalizedY = (offsetY / rect.height) * graphHeight

  const maxW = graphMetrics.value.maxW
  const calcPower = maxW * (1 - (normalizedY - padY) / (graphHeight - 2 * padY))
  const clampedPower = Math.max(0.5, Math.min(maxW, Math.round(calcPower * 10) / 10))

  if (isDraggingRun.value) {
    runningThreshold.value = Math.max(idleThreshold.value + 1.0, clampedPower)
  } else if (isDraggingIdle.value) {
    idleThreshold.value = Math.min(runningThreshold.value - 1.0, clampedPower)
  }
}

const stopDrag = () => {
  isDraggingRun.value = false
  isDraggingIdle.value = false
}

onMounted(() => {
  window.addEventListener('mouseup', stopDrag)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', stopDrag)
})

// Save Calibration
const handleSave = async () => {
  if (idleThreshold.value >= runningThreshold.value) {
    alert('Soak / Idle threshold must be less than the Active Running threshold.')
    return
  }

  isSaving.value = true
  emit('save-calibration', {
    plug_id: props.plug.id,
    power_threshold_running: runningThreshold.value,
    power_threshold_idle: idleThreshold.value,
    debounce_seconds: debounceSeconds.value,
    apply_to_similar_machines: applyToSimilar.value
  })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
    <div 
      class="rounded-[36px] p-6 max-w-4xl w-full space-y-5 border shadow-2xl transition-all my-auto animate-fadeIn"
      :class="darkMode ? 'bg-[#121824] border-white/10 text-white' : 'bg-white border-slate-200 text-slate-900'"
    >
      <!-- Modal Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-extrabold text-[#10b981] flex items-center gap-1">
              <Sliders class="w-3.5 h-3.5" />
              <span>VISUAL_THRESHOLD_CALIBRATION_STUDIO</span>
            </span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-emerald-500/20 text-emerald-400 border-emerald-500/30">
              Zero-Code Tuning
            </span>
          </div>
          <h3 class="text-base font-mono font-bold mt-1">
            {{ plug?.name || 'Smart Plug' }} • <span class="text-sky-400">{{ plug?.ip_address }}</span>
          </h3>
          <p class="text-xs font-mono mt-0.5" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Tune how the system infers whether the washing machine is washing, soaking, or finished.
          </p>
        </div>

        <button 
          @click="emit('close')" 
          class="p-2.5 rounded-2xl border transition self-end sm:self-auto"
          :class="darkMode ? 'border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-500 hover:text-slate-900 hover:bg-slate-100'"
        >
          ✕
        </button>
      </div>

      <!-- 1-Click Appliance Profile Presets & Smart Tools -->
      <div class="space-y-2.5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs font-mono font-bold uppercase flex items-center gap-1.5" :class="darkMode ? 'text-zinc-200' : 'text-slate-800'">
              <Sparkles class="w-3.5 h-3.5 text-amber-400" />
              <span>Washing Machine Profiles & Presets</span>
            </span>
            <span v-if="detectedProfile" class="text-[10px] font-mono px-2 py-0.5 rounded-full border bg-sky-500/20 text-sky-400 border-sky-500/30 animate-pulse">
              {{ detectedProfile }}
            </span>
          </div>

          <!-- Quick Action Buttons: Auto-Detect & Simulate -->
          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="runAutoCalibrate"
              class="px-2.5 py-1 text-[11px] font-mono font-bold rounded-xl border transition flex items-center gap-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30 active:scale-95 shadow-xs"
              title="Analyzes the loaded power curve to auto-calculate baseline standby, soak window, and running cutoff"
            >
              <span>⚡</span>
              <span>Auto-Detect from Graph</span>
            </button>
            <button
              type="button"
              @click="handleSimulateCycle"
              class="px-2.5 py-1 text-[11px] font-mono font-bold rounded-xl border transition flex items-center gap-1.5 bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 border-sky-500/30 active:scale-95 shadow-xs"
              title="Inject a realistic synthetic wash cycle to test the tuner without running physical appliances"
            >
              <span>🧪</span>
              <span>Simulate Test Cycle</span>
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <button
            v-for="preset in PRESETS"
            :key="preset.id"
            @click="applyPreset(preset.id)"
            class="p-2.5 rounded-2xl border text-left transition flex flex-col justify-between active:scale-95"
            :class="selectedPreset === preset.id ? (darkMode ? 'bg-[#10b981]/15 border-[#10b981] shadow-xs' : 'bg-emerald-50 border-emerald-500 shadow-xs') : (darkMode ? 'bg-[#0a0e17] border-white/5 hover:border-white/20' : 'bg-slate-50 border-slate-200 hover:bg-slate-100')"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-lg">{{ preset.icon }}</span>
              <span v-if="selectedPreset === preset.id" class="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
            </div>
            <div>
              <h4 class="text-[11px] font-mono font-bold leading-tight" :class="darkMode ? 'text-white' : 'text-slate-900'">{{ preset.name }}</h4>
              <span v-if="preset.run !== null" class="text-[9px] font-mono block mt-0.5" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
                {{ preset.run }}W / {{ preset.soak }}s
              </span>
              <span v-else class="text-[9px] font-mono block mt-0.5" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Manual</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Live State Simulator Pill Banner -->
      <div class="p-3.5 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#070a10] border-white/10 text-white font-mono text-xs">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-xl bg-white/5 border border-white/10 text-center min-w-[70px]">
            <span class="text-[9px] uppercase text-slate-400 block">Live Load</span>
            <span class="text-sm font-black text-emerald-400 tabular-nums">{{ currentPowerW }} W</span>
          </div>

          <div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] uppercase text-slate-400">Inferred State:</span>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border" :class="simulatedState.color">
                {{ simulatedState.label }}
              </span>
            </div>
            <p class="text-[11px] text-slate-300 mt-0.5">{{ simulatedState.description }}</p>
          </div>
        </div>

        <div class="text-[10px] text-zinc-400 sm:text-right">
          <span class="block">Debounce Timer: <strong class="text-white">{{ debounceSeconds }}s ({{ (debounceSeconds / 60).toFixed(1) }} min)</strong></span>
          <span class="text-slate-400">Filters out agitation pause false-positives</span>
        </div>
      </div>

      <!-- Interactive SVG Chart with Draggable Thresholds & Shaded Zones -->
      <div class="relative bg-[#070a10] border border-white/10 rounded-3xl p-4 text-white overflow-hidden select-none">
        <div class="flex items-center justify-between text-[11px] font-mono mb-2">
          <div class="flex items-center gap-4 flex-wrap">
            <span class="flex items-center gap-1.5 text-emerald-400 font-bold">
              <span class="w-3 h-0.5 bg-emerald-400 inline-block"></span>
              <span>🟢 Active Wash Zone (&ge; {{ runningThreshold }}W)</span>
            </span>
            <span class="flex items-center gap-1.5 text-amber-400 font-bold">
              <span class="w-3 h-0.5 bg-amber-400 inline-block"></span>
              <span>🟡 Soak / Pause Zone (&ge; {{ idleThreshold }}W)</span>
            </span>
            <span class="flex items-center gap-1.5 text-zinc-400">
              <span class="w-3 h-0.5 bg-zinc-600 inline-block"></span>
              <span>⚪ Standby Zone (&lt; {{ idleThreshold }}W)</span>
            </span>
          </div>

          <span class="text-[10px] text-slate-400">💡 Drag horizontal lines up/down to adjust</span>
        </div>

        <!-- SVG Canvas -->
        <svg 
          viewBox="0 0 760 220" 
          class="w-full h-56 overflow-visible cursor-crosshair"
          @mousemove="onSvgMouseMove"
        >
          <defs>
            <linearGradient id="activeZoneGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#10b981" stop-opacity="0.25" />
              <stop offset="100%" stop-color="#10b981" stop-opacity="0.08" />
            </linearGradient>
            <linearGradient id="soakZoneGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.20" />
              <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.05" />
            </linearGradient>
          </defs>

          <!-- Zone 1: Active Running Zone Background (Above Running Line) -->
          <rect 
            x="20" 
            :y="padY" 
            width="720" 
            :height="Math.max(0, graphMetrics.yRun - padY)" 
            fill="url(#activeZoneGrad)" 
          />

          <!-- Zone 2: Soak / Debounce Zone Background (Between Idle and Running Line) -->
          <rect 
            x="20" 
            :y="graphMetrics.yRun" 
            width="720" 
            :height="Math.max(0, graphMetrics.yIdle - graphMetrics.yRun)" 
            fill="url(#soakZoneGrad)" 
          />

          <!-- Horizontal Grid Lines -->
          <g class="stroke-white/10 stroke-[1]">
            <line x1="20" y1="20" x2="740" y2="20" stroke-dasharray="3,3" />
            <line x1="20" y1="110" x2="740" y2="110" stroke-dasharray="3,3" />
            <line x1="20" y1="200" x2="740" y2="200" />
          </g>

          <!-- Power Curve Area & Line -->
          <path 
            v-if="graphMetrics.localArea"
            :d="graphMetrics.localArea" 
            fill="#10b981" 
            fill-opacity="0.15" 
          />
          <path 
            v-if="graphMetrics.localPath"
            :d="graphMetrics.localPath" 
            fill="none" 
            stroke="#10b981" 
            stroke-width="2.2" 
            stroke-linejoin="round" 
          />

          <!-- Threshold Line 1: Active Running Cutoff (Emerald Line + Handle) -->
          <g class="cursor-ns-resize" @mousedown.prevent="startDrag('run')">
            <line 
              x1="20" 
              :y1="graphMetrics.yRun" 
              x2="740" 
              :y2="graphMetrics.yRun" 
              stroke="#10b981" 
              stroke-width="2" 
              stroke-dasharray="5,4" 
            />
            <!-- Drag Handle Pill -->
            <rect 
              x="620" 
              :y="graphMetrics.yRun - 11" 
              width="115" 
              height="22" 
              rx="11" 
              fill="#10b981" 
              class="filter drop-shadow-md hover:brightness-110 transition"
            />
            <text 
              x="677" 
              :y="graphMetrics.yRun + 4" 
              fill="#003824" 
              font-size="10" 
              font-family="monospace" 
              font-weight="bold" 
              text-anchor="middle"
            >
              RUN: {{ runningThreshold }}W ↕
            </text>
          </g>

          <!-- Threshold Line 2: Idle / Soak Cutoff (Amber Line + Handle) -->
          <g class="cursor-ns-resize" @mousedown.prevent="startDrag('idle')">
            <line 
              x1="20" 
              :y1="graphMetrics.yIdle" 
              x2="740" 
              :y2="graphMetrics.yIdle" 
              stroke="#f59e0b" 
              stroke-width="2" 
              stroke-dasharray="5,4" 
            />
            <!-- Drag Handle Pill -->
            <rect 
              x="620" 
              :y="graphMetrics.yIdle - 11" 
              width="115" 
              height="22" 
              rx="11" 
              fill="#f59e0b" 
              class="filter drop-shadow-md hover:brightness-110 transition"
            />
            <text 
              x="677" 
              :y="graphMetrics.yIdle + 4" 
              fill="#451a03" 
              font-size="10" 
              font-family="monospace" 
              font-weight="bold" 
              text-anchor="middle"
            >
              SOAK: {{ idleThreshold }}W ↕
            </text>
          </g>

          <!-- Y-Axis Labels -->
          <text x="18" y="24" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">{{ graphMetrics.maxW }}W</text>
          <text x="18" y="114" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">{{ Math.round(graphMetrics.maxW / 2) }}W</text>
          <text x="18" y="204" fill="#94a3b8" font-size="9" font-family="'JetBrains Mono', monospace" text-anchor="end">0W</text>
        </svg>
      </div>

      <!-- Plain-English Sliders & Fine-Tuning Inputs -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
        <!-- Slider 1: Running Threshold -->
        <div class="p-4 rounded-2xl border space-y-2" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <div class="flex items-center justify-between">
            <label class="font-bold text-emerald-500">1. Active Motor Cutoff</label>
            <span class="font-black text-sm tabular-nums">{{ runningThreshold }} W</span>
          </div>
          <input 
            v-model.number="runningThreshold" 
            type="range" 
            min="2" 
            max="100" 
            step="0.5" 
            class="w-full accent-emerald-500 cursor-pointer"
            @input="selectedPreset = 'custom'"
          />
          <p class="text-[10px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Machine is considered <strong>Washing</strong> when power exceeds this value.
          </p>
        </div>

        <!-- Slider 2: Idle Threshold -->
        <div class="p-4 rounded-2xl border space-y-2" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <div class="flex items-center justify-between">
            <label class="font-bold text-amber-500">2. Soak / Pause Cutoff</label>
            <span class="font-black text-sm tabular-nums">{{ idleThreshold }} W</span>
          </div>
          <input 
            v-model.number="idleThreshold" 
            type="range" 
            min="0.5" 
            max="50" 
            step="0.5" 
            class="w-full accent-amber-500 cursor-pointer"
            @input="selectedPreset = 'custom'"
          />
          <p class="text-[10px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Power below this value indicates the drum is empty or completely off.
          </p>
        </div>

        <!-- Slider 3: Soak Debounce Timer -->
        <div class="p-4 rounded-2xl border space-y-2" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
          <div class="flex items-center justify-between">
            <label class="font-bold text-sky-500">3. Soak Debounce Timer</label>
            <span class="font-black text-sm tabular-nums">{{ debounceSeconds }}s ({{ (debounceSeconds / 60).toFixed(1) }}m)</span>
          </div>
          <input 
            v-model.number="debounceSeconds" 
            type="range" 
            min="15" 
            max="300" 
            step="15" 
            class="w-full accent-sky-500 cursor-pointer"
            @input="selectedPreset = 'custom'"
          />
          <p class="text-[10px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            How long low power must persist before declaring the wash cycle finished.
          </p>
        </div>
      </div>

      <!-- Batch Apply Checkbox & Footer Actions -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t font-mono text-xs" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input 
            v-model="applyToSimilar" 
            type="checkbox" 
            class="w-4 h-4 rounded text-emerald-500 accent-[#10b981]" 
          />
          <span :class="darkMode ? 'text-zinc-300' : 'text-slate-700'">
            Apply this calibration to all similar machines in this hostel
          </span>
        </label>

        <div class="flex items-center gap-2 justify-end">
          <button 
            type="button" 
            @click="emit('close')" 
            class="px-4 py-2.5 rounded-xl font-bold border transition active:scale-95"
            :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'"
          >
            Cancel
          </button>
          <button 
            type="button" 
            @click="handleSave"
            :disabled="isSaving"
            class="px-5 py-2.5 bg-[#10b981] hover:bg-[#4edea3] text-[#003824] rounded-xl font-bold uppercase transition flex items-center gap-1.5 active:scale-95 shadow-md"
          >
            <Check class="w-4 h-4" />
            <span>{{ isSaving ? 'Saving...' : 'Save & Apply Calibration' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
