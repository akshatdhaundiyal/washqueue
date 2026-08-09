<script setup>
import { ref, onMounted, computed } from 'vue'

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl

// Admin Auth State
const isAuthenticated = ref(false)
const inputPin = ref('')
const pinError = ref('')
const isAuthenticating = ref(false)

// Admin Data State
const adminMachines = ref([])
const smartPlugs = ref([])
const usageStats = ref(null)
const machinesList = ref([]) // Basic list of machines for dropdown binding
const loading = ref(false)
const errorMsg = ref('')

// Toast notifications
const toasts = ref([])
const addToast = (message, type = 'info') => {
  const id = Date.now()
  toasts.value.push({ id, message, type })
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }, 5000)
}

// Smart Plug Form state (Add / Edit)
const isModalOpen = ref(false)
const editingPlugId = ref(null)
const plugForm = ref({
  machine_id: '',
  provider: 'tuya_local',
  device_id: '',
  local_key: '',
  ip_address: '',
  protocol_version: '3.3',
  power_threshold_running: 10.0,
  power_threshold_idle: 5.0,
  debounce_seconds: 120
})
const testingPlugId = ref(null)

// Verify Admin PIN
const verifyPin = async () => {
  if (!inputPin.value) return
  isAuthenticating.value = true
  pinError.value = ''

  try {
    const res = await $fetch(`${apiBase}/api/admin/verify-pin`, {
      method: 'POST',
      body: { pin: inputPin.value }
    })

    if (res.valid) {
      isAuthenticated.value = true
      // Store PIN in session memory for API headers
      sessionStorage.setItem('admin_pin', inputPin.value)
      addToast('Admin authenticated successfully!', 'success')
      fetchAdminData()
    }
  } catch (err) {
    pinError.value = err.data?.detail || 'Invalid Admin PIN.'
  } finally {
    isAuthenticating.value = false
  }
}

// Check session storage on mount
onMounted(() => {
  const savedPin = sessionStorage.getItem('admin_pin')
  if (savedPin) {
    inputPin.value = savedPin
    verifyPin()
  }
})

// Fetch all Admin Data (Machines with Identities, Smart Plugs, Stats)
const fetchAdminData = async () => {
  if (!isAuthenticated.value) return
  loading.value = true
  errorMsg.value = ''

  const headers = { 'X-Admin-PIN': inputPin.value }

  try {
    const [machinesData, plugsData, statsData, publicMachines] = await Promise.all([
      $fetch(`${apiBase}/api/admin/machines`, { headers }),
      $fetch(`${apiBase}/api/smart-plugs`, { headers }),
      $fetch(`${apiBase}/api/admin/usage-stats`, { headers }),
      $fetch(`${apiBase}/api/machines`)
    ])

    adminMachines.value = machinesData
    smartPlugs.value = plugsData
    usageStats.value = statsData
    machinesList.value = publicMachines
  } catch (err) {
    console.error('Failed to fetch admin data:', err)
    if (err.status === 403) {
      isAuthenticated.value = false
      sessionStorage.removeItem('admin_pin')
      pinError.value = 'Session expired. Please enter Admin PIN again.'
    } else {
      errorMsg.value = 'Failed to load admin data from server.'
    }
  } finally {
    loading.value = false
  }
}

// Smart Plug Management Actions
const openAddPlugModal = () => {
  editingPlugId.value = null
  plugForm.value = {
    machine_id: '',
    provider: 'tuya_local',
    device_id: '',
    local_key: '',
    ip_address: '',
    protocol_version: '3.3',
    power_threshold_running: 10.0,
    power_threshold_idle: 5.0,
    debounce_seconds: 120
  }
  isModalOpen.value = true
}

const openEditPlugModal = (plug) => {
  editingPlugId.value = plug.id
  plugForm.value = {
    machine_id: plug.machine_id || '',
    provider: plug.provider || 'tuya_local',
    device_id: plug.device_id,
    local_key: plug.local_key,
    ip_address: plug.ip_address,
    protocol_version: plug.protocol_version || '3.3',
    power_threshold_running: plug.power_threshold_running || 10.0,
    power_threshold_idle: plug.power_threshold_idle || 5.0,
    debounce_seconds: plug.debounce_seconds || 120
  }
  isModalOpen.value = true
}

const saveSmartPlug = async () => {
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const payload = {
      ...plugForm.value,
      machine_id: plugForm.value.machine_id ? plugForm.value.machine_id : null
    }

    if (editingPlugId.value) {
      await $fetch(`${apiBase}/api/smart-plugs/${editingPlugId.value}`, {
        method: 'PUT',
        headers,
        body: payload
      })
      addToast('Smart plug configuration updated.', 'success')
    } else {
      await $fetch(`${apiBase}/api/smart-plugs`, {
        method: 'POST',
        headers,
        body: payload
      })
      addToast('Smart plug registered successfully.', 'success')
    }
    isModalOpen.value = false
    fetchAdminData()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to save smart plug.', 'error')
  }
}

const deleteSmartPlug = async (plugId) => {
  if (!confirm('Are you sure you want to remove this smart plug configuration?')) return
  const headers = { 'X-Admin-PIN': inputPin.value }

  try {
    await $fetch(`${apiBase}/api/smart-plugs/${plugId}`, {
      method: 'DELETE',
      headers
    })
    addToast('Smart plug removed.', 'success')
    fetchAdminData()
  } catch (err) {
    addToast('Failed to delete smart plug.', 'error')
  }
}

const testPlugConnection = async (plugId) => {
  testingPlugId.value = plugId
  const headers = { 'X-Admin-PIN': inputPin.value }

  try {
    const res = await $fetch(`${apiBase}/api/smart-plugs/${plugId}/test`, {
      method: 'POST',
      headers
    })
    if (res.is_online) {
      addToast(`🟢 Local Plug Online! Power: ${res.power_w ?? 0}W, Voltage: ${res.voltage_v ?? 0}V`, 'success')
    } else {
      addToast(`🔴 Plug Offline or Unreachable. Check IP & Local Key. Detail: ${res.detail || 'Timeout'}`, 'error')
    }
    fetchAdminData()
  } catch (err) {
    addToast('Failed to test smart plug connection.', 'error')
  } finally {
    testingPlugId.value = null
  }
}
</script>

<template>
  <div class="relative min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-12 selection:bg-indigo-500 selection:text-white">
    <!-- Radiant Gradients -->
    <div class="absolute top-[-10%] left-[-20%] w-[60vw] h-[60vw] rounded-full bg-violet-900/10 blur-[120px] pointer-events-none"></div>

    <!-- Header Navigation -->
    <header class="border-b border-slate-900 bg-slate-900/60 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <NuxtLink to="/" class="bg-indigo-600 hover:bg-indigo-500 p-2 rounded-xl text-xl shadow-lg shadow-indigo-600/30 transition">
            ⬅️
          </NuxtLink>
          <div>
            <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              WashQueue Admin <span class="text-xs bg-violet-500/20 text-violet-400 px-2.5 py-0.5 rounded-full font-mono font-bold border border-violet-500/30">Protected</span>
            </h1>
            <p class="text-xs text-slate-400">Live User Identity Tracking & Local Smart Plug Manager</p>
          </div>
        </div>

        <div v-if="isAuthenticated" class="flex items-center gap-3">
          <button @click="fetchAdminData" class="bg-slate-900 hover:bg-slate-800 border border-slate-800 px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition">
            🔄 Refresh Data
          </button>
          <button @click="isAuthenticated = false; sessionStorage.removeItem('admin_pin')" class="bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 px-3 py-1.5 rounded-xl text-xs font-semibold transition">
            🔒 Lock Admin
          </button>
        </div>
      </div>
    </header>

    <!-- PIN Authentication Overlay Modal -->
    <div v-if="!isAuthenticated" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-lg flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 max-w-md w-full shadow-2xl text-center relative overflow-hidden">
        <div class="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl"></div>

        <div class="w-16 h-16 bg-violet-600/20 border border-violet-500/30 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
          🔐
        </div>
        <h2 class="text-2xl font-bold text-white mb-2">WashQueue Admin Security</h2>
        <p class="text-xs text-slate-400 mb-6">Enter the 4-digit Admin PIN to view live machine user identities and configure local smart plugs.</p>

        <form @submit.prevent="verifyPin" class="space-y-4">
          <input 
            v-model="inputPin" 
            type="password"
            maxlength="8"
            placeholder="Enter Admin PIN (Default: 1234)"
            class="w-full bg-slate-950 border border-slate-800 text-center font-mono text-xl tracking-widest text-white rounded-xl py-3 focus:outline-none focus:border-indigo-500 transition"
          />

          <p v-if="pinError" class="text-xs font-semibold text-rose-400 bg-rose-950/30 border border-rose-500/30 py-2 rounded-lg">
            {{ pinError }}
          </p>

          <button 
            type="submit" 
            :disabled="isAuthenticating || !inputPin"
            class="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-600/30"
          >
            <span v-if="isAuthenticating">Authenticating...</span>
            <span v-else>Unlock Admin Portal 🔓</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Authenticated Admin Content -->
    <main v-else class="max-w-7xl mx-auto px-6 mt-8 flex-1 w-full space-y-8">
      
      <!-- Headline Stats Cards -->
      <div v-if="usageStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-slate-900/50 border border-slate-900 rounded-2xl p-5">
          <p class="text-xs text-slate-400 font-medium">Total Machines</p>
          <p class="text-3xl font-black text-white mt-1">{{ usageStats.total_machines }}</p>
        </div>
        <div class="bg-slate-900/50 border border-slate-900 rounded-2xl p-5">
          <p class="text-xs text-slate-400 font-medium">Online Smart Plugs</p>
          <p class="text-3xl font-black text-emerald-400 mt-1">{{ usageStats.online_plugs }} / {{ smartPlugs.length }}</p>
        </div>
        <div class="bg-slate-900/50 border border-slate-900 rounded-2xl p-5">
          <p class="text-xs text-slate-400 font-medium">Currently In Use</p>
          <p class="text-3xl font-black text-rose-400 mt-1">{{ usageStats.status_breakdown.in_use }}</p>
        </div>
        <div class="bg-slate-900/50 border border-slate-900 rounded-2xl p-5">
          <p class="text-xs text-slate-400 font-medium">Idle & Full (Unloaded)</p>
          <p class="text-3xl font-black text-amber-400 mt-1">{{ usageStats.status_breakdown.idle_full }}</p>
        </div>
      </div>

      <!-- SECTION 1: Who Is Using What (Live Machine User Identity View) -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>👤 Live Machine User Identities</span>
              <span class="text-xs bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded font-mono">Admin Only</span>
            </h2>
            <p class="text-xs text-slate-400">Unmasked student names and contact details for active laundry bookings.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div 
            v-for="machine in adminMachines" 
            :key="machine.id"
            class="bg-slate-900/60 border border-slate-900 rounded-2xl p-5 flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-slate-200 text-sm font-bold">{{ machine.name }}</span>
                <span 
                  class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-emerald-500/20 text-emerald-400': machine.status === 'available',
                    'bg-rose-500/20 text-rose-400': machine.status === 'in_use',
                    'bg-amber-500/20 text-amber-400': machine.status === 'idle_full'
                  }"
                >
                  {{ machine.status }}
                </span>
              </div>

              <!-- Active Booking Holder Identity -->
              <div class="bg-slate-950/60 border border-slate-800 rounded-xl p-3 my-3">
                <p class="text-[11px] text-slate-400 uppercase font-mono font-semibold">Active User</p>
                <div v-if="machine.active_booking" class="mt-1">
                  <p class="text-sm font-bold text-indigo-300 flex items-center gap-1.5">
                    <span>🧑‍🎓</span> {{ machine.active_booking.user_name }}
                  </p>
                  <p v-if="machine.active_booking.user_email" class="text-xs text-slate-400 truncate">
                    ✉️ {{ machine.active_booking.user_email }}
                  </p>
                  <p class="text-[10px] text-slate-500 mt-1 font-mono">
                    Started: {{ new Date(machine.active_booking.started_at).toLocaleTimeString() }}
                  </p>
                </div>
                <p v-else class="text-xs text-slate-500 italic mt-1">No active user (Available)</p>
              </div>

              <!-- Live Telemetry Snapshot -->
              <div v-if="machine.latest_telemetry" class="grid grid-cols-3 gap-2 text-center my-3 bg-slate-950/40 p-2 rounded-xl border border-slate-900">
                <div>
                  <p class="text-[9px] text-slate-400 font-mono">VOLTAGE</p>
                  <p class="text-xs font-bold text-amber-400">{{ machine.latest_telemetry.voltage_v ?? 0 }}V</p>
                </div>
                <div>
                  <p class="text-[9px] text-slate-400 font-mono">POWER</p>
                  <p class="text-xs font-bold text-rose-400">{{ machine.latest_telemetry.power_w ?? 0 }}W</p>
                </div>
                <div>
                  <p class="text-[9px] text-slate-400 font-mono">CURRENT</p>
                  <p class="text-xs font-bold text-sky-400">{{ machine.latest_telemetry.current_ma ?? 0 }}mA</p>
                </div>
              </div>

              <!-- Queue Identities -->
              <div class="border-t border-slate-900 pt-3 mt-2">
                <p class="text-[11px] text-slate-400 font-medium mb-1.5">Waitlist Queue ({{ machine.queue.length }})</p>
                <div v-if="machine.queue.length > 0" class="space-y-1 max-h-20 overflow-y-auto">
                  <div v-for="q in machine.queue" :key="q.id" class="text-xs bg-slate-950 px-2 py-1 rounded border border-slate-900 flex items-center justify-between">
                    <span class="font-medium text-slate-300">#{{ q.position }} {{ q.user_name }}</span>
                    <span class="text-[10px] text-slate-500">{{ q.status }}</span>
                  </div>
                </div>
                <p v-else class="text-[11px] text-slate-500 italic">Queue is empty</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 2: Local Smart Plug Configuration Manager -->
      <section class="space-y-4 pt-4 border-t border-slate-900">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
              <span>⚡ Local Smart Plug Configurations (Wipro / Tuya LAN)</span>
            </h2>
            <p class="text-xs text-slate-400">Configure device IP, Local Key, and power thresholds for local socket telemetry polling.</p>
          </div>
          <button 
            @click="openAddPlugModal"
            class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-indigo-600/30"
          >
            ➕ Register Smart Plug
          </button>
        </div>

        <div class="bg-slate-900/40 border border-slate-900 rounded-2xl overflow-hidden">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-900/80 text-slate-400 uppercase font-mono border-b border-slate-800">
              <tr>
                <th class="p-4">Assigned Machine</th>
                <th class="p-4">Status</th>
                <th class="p-4">IP Address</th>
                <th class="p-4">Device ID</th>
                <th class="p-4">Thresholds</th>
                <th class="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-900">
              <tr v-for="plug in smartPlugs" :key="plug.id" class="hover:bg-slate-900/30 transition">
                <td class="p-4 font-bold text-slate-200">
                  {{ machinesList.find(m => m.id === plug.machine_id)?.name || 'Unassigned' }}
                </td>
                <td class="p-4">
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                    :class="plug.is_online ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'"
                  >
                    {{ plug.is_online ? 'Online' : 'Offline' }}
                  </span>
                </td>
                <td class="p-4 font-mono text-slate-300">{{ plug.ip_address }}</td>
                <td class="p-4 font-mono text-slate-400 truncate max-w-[120px]">{{ plug.device_id }}</td>
                <td class="p-4 font-mono text-slate-400">
                  Run: {{ plug.power_threshold_running }}W | Idle: {{ plug.power_threshold_idle }}W
                </td>
                <td class="p-4 text-right space-x-2">
                  <button 
                    @click="testPlugConnection(plug.id)"
                    :disabled="testingPlugId === plug.id"
                    class="bg-slate-800 hover:bg-slate-700 text-emerald-400 px-2.5 py-1 rounded text-[11px] font-semibold transition"
                  >
                    {{ testingPlugId === plug.id ? 'Testing...' : '📡 Test LAN' }}
                  </button>
                  <button 
                    @click="openEditPlugModal(plug)"
                    class="bg-slate-800 hover:bg-slate-700 text-indigo-300 px-2.5 py-1 rounded text-[11px] font-semibold transition"
                  >
                    ✏️ Edit
                  </button>
                  <button 
                    @click="deleteSmartPlug(plug.id)"
                    class="bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 px-2.5 py-1 rounded text-[11px] font-semibold transition"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
              <tr v-if="smartPlugs.length === 0">
                <td colspan="6" class="p-8 text-center text-slate-500 italic">
                  No smart plugs registered yet. Click "Register Smart Plug" to add your local Wipro plug.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <!-- Register / Edit Smart Plug Modal -->
    <div v-if="isModalOpen" class="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-lg w-full shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 class="text-base font-bold text-white">
            {{ editingPlugId ? 'Edit Smart Plug Config' : 'Register Wipro Smart Plug (Local LAN)' }}
          </h3>
          <button @click="isModalOpen = false" class="text-slate-400 hover:text-white">✕</button>
        </div>

        <form @submit.prevent="saveSmartPlug" class="space-y-3 text-xs">
          <div>
            <label class="block text-slate-400 font-medium mb-1">Assign to Machine</label>
            <select v-model="plugForm.machine_id" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 focus:outline-none focus:border-indigo-500">
              <option value="">-- Select Washing Machine --</option>
              <option v-for="m in machinesList" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 font-medium mb-1">IP Address (Local LAN)</label>
              <input v-model="plugForm.ip_address" required placeholder="192.168.1.50" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label class="block text-slate-400 font-medium mb-1">Protocol Version</label>
              <select v-model="plugForm.protocol_version" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 focus:outline-none focus:border-indigo-500 font-mono">
                <option value="3.3">3.3 (Standard Wipro)</option>
                <option value="3.1">3.1 (Older)</option>
                <option value="3.4">3.4 (Newer Tuya)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-slate-400 font-medium mb-1">Tuya Device ID</label>
            <input v-model="plugForm.device_id" required placeholder="bf1234567890abcdef" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
          </div>

          <div>
            <label class="block text-slate-400 font-medium mb-1">Tuya Local Key</label>
            <input v-model="plugForm.local_key" required type="text" placeholder="16-character local key" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
          </div>

          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-slate-400 font-medium mb-1">Run Threshold (W)</label>
              <input v-model.number="plugForm.power_threshold_running" type="number" step="0.1" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label class="block text-slate-400 font-medium mb-1">Idle Threshold (W)</label>
              <input v-model.number="plugForm.power_threshold_idle" type="number" step="0.1" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
            </div>
            <div>
              <label class="block text-slate-400 font-medium mb-1">Soak Debounce (s)</label>
              <input v-model.number="plugForm.debounce_seconds" type="number" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-slate-100 font-mono focus:outline-none focus:border-indigo-500" />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <button type="button" @click="isModalOpen = false" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-bold">Cancel</button>
            <button type="submit" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold">Save Plug</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Toast Floating Container -->
    <div class="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-sm w-full">
      <div 
        v-for="toast in toasts" 
        :key="toast.id"
        class="bg-slate-900 border border-slate-800 p-4 rounded-2xl shadow-2xl flex items-start gap-3"
        :class="{
          'border-emerald-500/40 text-emerald-300': toast.type === 'success',
          'border-rose-500/40 text-rose-300': toast.type === 'error',
          'border-indigo-500/40 text-indigo-300': toast.type === 'info',
        }"
      >
        <p class="text-xs font-bold flex-1">{{ toast.message }}</p>
      </div>
    </div>
  </div>
</template>
