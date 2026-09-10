<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { CheckCircle2 } from 'lucide-vue-next'
import AppSidebar from '~/components/hub/AppSidebar.vue'
import AppTopHeader from '~/components/hub/AppTopHeader.vue'
import HomeHeroMachine from '~/components/hub/HomeHeroMachine.vue'
import OverviewCards from '~/components/hub/OverviewCards.vue'
import ApplianceCard from '~/components/hub/ApplianceCard.vue'
import ResidentProfileView from '~/components/hub/ResidentProfileView.vue'
import SettingsModal from '~/components/hub/SettingsModal.vue'
import MobileBottomNav from '~/components/hub/MobileBottomNav.vue'
import PowerGraphModal from '~/components/common/PowerGraphModal.vue'

// Configuration & Theme
const config = useRuntimeConfig()
const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'

// Persistent Theme Synchronization
const { isDark: darkMode, toggleTheme, setTheme } = useAppTheme()

// Navigation & Modal State
const activeTab = ref('home') // 'home' | 'machines' | 'profile'
const showSettings = ref(false)
const toast = ref(null)
const filterType = ref('all') // 'all' | 'washers' | 'dryers' | 'free' | 'uncollected'
const pushAlertEnabled = ref(true)
const anonymousBuzzEnabled = ref(true)

// User's Claimed Active Appliance
const myMachine = ref({
  claimed: true,
  id: 'W-02',
  name: 'SpeedQueen Washer 02',
  location: 'Block B • 2nd Floor',
  isOn: true,
  runningMinutes: 28,
  powerDraw: '340W',
  startedAt: '8:42 AM',
  notifyWhenOff: true
})

// State of all appliances with inline buzz counters & smart telemetry
const machines = ref([
  {
    id: 'W-01',
    name: 'Washer 01 (LG Heavy)',
    type: 'washer',
    location: 'Block B • 2nd Floor',
    isOn: true,
    status: 'in-use', // 'available' | 'in-use' | 'uncollected'
    runningMinutes: 46,
    powerDraw: '320W',
    nudgesSent: 1,
    myBuzzed: false
  },
  {
    id: 'W-02',
    name: 'SpeedQueen Washer 02',
    type: 'washer',
    location: 'Block B • 2nd Floor',
    isOn: true,
    status: 'in-use',
    runningMinutes: 28,
    powerDraw: '340W',
    nudgesSent: 0,
    myBuzzed: false
  },
  {
    id: 'W-03',
    name: 'Washer 03 (IFB Eco)',
    type: 'washer',
    location: 'Block B • 2nd Floor',
    isOn: false,
    status: 'available',
    runningMinutes: 0,
    powerDraw: '0W',
    nudgesSent: 0,
    myBuzzed: false
  },
  {
    id: 'W-04',
    name: 'Washer 04 (Samsung)',
    type: 'washer',
    location: 'Block B • 2nd Floor',
    isOn: true,
    status: 'in-use',
    runningMinutes: 12,
    powerDraw: '280W',
    nudgesSent: 0,
    myBuzzed: false
  },
  {
    id: 'D-01',
    name: 'Dryer Pro 01 (Whirlpool)',
    type: 'dryer',
    location: 'Block B • 2nd Floor',
    isOn: false,
    status: 'uncollected',
    runningMinutes: 0,
    finishedAgoMin: 18,
    powerDraw: '0W',
    nudgesSent: 3,
    myBuzzed: false
  },
  {
    id: 'D-02',
    name: 'Dryer Pro 02 (Siemens)',
    type: 'dryer',
    location: 'Block B • 2nd Floor',
    isOn: false,
    status: 'available',
    runningMinutes: 0,
    powerDraw: '0W',
    nudgesSent: 0,
    myBuzzed: false
  }
])

const filterTabs = [
  { id: 'all', label: 'All' },
  { id: 'washers', label: 'Washers' },
  { id: 'dryers', label: 'Dryers' },
  { id: 'free', label: 'Available' },
  { id: 'uncollected', label: 'Uncollected' }
]

// Toast notification trigger
let toastTimer = null
const showToast = (msg) => {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = msg
  toastTimer = setTimeout(() => {
    toast.value = null
  }, 3500)
}

// Formatted current date string
const formattedDate = computed(() => {
  const d = new Date()
  return d.toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
})

// Optional background synchronization if backend API is reachable
const fetchBackendData = async () => {
  try {
    const data = await $fetch(`${apiBase}/api/machines`)
    if (data && Array.isArray(data) && data.length > 0) {
      machines.value = data.map((m) => {
        const powerW = m.latest_power_w ?? 0
        const isRunning = m.status === 'in_use' || powerW >= 10.0
        const isUncollected = m.status === 'uncollected'
        return {
          id: m.id,
          name: m.name,
          type: m.type || (m.name.toLowerCase().includes('dryer') ? 'dryer' : 'washer'),
          location: m.location || 'Block B • 2nd Floor',
          isOn: isRunning,
          status: isUncollected ? 'uncollected' : isRunning ? 'in-use' : 'available',
          runningMinutes: m.running_minutes ?? (isRunning ? 28 : 0),
          finishedAgoMin: m.finished_ago_min ?? (isUncollected ? 15 : undefined),
          powerDraw: `${powerW.toFixed(0)}W`,
          nudgesSent: m.nudges_sent ?? 0,
          myBuzzed: false
        }
      })
    }
  } catch (err) {
    // Graceful offline fallback
  }
}

// Live timer tick for minutes elapsed
let intervalId = null
onMounted(() => {
  fetchBackendData()

  intervalId = setInterval(() => {
    if (myMachine.value.claimed && myMachine.value.isOn) {
      myMachine.value.runningMinutes += 1
    }

    machines.value = machines.value.map((m) => {
      if (m.isOn) {
        return { ...m, runningMinutes: m.runningMinutes + 1 }
      }
      if (m.status === 'uncollected' && m.finishedAgoMin !== undefined) {
        return { ...m, finishedAgoMin: m.finishedAgoMin + 1 }
      }
      return m
    })
  }, 60000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
  if (toastTimer) clearTimeout(toastTimer)
})

// Claim & Book an available machine
const handleClaimMachine = async (machine) => {
  const startTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  machines.value = machines.value.map((m) =>
    m.id === machine.id
      ? {
          ...m,
          isOn: true,
          status: 'in-use',
          runningMinutes: 1,
          powerDraw: m.type === 'dryer' ? '1800W' : '310W'
        }
      : m
  )

  myMachine.value = {
    claimed: true,
    id: machine.id,
    name: machine.name,
    location: machine.location,
    isOn: true,
    runningMinutes: 1,
    powerDraw: machine.type === 'dryer' ? '1800W' : '310W',
    startedAt: startTime,
    notifyWhenOff: true
  }

  showToast(`Claimed & booked ${machine.name}! Duration meter started 🧼`)
  activeTab.value = 'home'

  try {
    await $fetch(`${apiBase}/api/machines/${machine.id}/claim`, {
      method: 'POST',
      body: { user_id: 'akshat-student', duration_minutes: 45 }
    })
  } catch (e) {
    // Offline local state already updated
  }
}

// Release active load
const handleReleaseMachine = async () => {
  const machineId = myMachine.value.id

  if (machineId) {
    machines.value = machines.value.map((m) =>
      m.id === machineId
        ? { ...m, isOn: false, status: 'available', runningMinutes: 0, powerDraw: '0W' }
        : m
    )
  }

  myMachine.value = {
    claimed: false,
    id: null,
    name: '',
    location: '',
    isOn: false,
    runningMinutes: 0,
    powerDraw: '0W',
    startedAt: '',
    notifyWhenOff: false
  }

  showToast('Released machine. Marked as available.')

  if (machineId) {
    try {
      await $fetch(`${apiBase}/api/machines/${machineId}/clear`, {
        method: 'POST',
        body: { user_id: 'akshat-student' }
      })
    } catch (e) {
      // Offline local state already updated
    }
  }
}

// Inline Buzz / Nudge Trigger
const handleSendBuzz = async (machineId, machineName, isUncollected = false) => {
  machines.value = machines.value.map((m) =>
    m.id === machineId
      ? { ...m, nudgesSent: (m.nudgesSent || 0) + 1, myBuzzed: true }
      : m
  )

  if (isUncollected) {
    showToast(`Friendly reminder sent to ${machineName}'s owner to collect clothes 🧺`)
  } else {
    showToast(`Buzzed ${machineName}! Resident notified to check their load ⚡`)
  }

  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/ping`, {
      method: 'POST',
      body: { user_id: 'akshat-student', target: 'occupant' }
    })
  } catch (e) {
    // Offline local state already updated
  }
}

// Helper to switch filter and tab simultaneously
const setFilterAndNavigate = (type) => {
  filterType.value = type
  activeTab.value = 'machines'
}

// Calculated Summary Stats
const freeMachinesCount = computed(() => machines.value.filter((m) => m.status === 'available').length)
const runningMachinesCount = computed(() => machines.value.filter((m) => m.status === 'in-use').length)
const uncollectedCount = computed(() => machines.value.filter((m) => m.status === 'uncollected').length)

// Filtered Machines List
const filteredMachines = computed(() => {
  return machines.value.filter((m) => {
    if (filterType.value === 'washers') return m.type === 'washer'
    if (filterType.value === 'dryers') return m.type === 'dryer'
    if (filterType.value === 'free') return m.status === 'available'
    if (filterType.value === 'uncollected') return m.status === 'uncollected'
    return true
  })
})

// =========================================================================
// 4-HOUR POWER CONSUMPTION GRAPH POPUP (Tapping Machine Card)
// =========================================================================
const isPowerGraphOpen = ref(false)
const selectedMachineForGraph = ref(null)
const machinePowerHistory = ref(null)
const historyLoading = ref(false)

// Open 4-hour Power Consumption Graph on Card Tap
const openMachinePowerGraph = async (machine) => {
  selectedMachineForGraph.value = machine
  isPowerGraphOpen.value = true
  historyLoading.value = true
  machinePowerHistory.value = null

  try {
    const data = await $fetch(`${apiBase}/api/machines/${machine.id}/power-history?hours=4`)
    if (data && data.series && data.series.length > 0) {
      machinePowerHistory.value = data
    } else {
      machinePowerHistory.value = generateSimulatedPowerHistory(machine)
    }
  } catch (err) {
    machinePowerHistory.value = generateSimulatedPowerHistory(machine)
  } finally {
    historyLoading.value = false
  }
}

// Generate realistic 4-hour telemetry time-series curve for machines
const generateSimulatedPowerHistory = (machine) => {
  const now = Date.now()
  const fourHoursMs = 4 * 60 * 60 * 1000
  const points = []
  const stepMs = 3 * 60 * 1000 // every 3 minutes = 80 data points
  const isRunning = machine.isOn || machine.status === 'in-use'
  const isDryer = machine.type === 'dryer' || machine.name?.toLowerCase().includes('dryer')
  const basePeak = isDryer ? 1750 : 340

  let t = now - fourHoursMs
  while (t <= now) {
    const minutesAgo = Math.round((now - t) / 60000)
    let powerW = 0.0

    if (isRunning && minutesAgo <= (machine.runningMinutes || 28)) {
      // Active wash cycle happening right now
      const phase = minutesAgo % 12
      if (phase < 3) powerW = Math.round(basePeak * 0.9 + Math.random() * 30) // Motor agitation
      else if (phase < 5) powerW = Math.round(basePeak * 0.15 + Math.random() * 15) // Soak
      else if (phase < 9) powerW = Math.round(basePeak * 0.98 + Math.random() * 25) // High-speed spin
      else powerW = Math.round(basePeak * 0.45 + Math.random() * 20) // Rinse
    } else if (minutesAgo >= 110 && minutesAgo <= 170) {
      // Prior cycle 2-3 hours ago
      const phase = minutesAgo % 10
      if (phase < 6) powerW = Math.round(basePeak * 0.85 + Math.random() * 40)
      else powerW = Math.round(5 + Math.random() * 10)
    } else {
      // Off / Standby state
      powerW = Math.random() < 0.15 ? Math.round(1.5 + Math.random() * 1.5) : 0.0
    }

    points.push({
      timestamp: new Date(t).toISOString(),
      power_w: powerW,
      voltage_v: Math.round(230 + Math.random() * 8),
      current_ma: Math.round(powerW > 0 ? (powerW / 230) * 1000 : 0),
      source: 'local'
    })
    t += stepMs
  }

  const powers = points.map(p => p.power_w)
  const peak = Math.max(...powers, 10)
  const avg = powers.reduce((a, b) => a + b, 0) / powers.length

  return {
    plug_id: machine.id,
    plug_name: `${machine.name} • Smart Plug Node`,
    hours: 4,
    peak_power_w: Math.round(peak),
    avg_power_w: Math.round(avg),
    local_points_count: points.length,
    cloud_points_count: 0,
    series: points
  }
}

// Real-time Local Edge WebSocket live stream listener
const { isConnected: isWsConnected } = useLocalWebSocket(apiBase, (event) => {
  if (event.type === 'telemetry_update' && event.plug_id) {
    // Append dynamically to 4-hour graph if open
    if (isPowerGraphOpen.value && machinePowerHistory.value) {
      const newPt = {
        timestamp: event.telemetry.recorded_at,
        power_w: event.telemetry.power_w || 0.0,
        voltage_v: event.telemetry.voltage_v,
        current_ma: event.telemetry.current_ma,
        source: event.telemetry.source || 'local'
      }
      machinePowerHistory.value.series.push(newPt)
      machinePowerHistory.value.local_points_count++
      if (newPt.power_w > machinePowerHistory.value.peak_power_w) {
        machinePowerHistory.value.peak_power_w = newPt.power_w
      }
    }
  } else if (event.type === 'machine_status_change') {
    fetchBackendData()
  }
})
</script>

<template>
  <div
    :class="[
      'min-h-screen flex flex-col md:flex-row font-sans antialiased transition-colors duration-200',
      darkMode ? 'bg-[#0c0e14] text-slate-100' : 'bg-[#f6f8fa] text-slate-900'
    ]"
  >
    <!-- Floating Toast Notification -->
    <div
      v-if="toast"
      class="fixed top-5 right-5 z-50 bg-[#161a22] text-white px-5 py-3 rounded-full text-xs font-semibold shadow-2xl flex items-center gap-2.5 animate-bounce border border-white/15"
    >
      <CheckCircle2 class="w-4 h-4 text-emerald-400 shrink-0" />
      <span class="tracking-tight text-white">{{ toast }}</span>
    </div>

    <!-- 1. DESKTOP LEFT SIDEBAR -->
    <AppSidebar
      :active-tab="activeTab"
      :free-machines-count="freeMachinesCount"
      :my-machine="myMachine"
      :dark-mode="darkMode"
      @update:active-tab="activeTab = $event"
      @open-settings="showSettings = true"
      @set-theme="setTheme($event)"
    />

    <!-- RIGHT COLUMN: TOP HEADER + MAIN CONTENT -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 2. TOP HEADER (Mobile & Desktop) -->
      <AppTopHeader
        :active-tab="activeTab"
        :my-machine="myMachine"
        :dark-mode="darkMode"
        :formatted-date="formattedDate"
        @open-settings="showSettings = true"
        @view-profile="activeTab = 'profile'"
        @notify-click="showToast('Smart plug telemetry updated seconds ago')"
      />

      <!-- MAIN CONTENT DASHBOARD -->
      <main class="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 lg:p-10 pb-24 md:pb-10">
        <div class="max-w-6xl mx-auto space-y-6">

          <!-- Dynamic Page Title Banner -->
          <div>
            <h2 class="text-xl sm:text-2xl font-black tracking-tight text-slate-900 dark:text-white">
              {{ activeTab === 'home' ? 'Here’s your active laundry status' : activeTab === 'machines' ? 'Hostel Laundry Appliances' : 'Resident Profile' }}
            </h2>
            <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              {{ activeTab === 'home' ? 'Monitor active cycles and room availability in real time' : activeTab === 'machines' ? 'Block B • 2nd Floor • Claim free units or nudge finished loads' : 'Room 214 • Block B Resident Info & Protocol' }}
            </p>
          </div>

          <!-- TAB 1: HOME VIEW -->
          <div v-if="activeTab === 'home'" class="space-y-6 animate-fadeIn">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <!-- 3. Hero Active Machine (Cols 1-7) -->
              <div class="lg:col-span-7">
                <HomeHeroMachine
                  :my-machine="myMachine"
                  :dark-mode="darkMode"
                  @release-machine="handleReleaseMachine"
                  @browse-machines="activeTab = 'machines'"
                  @toggle-notify="showToast(myMachine.notifyWhenOff ? 'Notification already set for 0W motor shutdown 🔔' : 'Alert configured!')"
                  @view-history="openMachinePowerGraph"
                />
              </div>

              <!-- 4. Overview Cards (Cols 8-12) -->
              <div class="lg:col-span-5">
                <OverviewCards
                  :free-machines-count="freeMachinesCount"
                  :running-machines-count="runningMachinesCount"
                  :uncollected-count="uncollectedCount"
                  :dark-mode="darkMode"
                  @navigate-filter="setFilterAndNavigate($event)"
                  @view-appliances="activeTab = 'machines'"
                />
              </div>
            </div>
          </div>

          <!-- TAB 2: APPLIANCES HUB VIEW -->
          <div v-else-if="activeTab === 'machines'" class="space-y-6 animate-fadeIn">
            <!-- Filter Bar -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 class="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
                  All Available & In-Use Units
                </h3>
                <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                  Claim free units or send polite peer buzzes for finished loads
                </p>
              </div>

              <!-- Filter Pills -->
              <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
                <button
                  v-for="f in filterTabs"
                  :key="f.id"
                  @click="filterType = f.id"
                  :class="[
                    'px-4 py-2 rounded-full text-xs font-bold transition-all whitespace-nowrap',
                    filterType === f.id
                      ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
                      : darkMode
                      ? 'bg-slate-800 text-slate-400 hover:text-white'
                      : 'bg-white border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-2xs'
                  ]"
                >
                  {{ f.label }}
                </button>
              </div>
            </div>

            <!-- 5. 6-Machine Appliances Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
              <ApplianceCard
                v-for="machine in filteredMachines"
                :key="machine.id"
                :machine="machine"
                :is-my-machine="myMachine.claimed && myMachine.id === machine.id"
                :dark-mode="darkMode"
                @claim="handleClaimMachine"
                @buzz="handleSendBuzz"
                @view-history="openMachinePowerGraph"
              />
            </div>
          </div>

          <!-- TAB 3: RESIDENT PROFILE VIEW -->
          <div v-else-if="activeTab === 'profile'">
            <!-- 6. Resident Profile Component -->
            <ResidentProfileView
              :my-machine="myMachine"
              :dark-mode="darkMode"
            />
          </div>

        </div>
      </main>
    </div>

    <!-- 7. MOBILE BOTTOM FLOATING DOCK -->
    <MobileBottomNav
      :active-tab="activeTab"
      :free-machines-count="freeMachinesCount"
      :dark-mode="darkMode"
      @update:active-tab="activeTab = $event"
    />

    <!-- 8. SETTINGS POPUP MODAL -->
    <SettingsModal
      :show-settings="showSettings"
      :dark-mode="darkMode"
      :push-alert-enabled="pushAlertEnabled"
      :anonymous-buzz-enabled="anonymousBuzzEnabled"
      @close="showSettings = false"
      @set-theme="setTheme($event)"
      @update:push-alert-enabled="pushAlertEnabled = $event; showToast(pushAlertEnabled ? 'Alerts enabled' : 'Alerts disabled')"
      @update:anonymous-buzz-enabled="anonymousBuzzEnabled = $event"
    />

    <!-- 9. 4-HOUR POWER CONSUMPTION GRAPH POPUP (Tapping Machine Card) -->
    <PowerGraphModal
      :is-open="isPowerGraphOpen"
      :title="selectedMachineForGraph?.name"
      :subtitle="selectedMachineForGraph?.location || 'Block B • 2nd Floor'"
      :plug="selectedMachineForGraph"
      :history="machinePowerHistory"
      :loading="historyLoading"
      :dark-mode="darkMode"
      @close="isPowerGraphOpen = false"
    />
  </div>
</template>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
