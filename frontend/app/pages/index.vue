<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl

// Mock users for local testing
const mockUsers = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Alex (User A)', avatar: '🧑‍💻' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Blake (User B)', avatar: '👩‍🔬' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Charlie (User C)', avatar: '👨‍🎨' }
]

// App state
const currentUser = ref(mockUsers[0])
const machines = ref([])
const loading = ref(true)
const errorMsg = ref('')

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
    errorMsg.value = 'Failed to connect to the backend server.'
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

  // Subscribe to DB updates
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

  // Subscribe to Realtime Broadcasts for owner pings
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
  if (dbChannel) $supabase.removeChannel(dbChannel)
  if (broadcastChannel) $supabase.removeChannel(broadcastChannel)
})


// Check if current user is the owner of the active booking
const isOwner = (machine) => {
  return machine.active_booking && machine.active_booking.user_id === currentUser.value.id
}

// Check if current user is in the queue for a machine
const getQueuePosition = (machine) => {
  const idx = machine.queue.findIndex(q => q.user_id === currentUser.value.id)
  return idx !== -1 ? idx + 1 : null
}

// Check if current user is notified for a machine
const isNotified = (machine) => {
  const entry = machine.queue.find(q => q.user_id === currentUser.value.id)
  return entry && entry.status === 'notified'
}

// Timer helpers
const getSecondsRemaining = (estimatedEndAt) => {
  const diff = new Date(estimatedEndAt).getTime() - now.value
  return diff <= 0 ? 0 : Math.floor(diff / 1000)
}

const formatTime = (seconds) => {
  const mm = Math.floor(seconds / 60).toString().padStart(2, '0')
  const ss = (seconds % 60).toString().padStart(2, '0')
  return `${mm}:${ss}`
}

// API Actions
const claimMachine = async (machineId) => {
  try {
    await $fetch(`${apiBase}/api/machines/${machineId}/claim`, {
      method: 'POST',
      body: { user_id: currentUser.value.id }
    })
    addToast('Machine claimed successfully! Cycle started (45 min).', 'success')
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
    
    // Broadcast ping alert to Supabase
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
  } catch (err) {
    addToast(err.data?.detail || 'Failed to leave queue.', 'error')
  }
}

// Trigger background scheduler overdue check
const triggerSchedulerTick = async () => {
  try {
    const res = await $fetch(`${apiBase}/api/scheduler/tick`, {
      method: 'POST'
    })
    if (res.updated_count > 0) {
      addToast(`Scheduler updated ${res.updated_count} machine(s) to Idle-Full.`, 'success')
    } else {
      addToast('Scheduler tick: No overdue machines found.', 'info')
    }
  } catch (err) {
    addToast('Failed to trigger scheduler tick.', 'error')
  }
}

// UI State computed helpers
const getMachineState = (machine) => {
  if (machine.status === 'available') {
    return {
      label: 'Available',
      class: 'border-emerald-500/30 bg-emerald-950/20 text-emerald-400',
      dot: 'bg-emerald-400 shadow-emerald-400/50'
    }
  }
  
  if (machine.status === 'in_use') {
    const seconds = getSecondsRemaining(machine.active_booking?.estimated_end_at)
    if (seconds === 0) {
      return {
        label: 'Cycle Complete (Occupied)',
        class: 'border-amber-500/30 bg-amber-950/20 text-amber-400',
        dot: 'bg-amber-400 shadow-amber-400/50 animate-pulse'
      }
    }
    return {
      label: 'In Use',
      class: 'border-rose-500/30 bg-rose-950/20 text-rose-400',
      dot: 'bg-rose-400 shadow-rose-400/50 animate-pulse'
    }
  }
  
  if (machine.status === 'idle_full') {
    return {
      label: 'Idle Full (Unloaded)',
      class: 'border-amber-500/30 bg-amber-950/20 text-amber-400',
      dot: 'bg-amber-500 shadow-amber-500/50'
    }
  }
  
  return {
    label: 'Unknown',
    class: 'border-slate-500/30 bg-slate-950/20 text-slate-400',
    dot: 'bg-slate-400'
  }
}
</script>

<template>
  <div class="relative min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white pb-12 overflow-x-hidden">
    <!-- Radiant Gradients -->
    <div class="absolute top-[-10%] left-[-20%] w-[60vw] h-[60vw] rounded-full bg-indigo-900/10 blur-[120px] pointer-events-none"></div>
    <div class="absolute bottom-[-10%] right-[-20%] w-[60vw] h-[60vw] rounded-full bg-violet-900/10 blur-[120px] pointer-events-none"></div>

    <!-- Header Navigation -->
    <header class="border-b border-slate-900 bg-slate-900/40 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div class="flex items-center gap-3">
          <div class="bg-indigo-600 p-2 rounded-xl text-2xl shadow-lg shadow-indigo-600/30">🌀</div>
          <div>
            <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              WashQueue 
              <span 
                class="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold border transition"
                :class="isWsConnected ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-sky-500/20 text-sky-400 border-sky-500/30'"
              >
                {{ isWsConnected ? '🟢 Hostel LAN (WebSocket)' : '☁️ Remote Mobile' }}
              </span>
            </h1>
            <p class="text-xs text-slate-400">Hostel Laundry Management & Telemetry Appliance</p>
          </div>

        </div>

        <div class="flex flex-wrap items-center gap-3">
          <!-- Admin Portal Link -->
          <NuxtLink 
            to="/admin" 
            class="bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 text-violet-300 px-3 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5"
          >
            🔒 Admin Portal
          </NuxtLink>

          <!-- Simulation Tools -->
          <div class="bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-1.5 flex items-center gap-2.5">
            <span class="text-xs text-slate-400 font-medium">Active User:</span>
            <select 
              v-model="currentUser"
              class="bg-slate-950 border border-slate-800 text-sm font-semibold rounded-lg text-slate-100 px-2 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              <option v-for="user in mockUsers" :key="user.id" :value="user">
                {{ user.avatar }} {{ user.name }}
              </option>
            </select>
          </div>

          <button 
            @click="triggerSchedulerTick" 
            class="bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition active:scale-95"
            title="Simulates time passing to change expired bookings to Idle Full"
          >
            ⏱️ Trigger Scheduler Tick
          </button>
        </div>
      </div>
    </header>


    <!-- Main Content Dashboard -->
    <main class="max-w-7xl mx-auto px-6 mt-8 flex-1 w-full">
      <div v-if="errorMsg" class="bg-rose-950/20 border border-rose-500/30 text-rose-300 rounded-2xl p-4 mb-6 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <span class="text-xl">⚠️</span>
          <p class="text-sm font-medium">{{ errorMsg }} Please configure your Supabase settings.</p>
        </div>
        <button @click="fetchMachines" class="bg-rose-500/20 hover:bg-rose-500/30 px-3 py-1.5 rounded-lg text-xs font-bold transition">Retry Connection</button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-24 gap-4">
        <div class="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-slate-400 text-sm font-medium animate-pulse">Syncing laundry machine configurations...</p>
      </div>

      <!-- Loaded Dashboard Grid -->
      <div v-else>
        <!-- Headline Stats Summary -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4">
            <p class="text-xs text-slate-400">Available Machines</p>
            <p class="text-2xl font-black text-emerald-400 mt-1">
              {{ machines.filter(m => m.status === 'available').length }} / {{ machines.length }}
            </p>
          </div>
          <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4">
            <p class="text-xs text-slate-400">Currently Running</p>
            <p class="text-2xl font-black text-rose-400 mt-1">
              {{ machines.filter(m => m.status === 'in_use').length }}
            </p>
          </div>
          <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4">
            <p class="text-xs text-slate-400">Idle & Full</p>
            <p class="text-2xl font-black text-amber-400 mt-1">
              {{ machines.filter(m => m.status === 'idle_full').length }}
            </p>
          </div>
          <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4">
            <p class="text-xs text-slate-400">My Running Cycles</p>
            <p class="text-2xl font-black text-indigo-400 mt-1">
              {{ machines.filter(isOwner).length }}
            </p>
          </div>
        </div>

        <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span>⚡ Live Machine Status</span>
          <span class="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span>
        </h2>

        <!-- Machines Cards List -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div 
            v-for="machine in machines" 
            :key="machine.id"
            class="bg-slate-900/50 backdrop-blur-md border border-slate-900 rounded-2xl p-5 flex flex-col justify-between transition-all duration-300 hover:border-slate-800 hover:shadow-xl hover:shadow-indigo-950/10 group"
          >
            <!-- Card Upper Section -->
            <div>
              <div class="flex items-center justify-between mb-4">
                <span class="text-slate-400 text-xs font-mono font-semibold">{{ machine.name.toUpperCase() }}</span>
                <div class="flex items-center gap-2">
                  <!-- Live Telemetry Wattage Badge -->
                  <span 
                    v-if="machine.latest_power_w !== null && machine.latest_power_w !== undefined" 
                    class="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[11px] px-2 py-0.5 rounded-full font-mono font-bold flex items-center gap-1"
                    :title="`Live LAN Smart Plug Reading: ${machine.latest_power_w}W`"
                  >
                    ⚡ {{ machine.latest_power_w.toFixed(0) }}W
                  </span>

                  <!-- Status Badge -->
                  <div class="flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold" :class="getMachineState(machine).class">
                    <span class="w-1.5 h-1.5 rounded-full" :class="getMachineState(machine).dot"></span>
                    {{ getMachineState(machine).label }}
                  </div>
                </div>
              </div>


              <!-- Animated Drum Display -->
              <div class="flex items-center gap-4 my-4 p-3 bg-slate-950/50 border border-slate-900/80 rounded-xl">
                <div class="relative w-12 h-12 rounded-full border border-slate-800 flex items-center justify-center bg-slate-900">
                  <div 
                    class="text-2xl transition-transform duration-1000"
                    :class="{ 'animate-spin': machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) > 0 }"
                    style="animation-duration: 2.5s;"
                  >
                    🌀
                  </div>
                </div>

                <!-- Timer / Claim Holder details -->
                <div>
                  <!-- Countdown Timer -->
                  <div v-if="machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) > 0">
                    <p class="text-xs text-slate-400">Time Remaining</p>
                    <p class="text-xl font-bold font-mono text-rose-400 tracking-wider">
                      {{ formatTime(getSecondsRemaining(machine.active_booking?.estimated_end_at)) }}
                    </p>
                  </div>

                  <!-- Cycle Complete Status -->
                  <div v-else-if="machine.status === 'in_use' && getSecondsRemaining(machine.active_booking?.estimated_end_at) === 0">
                    <p class="text-xs text-amber-500 font-medium">Waiting to unload</p>
                    <p class="text-sm font-bold text-amber-400">00:00</p>
                  </div>

                  <!-- Available display -->
                  <div v-else-if="machine.status === 'available'">
                    <p class="text-xs text-slate-400">Ready for laundry</p>
                    <p class="text-sm font-bold text-emerald-400">Ready</p>
                  </div>

                  <!-- Idle Full Display -->
                  <div v-else-if="machine.status === 'idle_full'">
                    <p class="text-xs text-slate-400">Done & Full</p>
                    <p class="text-sm font-bold text-amber-500">Unload Needed</p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Waitlist Section for this Card -->
            <div class="my-4 border-t border-slate-900/80 pt-4">
              <div class="flex items-center justify-between text-xs text-slate-400 mb-2">
                <span class="font-semibold flex items-center gap-1">📋 Waitlist Queue <span class="bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded text-[10px]">{{ machine.queue.length }}</span></span>
              </div>
              
              <!-- Virtual Waitlist list -->
              <div v-if="machine.queue.length > 0" class="space-y-1.5 max-h-24 overflow-y-auto pr-1">
                <div 
                  v-for="(entry, index) in machine.queue" 
                  :key="entry.id"
                  class="flex items-center justify-between text-xs bg-slate-950/40 px-2.5 py-1.5 rounded-lg border border-slate-900"
                  :class="{ 
                    'border-indigo-500/20 bg-indigo-950/10 text-indigo-300': entry.user_id === currentUser.id,
                    'border-amber-500/30 bg-amber-950/10 animate-pulse': entry.status === 'notified'
                  }"
                >
                  <span class="font-medium flex items-center gap-1.5">
                    <span class="w-4 h-4 text-[10px] rounded-full bg-slate-800 flex items-center justify-center font-mono">{{ index + 1 }}</span>
                    <span>Student (..{{ entry.user_id.substring(0, 4) }})</span>
                  </span>
                  
                  <span 
                    v-if="entry.status === 'notified'" 
                    class="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider"
                  >
                    Reserved
                  </span>
                  <span v-else class="text-[10px] text-slate-500 font-mono">Waiting</span>
                </div>
              </div>
              <p v-else class="text-xs text-slate-500 italic py-1">Waitlist is currently empty.</p>
            </div>

            <!-- Card Action Footer -->
            <div class="border-t border-slate-900/80 pt-4 mt-2">
              <!-- Available State Actions -->
              <div v-if="machine.status === 'available'" class="space-y-2">
                <!-- If current user is notified, they are allowed to claim -->
                <button 
                  v-if="isNotified(machine)"
                  @click="claimMachine(machine.id)"
                  class="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                >
                  Claim My Reservation 🚀
                </button>
                <button 
                  v-else-if="machine.queue.length > 0"
                  disabled
                  class="w-full bg-slate-800 text-slate-400 py-2.5 rounded-xl text-xs font-bold cursor-not-allowed flex items-center justify-center gap-1"
                >
                  🔒 Reserved for Queue
                </button>
                <button 
                  v-else
                  @click="claimMachine(machine.id)"
                  class="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                >
                  Start Laundry 🚀
                </button>
              </div>

              <!-- In Use State Actions -->
              <div v-else-if="machine.status === 'in_use'" class="space-y-2">
                <!-- If current user owns the active booking, let them finish/clear -->
                <button 
                  v-if="isOwner(machine)"
                  @click="clearMachine(machine.id)"
                  class="w-full bg-rose-600 hover:bg-rose-500 text-white py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                >
                  Clear Machine 🛑
                </button>
                
                <!-- Queue Actions for other users -->
                <div v-else>
                  <!-- Already in Queue -->
                  <button 
                    v-if="getQueuePosition(machine) !== null"
                    @click="leaveQueue(machine.id)"
                    class="w-full bg-slate-800 hover:bg-slate-700 text-rose-400 py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                  >
                    Cancel Queue (Pos: #{{ getQueuePosition(machine) }}) ❌
                  </button>
                  <!-- Join Queue -->
                  <button 
                    v-else
                    @click="joinQueue(machine.id)"
                    class="w-full bg-slate-800 hover:bg-slate-700 text-indigo-400 py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                  >
                    Join Waitlist Queue 📋
                  </button>
                </div>
              </div>

              <!-- Idle Full State Actions -->
              <div v-else-if="machine.status === 'idle_full'" class="space-y-2">
                <!-- Anyone can clear/unload an idle full machine -->
                <button 
                  @click="clearMachine(machine.id)"
                  class="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-xl text-xs font-bold transition flex items-center justify-center gap-1.5 active:scale-95"
                >
                  Unload & Make Available 🧺
                </button>

                <!-- Ping Owner Button (Visible to users in the queue for this machine) -->
                <button 
                  v-if="getQueuePosition(machine) !== null"
                  @click="pingOwner(machine.id)"
                  class="w-full bg-amber-500 hover:bg-amber-600 text-slate-950 py-2.5 rounded-xl text-xs font-extrabold transition flex items-center justify-center gap-1.5 active:scale-95 animate-pulse"
                >
                  📢 Ping Owner to Unload
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Floating Live Toast Notifications System -->
    <div class="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full">
      <div 
        v-for="toast in toasts" 
        :key="toast.id"
        class="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-2xl flex items-start gap-3 transition-all duration-300 animate-slide-in"
        :class="{
          'border-amber-500/40 bg-amber-950/20 text-amber-300': toast.type === 'warning',
          'border-emerald-500/40 bg-emerald-950/20 text-emerald-300': toast.type === 'success',
          'border-rose-500/40 bg-rose-950/20 text-rose-300': toast.type === 'error',
          'border-indigo-500/40 bg-slate-900 text-indigo-300': toast.type === 'info',
        }"
      >
        <div class="text-lg">
          <span v-if="toast.type === 'warning'">📢</span>
          <span v-else-if="toast.type === 'success'">✅</span>
          <span v-else-if="toast.type === 'error'">🚨</span>
          <span v-else>ℹ️</span>
        </div>
        <div class="flex-1">
          <p class="text-sm font-semibold">{{ toast.message }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Custom toast entry animation */
@keyframes slideIn {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
.animate-slide-in {
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
