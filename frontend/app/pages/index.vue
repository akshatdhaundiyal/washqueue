<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl

// Mock users for local testing
const mockUsers = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Alex', room: 'Room 304', avatar: '🧑‍💻' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Blake', room: 'Room 102', avatar: '👩‍🔬' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Charlie', room: 'Room 215', avatar: '👨‍🎨' }
]

// App state
const currentUser = ref(mockUsers[0])
const machines = ref([])
const loading = ref(true)
const errorMsg = ref('')

// Filter state
const activeTab = ref('all') // 'all', 'washers', 'dryers', 'available', 'my'

// Toast notifications
const toasts = ref([])
const addToast = (message, type = 'info') => {
  const id = Date.now()
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 6000)
}

// Timer logic: update client time every second
const now = ref(Date.now())
let timerInterval = null

onMounted(() => {
  timerInterval = setInterval(() => {
    now.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})

// Fetch machines from FastAPI
const fetchMachines = async () => {
  try {
    const data = await $fetch(`${apiBase}/api/machines`)
    machines.value = data
    errorMsg.value = ''
  } catch (err) {
    console.error('Failed to fetch machines:', err)
    errorMsg.value = 'Failed to connect to the WashQueue local backend.'
  } finally {
    loading.value = false
  }
}

// Local Edge WebSocket integration
const { isConnected: isWsConnected } = useLocalWebSocket(apiBase, (event) => {
  if (event.type === 'machine_status_change' || event.type === 'machine_update') {
    fetchMachines()
  }
})

// Supabase Realtime Subscriptions (Cloud fallback)
const { $supabase } = useNuxtApp()
let dbChannel = null
let broadcastChannel = null

const setupRealtime = () => {
  if (!$supabase) return

  dbChannel = $supabase
    .channel('laundry_db_changes')
    .on('postgres_changes', { event: '*', schema: 'public', table: 'machines' }, () => {
      fetchMachines()
    })
    .on('postgres_changes', { event: '*', schema: 'public', table: 'bookings' }, () => {
      fetchMachines()
    })
    .on('postgres_changes', { event: '*', schema: 'public', table: 'queue' }, () => {
      fetchMachines()
    })
    .subscribe()

  broadcastChannel = $supabase.channel('laundry_broadcast')
  broadcastChannel
    .on('broadcast', { event: 'ping_alert' }, ({ payload }) => {
      if (payload.targetUserId === currentUser.value.id) {
        addToast(`📢 Ping! Another student is waiting for "${payload.machineName}". Please clear your laundry!`, 'warning')
      }
    })
    .subscribe()
}

onMounted(() => {
  fetchMachines()
  setupRealtime()
})

onUnmounted(() => {
  if (dbChannel && $supabase) $supabase.removeChannel(dbChannel)
  if (broadcastChannel && $supabase) $supabase.removeChannel(broadcastChannel)
})

// Owner & Queue helpers
const isOwner = (machine) => {
  return machine.active_booking && machine.active_booking.user_id === currentUser.value.id
}

const getQueuePosition = (machine) => {
  const idx = machine.queue.findIndex(q => q.user_id === currentUser.value.id)
  return idx !== -1 ? idx + 1 : null
}

const isNotified = (machine) => {
  const entry = machine.queue.find(q => q.user_id === currentUser.value.id)
  return entry && entry.status === 'notified'
}

const getSecondsRemaining = (estimatedEndAt) => {
  const diff = new Date(estimatedEndAt).getTime() - now.value
  return diff <= 0 ? 0 : Math.floor(diff / 1000)
}

const formatTime = (seconds) => {
  const mm = Math.floor(seconds / 60).toString().padStart(2, '0')
  const ss = (seconds % 60).toString().padStart(2, '0')
  return `${mm}:${ss}`
}

// Filtered Machines Computed
const filteredMachines = computed(() => {
  if (activeTab.value === 'washers') {
    return machines.value.filter(m => m.name.toLowerCase().includes('washer'))
  }
  if (activeTab.value === 'dryers') {
    return machines.value.filter(m => m.name.toLowerCase().includes('dryer'))
  }
  if (activeTab.value === 'available') {
    return machines.value.filter(m => m.status === 'available')
  }
  if (activeTab.value === 'my') {
    return machines.value.filter(isOwner)
  }
  return machines.value
})

// API Actions
const claimMachine = async (machineId) => {
  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/claim`, {
      method: 'POST',
      body: { user_id: currentUser.value.id }
    })
    addToast('Machine claimed successfully! Cycle started.', 'success')
    fetchMachines()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to claim machine.', 'error')
  }
}

const clearMachine = async (machineId) => {
  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/clear`, {
      method: 'POST'
    })
    addToast('Machine cleared and is now available.', 'success')
    fetchMachines()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to clear machine.', 'error')
  }
}

const pingOwner = async (machineId) => {
  try {
    const res = await $fetch(`${apiBase}/api/machines/${machineId}/ping`, {
      method: 'POST',
      body: { user_id: currentUser.value.id }
    })
    if (broadcastChannel && res.owner_user_id) {
      broadcastChannel.send({
        type: 'broadcast',
        event: 'ping_alert',
        payload: {
          targetUserId: res.owner_user_id,
          machineName: res.machine_name
        }
      })
    }
    addToast('Owner has been pinged anonymously!', 'success')
  } catch (err) {
    addToast(err.data?.detail || 'Failed to ping owner.', 'error')
  }
}

const joinQueue = async (machineId) => {
  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/queue/join`, {
      method: 'POST',
      body: { user_id: currentUser.value.id }
    })
    addToast('Joined the waitlist queue.', 'success')
    fetchMachines()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to join queue.', 'error')
  }
}

const leaveQueue = async (machineId) => {
  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/queue/leave`, {
      method: 'POST',
      body: { user_id: currentUser.value.id }
    })
    addToast('Left the waitlist queue.', 'success')
    fetchMachines()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to leave queue.', 'error')
  }
}

const triggerSchedulerTick = async () => {
  try {
    const res = await $fetch(`${apiBase}/api/scheduler/tick`, { method: 'POST' })
    if (res.updated_count > 0) {
      addToast(`Scheduler updated ${res.updated_count} machine(s) to Idle-Full.`, 'success')
    } else {
      addToast('Scheduler tick: No overdue machines found.', 'info')
    }
    fetchMachines()
  } catch (err) {
    addToast('Failed to trigger scheduler tick.', 'error')
  }
}
</script>

<template>
  <div class="stitch-app min-h-screen bg-[#090D16] text-[#dfe2ef] selection:bg-[#10b981] selection:text-black">
    <!-- Top Header -->
    <header class="bg-[#090D16]/80 backdrop-blur-xl border-b border-white/10 sticky top-0 w-full z-50 px-6 py-4">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        <!-- Logo & Title -->
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-[#10b981]/10 border border-[#10b981]/30 flex items-center justify-center text-2xl shadow-[0_0_15px_rgba(16,185,129,0.3)]">
            🌀
          </div>
          <div>
            <h1 class="text-xl font-bold font-mono tracking-tight text-white flex items-center gap-2">
              WASHQUEUE
              <span 
                class="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded-full border"
                :class="isWsConnected ? 'bg-[#10b981]/10 text-[#4edea3] border-[#10b981]/30' : 'bg-sky-500/10 text-sky-400 border-sky-500/30'"
              >
                {{ isWsConnected ? '🟢 Hostel LAN (WebSocket)' : '☁️ Remote Mobile' }}
              </span>
            </h1>
            <p class="text-xs text-[#86948a] font-mono">Neural Interface // Local IoT Telemetry</p>
          </div>
        </div>

        <!-- Controls & Navigation -->
        <div class="flex flex-wrap items-center gap-3">
          <!-- Active User Selector -->
          <div class="glass-card px-3 py-1.5 rounded-xl border border-white/10 flex items-center gap-2">
            <span class="text-xs text-[#86948a] font-mono font-medium">Student:</span>
            <select 
              v-model="currentUser"
              class="bg-transparent border-none text-sm font-mono font-semibold text-white focus:outline-none cursor-pointer"
            >
              <option v-for="user in mockUsers" :key="user.id" :value="user" class="bg-[#0f131c] text-white">
                {{ user.avatar }} {{ user.name }} ({{ user.room }})
              </option>
            </select>
          </div>

          <!-- Scheduler Tick -->
          <button 
            @click="triggerSchedulerTick" 
            class="glass-card px-3 py-2 rounded-xl text-xs font-mono font-semibold hover:border-[#10b981]/40 transition active:scale-95 flex items-center gap-1.5"
          >
            ⏱️ Tick Scheduler
          </button>

          <!-- Admin Portal Link -->
          <NuxtLink 
            to="/admin" 
            class="bg-[#10b981]/20 hover:bg-[#10b981]/30 border border-[#10b981]/40 text-[#4edea3] px-3.5 py-2 rounded-xl text-xs font-mono font-bold uppercase tracking-wider transition flex items-center gap-1.5"
          >
            🔒 Admin Portal
          </NuxtLink>
        </div>
      </div>
    </header>

    <!-- Main Content Canvas -->
    <main class="max-w-7xl mx-auto px-6 pt-8 pb-16">
      <!-- Error Message Banner -->
      <div v-if="errorMsg" class="glass-card border-rose-500/40 bg-rose-950/20 text-rose-300 rounded-2xl p-4 mb-6 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="text-xl">⚠️</span>
          <p class="text-sm font-mono">{{ errorMsg }}</p>
        </div>
        <button @click="fetchMachines" class="bg-rose-500/20 hover:bg-rose-500/30 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition">Retry Connection</button>
      </div>

      <!-- Loading Spinner -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-24 gap-4">
        <div class="w-12 h-12 border-4 border-[#10b981] border-t-transparent rounded-full animate-spin"></div>
        <p class="text-[#86948a] font-mono text-sm animate-pulse">Syncing smart plug telemetry & machine nodes...</p>
      </div>

      <!-- Main Dashboard Content -->
      <div v-else>
        <!-- Metric Summary Grid (4 Stat Cards) -->
        <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <!-- Stat Card 1: Available -->
          <div class="glass-card rounded-2xl p-5 glow-emerald relative overflow-hidden">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono text-[#86948a] uppercase tracking-wider">Available Machines</span>
              <span class="text-emerald-400 text-lg">🟢</span>
            </div>
            <p class="text-3xl font-mono font-bold text-[#4edea3] mt-2">
              {{ machines.filter(m => m.status === 'available').length }} / {{ machines.length }}
            </p>
          </div>

          <!-- Stat Card 2: Running -->
          <div class="glass-card rounded-2xl p-5 glow-rose relative overflow-hidden">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono text-[#86948a] uppercase tracking-wider">Currently Running</span>
              <span class="text-rose-400 text-lg animate-spin">🌀</span>
            </div>
            <p class="text-3xl font-mono font-bold text-[#ffb2b7] mt-2">
              {{ machines.filter(m => m.status === 'in_use').length }}
            </p>
          </div>

          <!-- Stat Card 3: Idle Full -->
          <div class="glass-card rounded-2xl p-5 glow-amber relative overflow-hidden">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono text-[#86948a] uppercase tracking-wider">Idle & Full (Unload)</span>
              <span class="text-amber-400 text-lg">🧺</span>
            </div>
            <p class="text-3xl font-mono font-bold text-[#fbbf24] mt-2">
              {{ machines.filter(m => m.status === 'idle_full').length }}
            </p>
          </div>

          <!-- Stat Card 4: My Cycles -->
          <div class="glass-card rounded-2xl p-5 glow-indigo relative overflow-hidden">
            <div class="flex items-center justify-between">
              <span class="text-xs font-mono text-[#86948a] uppercase tracking-wider">My Active Cycles</span>
              <span class="text-indigo-400 text-lg">🧑‍💻</span>
            </div>
            <p class="text-3xl font-mono font-bold text-[#c0c1ff] mt-2">
              {{ machines.filter(isOwner).length }}
            </p>
          </div>
        </section>

        <!-- Filter Tabs -->
        <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div class="flex items-center gap-2 bg-[#181b25] p-1.5 rounded-xl border border-white/10">
            <button 
              @click="activeTab = 'all'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
              :class="activeTab === 'all' ? 'bg-[#10b981] text-[#003824] shadow' : 'text-[#86948a] hover:text-white'"
            >
              All ({{ machines.length }})
            </button>
            <button 
              @click="activeTab = 'washers'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
              :class="activeTab === 'washers' ? 'bg-[#10b981] text-[#003824] shadow' : 'text-[#86948a] hover:text-white'"
            >
              Washers
            </button>
            <button 
              @click="activeTab = 'dryers'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
              :class="activeTab === 'dryers' ? 'bg-[#10b981] text-[#003824] shadow' : 'text-[#86948a] hover:text-white'"
            >
              Dryers
            </button>
            <button 
              @click="activeTab = 'available'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
              :class="activeTab === 'available' ? 'bg-[#10b981] text-[#003824] shadow' : 'text-[#86948a] hover:text-white'"
            >
              Available
            </button>
            <button 
              @click="activeTab = 'my'"
              class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
              :class="activeTab === 'my' ? 'bg-[#10b981] text-[#003824] shadow' : 'text-[#86948a] hover:text-white'"
            >
              My Laundry
            </button>
          </div>

          <p class="text-xs font-mono text-[#86948a]">Showing {{ filteredMachines.length }} machine(s)</p>
        </div>

        <!-- Machine Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div 
            v-for="machine in filteredMachines" 
            :key="machine.id"
            class="glass-card rounded-2xl p-5 flex flex-col justify-between relative overflow-hidden group hover:border-[#10b981]/50 transition-all duration-300"
            :class="{
              'glow-emerald': machine.status === 'available',
              'glow-rose': machine.status === 'in_use',
              'glow-amber': machine.status === 'idle_full'
            }"
          >
            <!-- Card Header -->
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-white font-mono font-bold text-sm tracking-wider">{{ machine.name.toUpperCase() }}</span>
                
                <!-- Live Telemetry Wattage Pill -->
                <span 
                  v-if="machine.latest_power_w !== null && machine.latest_power_w !== undefined" 
                  class="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[11px] px-2 py-0.5 rounded-full font-mono font-bold flex items-center gap-1"
                >
                  ⚡ {{ machine.latest_power_w.toFixed(0) }}W
                </span>
              </div>

              <!-- Animated Drum Display -->
              <div class="flex items-center gap-4 my-4 p-3 bg-[#0a0e17]/80 rounded-xl border border-white/10">
                <div class="w-12 h-12 rounded-full border border-white/10 flex items-center justify-center bg-[#181b25] relative">
                  <div 
                    class="text-2xl transition-transform duration-1000"
                    :class="{ 'animate-spin': machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) > 0 }"
                    style="animation-duration: 2.5s;"
                  >
                    🌀
                  </div>
                </div>

                <div>
                  <div v-if="machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) > 0">
                    <p class="text-[11px] font-mono text-[#86948a]">TIME REMAINING</p>
                    <p class="text-xl font-mono font-bold text-rose-400 tracking-wider">
                      {{ formatTime(getSecondsRemaining(machine.active_booking?.estimated_end_at)) }}
                    </p>
                  </div>

                  <div v-else-if="machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) === 0">
                    <p class="text-[11px] font-mono text-amber-400">UNLOAD NEEDED</p>
                    <p class="text-sm font-mono font-bold text-amber-300">00:00</p>
                  </div>

                  <div v-else-if="machine.status === 'available'">
                    <p class="text-[11px] font-mono text-[#86948a]">STATUS</p>
                    <p class="text-sm font-mono font-bold text-emerald-400">READY</p>
                  </div>

                  <div v-else-if="machine.status === 'idle_full'">
                    <p class="text-[11px] font-mono text-[#86948a]">DONE & FULL</p>
                    <p class="text-sm font-mono font-bold text-amber-500">FINISHED</p>
                  </div>
                </div>
              </div>

              <!-- Waitlist Queue Section -->
              <div class="my-3 border-t border-white/10 pt-3">
                <div class="flex items-center justify-between text-xs font-mono text-[#86948a] mb-2">
                  <span>📋 WAITLIST ({{ machine.queue.length }})</span>
                </div>
                
                <div v-if="machine.queue.length > 0" class="space-y-1 max-h-20 overflow-y-auto pr-1">
                  <div 
                    v-for="(entry, index) in machine.queue" 
                    :key="entry.id"
                    class="flex items-center justify-between text-xs font-mono px-2 py-1 rounded bg-[#181b25] border border-white/10"
                    :class="{ 'border-indigo-500/40 text-indigo-300': entry.user_id === currentUser.id }"
                  >
                    <span>#{{ index + 1 }} Student (..{{ entry.user_id.substring(0, 4) }})</span>
                    <span v-if="entry.status === 'notified'" class="text-[10px] text-amber-400 font-bold">RESERVED</span>
                    <span v-else class="text-[10px] text-[#86948a]">WAITING</span>
                  </div>
                </div>
                <p v-else class="text-xs font-mono text-[#86948a]/60 italic">Queue is empty.</p>
              </div>
            </div>

            <!-- Card Actions -->
            <div class="border-t border-white/10 pt-3 mt-2">
              <div v-if="machine.status === 'available'">
                <button 
                  v-if="isNotified(machine)"
                  @click="claimMachine(machine.id)"
                  class="w-full bg-[#fbbf24] hover:bg-amber-500 text-black font-mono font-bold py-2.5 rounded-xl text-xs uppercase tracking-wider transition active:scale-95"
                >
                  Claim My Reservation 🚀
                </button>
                <button 
                  v-else-if="machine.queue.length > 0"
                  disabled
                  class="w-full bg-[#181b25] text-[#86948a] font-mono py-2.5 rounded-xl text-xs cursor-not-allowed"
                >
                  🔒 Reserved for Queue
                </button>
                <button 
                  v-else
                  @click="claimMachine(machine.id)"
                  class="w-full bg-[#10b981] hover:bg-[#4edea3] text-[#003824] font-mono font-bold py-2.5 rounded-xl text-xs uppercase tracking-wider transition active:scale-95"
                >
                  Start Laundry 🚀
                </button>
              </div>

              <div v-else-if="machine.status === 'in_use'">
                <button 
                  v-if="isOwner(machine)"
                  @click="clearMachine(machine.id)"
                  class="w-full bg-rose-600 hover:bg-rose-500 text-white font-mono font-bold py-2.5 rounded-xl text-xs uppercase tracking-wider transition active:scale-95"
                >
                  Clear Machine 🛑
                </button>

                <div v-else>
                  <button 
                    v-if="getQueuePosition(machine) !== null"
                    @click="leaveQueue(machine.id)"
                    class="w-full bg-[#181b25] hover:bg-[#262a34] text-rose-400 font-mono py-2.5 rounded-xl text-xs transition active:scale-95"
                  >
                    Cancel Queue (Pos: #{{ getQueuePosition(machine) }}) ❌
                  </button>
                  <button 
                    v-else
                    @click="joinQueue(machine.id)"
                    class="w-full bg-[#181b25] hover:bg-[#262a34] text-[#4edea3] font-mono font-bold py-2.5 rounded-xl text-xs transition active:scale-95"
                  >
                    Join Waitlist Queue 📋
                  </button>
                </div>
              </div>

              <div v-else-if="machine.status === 'idle_full'" class="space-y-2">
                <button 
                  @click="clearMachine(machine.id)"
                  class="w-full bg-[#10b981] hover:bg-[#4edea3] text-[#003824] font-mono font-bold py-2.5 rounded-xl text-xs uppercase tracking-wider transition active:scale-95"
                >
                  Unload & Make Available 🧺
                </button>
                <button 
                  v-if="getQueuePosition(machine) !== null"
                  @click="pingOwner(machine.id)"
                  class="w-full bg-amber-500 hover:bg-amber-600 text-black font-mono font-bold py-2 rounded-xl text-xs animate-pulse"
                >
                  📢 Ping Owner to Unload
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Toast Notifications -->
    <div class="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full">
      <div 
        v-for="toast in toasts" 
        :key="toast.id"
        class="glass-card p-4 rounded-xl border border-white/20 shadow-2xl flex items-start gap-3 transition-all duration-300"
        :class="{
          'border-amber-500/40 bg-amber-950/30 text-amber-300': toast.type === 'warning',
          'border-[#10b981]/40 bg-[#10b981]/10 text-[#4edea3]': toast.type === 'success',
          'border-rose-500/40 bg-rose-950/30 text-rose-300': toast.type === 'error',
          'border-indigo-500/40 bg-indigo-950/30 text-indigo-300': toast.type === 'info',
        }"
      >
        <span class="text-lg">
          <span v-if="toast.type === 'warning'">📢</span>
          <span v-else-if="toast.type === 'success'">✅</span>
          <span v-else-if="toast.type === 'error'">🚨</span>
          <span v-else>ℹ️</span>
        </span>
        <p class="text-xs font-mono font-semibold leading-relaxed flex-1">{{ toast.message }}</p>
      </div>
    </div>
  </div>
</template>

<style>
/* Stitch Custom Glassmorphic Styles */
.glass-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: border-color 0.3s ease;
}
.glass-card:hover {
  border-color: rgba(255, 255, 255, 0.25);
}
.glow-emerald {
  box-shadow: 0 0 30px rgba(16, 185, 129, 0.12);
}
.glow-rose {
  box-shadow: 0 0 30px rgba(244, 63, 94, 0.12);
}
.glow-amber {
  box-shadow: 0 0 30px rgba(245, 158, 11, 0.12);
}
.glow-indigo {
  box-shadow: 0 0 30px rgba(99, 102, 241, 0.12);
}
</style>
