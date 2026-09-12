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
import MachineStatusModal from '~/components/hub/MachineStatusModal.vue'

// Configuration & Theme
const config = useRuntimeConfig()
const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'

// Persistent Theme Synchronization
const { isDark: darkMode, toggleTheme, setTheme } = useAppTheme()

// Localized Timezone Management
const {
  formatDate,
  formatTime,
  parseToUtcDate,
  getTimezoneAbbr
} = useAppTimezone()

// Navigation & Modal State
const activeTab = ref('home') // 'home' | 'machines' | 'profile'
const showSettings = ref(false)
const toast = ref(null)
const filterType = ref('all') // 'all' | 'washers' | 'dryers' | 'free' | 'uncollected'
const pushAlertEnabled = ref(true)
const anonymousBuzzEnabled = ref(true)

// Helper to humanize cycle stage from power and elapsed time
const getCycleStageInfo = (powerW, elapsedMin, isUncollected = false) => {
  if (isUncollected) {
    return {
      stage: '🧺 Cycle Finished • Uncollected',
      badgeClass: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20',
      remainingMin: 0
    }
  }
  const remaining = Math.max(0, 45 - (elapsedMin || 0))

  if (powerW >= 150.0) {
    return {
      stage: '🌀 Washing & Agitating',
      badgeClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
      remainingMin: remaining
    }
  } else if (powerW >= 5.0 && powerW < 150.0) {
    return {
      stage: '💧 Water Fill / Rinse',
      badgeClass: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20',
      remainingMin: remaining
    }
  } else if (powerW > 0.0 && powerW < 5.0) {
    return {
      stage: '⏳ Soaking Pause',
      badgeClass: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
      remainingMin: remaining
    }
  } else {
    return {
      stage: elapsedMin > 35 ? '💨 Final Spin Down' : '⏳ Soaking Pause',
      badgeClass: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20',
      remainingMin: remaining
    }
  }
}

// User's Claimed Active Appliance
const myMachine = ref({
  claimed: false,
  id: null,
  name: '',
  location: 'Block B • 2nd Floor',
  isOn: false,
  runningMinutes: 0,
  cycleStage: '🌀 Active Washing',
  stageBadgeClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
  remainingMinutes: 30,
  startedAt: '',
  notifyWhenOff: false
})

// State of all appliances with inline buzz counters & smart telemetry
const machines = ref([])

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
  return formatDate(new Date())
})

// Synchronize machine status and active bookings with backend API
const fetchBackendData = async () => {
  try {
    const data = await $fetch(`${apiBase}/api/machines`)
    if (data && Array.isArray(data)) {
      machines.value = data.map((m) => {
        const powerW = m.latest_power_w ?? 0
        const isRunning = m.status === 'in_use' || powerW >= 10.0
        const isUncollected = m.status === 'idle_full' || m.status === 'uncollected'
        
        let elapsed = 0
        if (m.active_booking?.started_at) {
          const startedUtc = parseToUtcDate(m.active_booking.started_at)
          if (startedUtc) {
            elapsed = Math.max(0, Math.floor((Date.now() - startedUtc.getTime()) / 60000))
          }
        }

        const stageInfo = getCycleStageInfo(powerW, elapsed, isUncollected)

        return {
          id: m.id,
          name: m.name,
          type: m.type || (m.name.toLowerCase().includes('dryer') ? 'dryer' : 'washer'),
          location: m.location || 'Block B • 2nd Floor',
          isOn: isRunning,
          status: isUncollected ? 'uncollected' : isRunning ? 'in-use' : 'available',
          runningMinutes: elapsed,
          cycleStage: stageInfo.stage,
          stageBadgeClass: stageInfo.badgeClass,
          remainingMinutes: stageInfo.remainingMin,
          finishedAgoMin: isUncollected ? (m.finished_ago_min || 0) : undefined,
          powerDraw: `${powerW.toFixed(0)}W`,
          nudgesSent: m.nudges_sent ?? 0,
          myBuzzed: false,
          active_booking: m.active_booking,
          queue: m.queue || []
        }
      })

      // Keep opened detail modal in sync
      if (isDetailModalOpen.value && selectedMachineForDetail.value) {
        selectedMachineForDetail.value = machines.value.find(m => m.id === selectedMachineForDetail.value.id) || selectedMachineForDetail.value
      }

      // Check if current user has an active booking on any machine
      const storedUser = typeof localStorage !== 'undefined' ? localStorage.getItem('washqueue_student_user') : null
      let currentUserId = null
      try {
        if (storedUser) currentUserId = JSON.parse(storedUser)?.id
      } catch (e) {}

      const prevWasRunning = myMachine.value.claimed && myMachine.value.isOn

      const myActiveMachine = data.find(m => m.active_booking && currentUserId && m.active_booking.user_id === currentUserId)
      if (myActiveMachine && myActiveMachine.active_booking) {
        const startedUtc = parseToUtcDate(myActiveMachine.active_booking.started_at)
        const elapsedMin = startedUtc ? Math.max(0, Math.floor((Date.now() - startedUtc.getTime()) / 60000)) : 0
        const pwr = myActiveMachine.latest_power_w ?? 0
        const isUncoll = myActiveMachine.status === 'idle_full' || myActiveMachine.status === 'uncollected'
        const stageInfo = getCycleStageInfo(pwr, elapsedMin, isUncoll)
        myMachine.value = {
          claimed: true,
          id: myActiveMachine.id,
          name: myActiveMachine.name,
          location: 'Block B • 2nd Floor',
          isOn: myActiveMachine.status === 'in_use' || pwr >= 10.0,
          runningMinutes: elapsedMin,
          cycleStage: stageInfo.stage,
          stageBadgeClass: stageInfo.badgeClass,
          remainingMinutes: stageInfo.remainingMin,
          powerDraw: `${pwr.toFixed(0)}W`,
          startedAt: formatTime(startedUtc),
          notifyWhenOff: true
        }

        // Completion alert prompt for resident
        if (prevWasRunning && !myMachine.value.isOn && pushAlertEnabled.value) {
          showToast('🧺 Your laundry is done! Please collect within 15 minutes to avoid being buzzed.')
        }
      } else if (!myMachine.value.id || !data.some(m => m.id === myMachine.value.id && m.active_booking)) {
        myMachine.value.claimed = false
      }
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
      myMachine.value.remainingMinutes = Math.max(0, 45 - myMachine.value.runningMinutes)
    }

    machines.value = machines.value.map((m) => {
      if (m.isOn) {
        const nextRun = m.runningMinutes + 1
        return {
          ...m,
          runningMinutes: nextRun,
          remainingMinutes: Math.max(0, 45 - nextRun)
        }
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

const getCurrentUser = () => {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem('washqueue_student_user')
    return raw ? JSON.parse(raw) : null
  } catch (e) {
    return null
  }
}

// Claim & Book an available machine
const handleClaimMachine = async (machine) => {
  const currentUser = getCurrentUser()
  if (!currentUser || !currentUser.id) {
    showToast('Please sign in to claim a machine.')
    navigateTo('/login')
    return
  }

  const startTime = formatTime(new Date())
  const stageInfo = getCycleStageInfo(250.0, 1)

  machines.value = machines.value.map((m) =>
    m.id === machine.id
      ? {
          ...m,
          isOn: true,
          status: 'in-use',
          runningMinutes: 1,
          cycleStage: stageInfo.stage,
          stageBadgeClass: stageInfo.badgeClass,
          remainingMinutes: 44,
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
    cycleStage: stageInfo.stage,
    stageBadgeClass: stageInfo.badgeClass,
    remainingMinutes: 44,
    powerDraw: machine.type === 'dryer' ? '1800W' : '310W',
    startedAt: startTime,
    notifyWhenOff: true
  }

  showToast(`Claimed & booked ${machine.name}! Duration meter started 🧼`)
  activeTab.value = 'home'

  try {
    await $fetch(`${apiBase}/api/machines/${machine.id}/claim`, {
      method: 'POST',
      body: { user_id: currentUser.id, duration_minutes: 45 }
    })
  } catch (e) {
    // Offline local state already updated
  }
}

// Release active load
const handleReleaseMachine = async () => {
  const machineId = myMachine.value.id
  const currentUser = getCurrentUser()

  if (machineId) {
    machines.value = machines.value.map((m) =>
      m.id === machineId
        ? {
            ...m,
            isOn: false,
            status: 'available',
            runningMinutes: 0,
            cycleStage: '',
            remainingMinutes: 0,
            powerDraw: '0W'
          }
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
    cycleStage: '🌀 Active Washing',
    stageBadgeClass: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20',
    remainingMinutes: 0,
    powerDraw: '0W',
    startedAt: '',
    notifyWhenOff: false
  }

  showToast('Released machine. Marked as available.')

  if (machineId && currentUser?.id) {
    try {
      await $fetch(`${apiBase}/api/machines/${machineId}/clear`, {
        method: 'POST',
        body: { user_id: currentUser.id }
      })
    } catch (e) {
      // Offline local state already updated
    }
  }
}

// Inline Buzz / Nudge Trigger
const handleSendBuzz = async (machineId, machineName, isUncollected = false) => {
  const currentUser = getCurrentUser()

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
      body: { user_id: currentUser?.id, target: 'occupant' }
    })
  } catch (e) {
    // Offline local state already updated
  }
}

// Machine Status Drawer / Modal State
const selectedMachineForDetail = ref(null)
const isDetailModalOpen = ref(false)

const openMachineDetail = (machine) => {
  selectedMachineForDetail.value = machine
  isDetailModalOpen.value = true
}

// Join / Leave Virtual Waitlist Queue
const handleJoinQueue = async (machine) => {
  const currentUser = getCurrentUser()
  if (!currentUser || !currentUser.id) {
    showToast('Please sign in to join the waitlist.')
    navigateTo('/login')
    return
  }

  try {
    await $fetch(`${apiBase}/api/machines/${machine.id}/queue/join`, {
      method: 'POST',
      body: { user_id: currentUser.id }
    })
    showToast(`Joined waitlist for ${machine.name}! You'll be alerted when free 📋`)
    await fetchBackendData()
    if (selectedMachineForDetail.value?.id === machine.id) {
      selectedMachineForDetail.value = machines.value.find(m => m.id === machine.id) || selectedMachineForDetail.value
    }
  } catch (err) {
    const msg = err?.data?.detail || 'Could not join waitlist'
    showToast(msg)
  }
}

const handleLeaveQueue = async (machine) => {
  const currentUser = getCurrentUser()
  if (!currentUser || !currentUser.id) return

  try {
    await $fetch(`${apiBase}/api/machines/${machine.id}/queue/leave`, {
      method: 'POST',
      body: { user_id: currentUser.id }
    })
    showToast(`Left waitlist for ${machine.name}.`)
    await fetchBackendData()
    if (selectedMachineForDetail.value?.id === machine.id) {
      selectedMachineForDetail.value = machines.value.find(m => m.id === machine.id) || selectedMachineForDetail.value
    }
  } catch (err) {
    const msg = err?.data?.detail || 'Could not leave waitlist'
    showToast(msg)
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

// Real-time Local Edge WebSocket live stream listener
const { isConnected: isWsConnected } = useLocalWebSocket(apiBase, (event) => {
  if (event.type === 'telemetry_update' && event.plug_id) {
    const powerW = event.telemetry?.power_w || 0.0
    // Dynamically update cycle stages on active machines
    machines.value = machines.value.map((m) => {
      if (m.id === event.plug_id && m.isOn) {
        const stageInfo = getCycleStageInfo(powerW, m.runningMinutes, m.status === 'uncollected')
        return {
          ...m,
          cycleStage: stageInfo.stage,
          stageBadgeClass: stageInfo.badgeClass
        }
      }
      return m
    })
    if (myMachine.value.claimed && myMachine.value.id === event.plug_id) {
      const stageInfo = getCycleStageInfo(powerW, myMachine.value.runningMinutes)
      myMachine.value.cycleStage = stageInfo.stage
      myMachine.value.stageBadgeClass = stageInfo.badgeClass
    }
    if (isDetailModalOpen.value && selectedMachineForDetail.value?.id === event.plug_id) {
      selectedMachineForDetail.value = machines.value.find(m => m.id === event.plug_id) || selectedMachineForDetail.value
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
                  @toggle-notify="showToast(myMachine.notifyWhenOff ? 'Notification already set for completion 🔔' : 'Alert configured!')"
                  @view-details="openMachineDetail(machines.find(m => m.id === myMachine.id) || myMachine)"
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
                @select="openMachineDetail"
                @claim="handleClaimMachine"
                @buzz="handleSendBuzz"
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

    <!-- 9. RESIDENT MACHINE STATUS & WAITLIST DRAWER/MODAL -->
    <MachineStatusModal
      :is-open="isDetailModalOpen"
      :machine="selectedMachineForDetail"
      :is-my-machine="myMachine.claimed && myMachine.id === selectedMachineForDetail?.id"
      :dark-mode="darkMode"
      :current-user="getCurrentUser()"
      @close="isDetailModalOpen = false"
      @claim="handleClaimMachine"
      @buzz="handleSendBuzz"
      @release="handleReleaseMachine"
      @join-queue="handleJoinQueue"
      @leave-queue="handleLeaveQueue"
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
