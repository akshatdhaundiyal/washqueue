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
const machinesList = ref([])
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

onMounted(() => {
  const savedPin = sessionStorage.getItem('admin_pin')
  if (savedPin) {
    inputPin.value = savedPin
    verifyPin()
  }
})

// Fetch all Admin Data
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
    await $fetch(`${apiBase}/api/smart-plugs/${plugId}`, { method: 'DELETE', headers })
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
      addToast(`🔴 Plug Offline or Unreachable. Check IP & Local Key.`, 'error')
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
  <div class="stitch-app min-h-screen bg-[#090D16] text-[#dfe2ef] selection:bg-[#10b981] selection:text-black">
    <!-- Top Header Navigation -->
    <header class="bg-[#090D16]/80 backdrop-blur-xl border-b border-white/10 sticky top-0 w-full z-50 px-6 py-4">
      <div class="max-w-7xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <NuxtLink to="/" class="glass-card px-3 py-2 rounded-xl text-xs font-mono font-bold text-white hover:text-[#4edea3] transition">
            ← Dashboard
          </NuxtLink>
          <div>
            <h1 class="text-xl font-bold font-mono tracking-tight text-white flex items-center gap-2">
              ADMIN PORTAL // SECURE_NODE
              <span v-if="isAuthenticated" class="text-xs bg-[#10b981]/20 text-[#4edea3] px-2.5 py-0.5 rounded-full font-mono font-bold border border-[#10b981]/30">
                Admin Authenticated (PIN: 1234)
              </span>
            </h1>
            <p class="text-xs text-[#86948a] font-mono">User Identity Resolver & Local Wipro Smart Plug Telemetry</p>
          </div>
        </div>

        <div v-if="isAuthenticated" class="flex items-center gap-3">
          <button @click="fetchAdminData" class="glass-card px-3 py-1.5 rounded-xl text-xs font-mono font-semibold hover:border-[#10b981]/40 transition">
            🔄 Refresh
          </button>
          <button @click="isAuthenticated = false; sessionStorage.removeItem('admin_pin')" class="bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 px-3 py-1.5 rounded-xl text-xs font-mono font-bold transition">
            🔒 Lock Admin
          </button>
        </div>
      </div>
    </header>

    <!-- PIN Unlock Modal -->
    <div v-if="!isAuthenticated" class="fixed inset-0 z-50 bg-[#090D16]/90 backdrop-blur-xl flex items-center justify-center p-4">
      <div class="glass-card rounded-3xl p-8 max-w-md w-full text-center relative overflow-hidden glow-indigo">
        <div class="w-16 h-16 bg-[#10b981]/10 border border-[#10b981]/30 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
          🔐
        </div>
        <h2 class="text-xl font-mono font-bold text-white mb-2">SECURITY_AUTHENTICATION</h2>
        <p class="text-xs font-mono text-[#86948a] mb-6">Enter Admin PIN to inspect student identities and local smart plug configurations.</p>

        <form @submit.prevent="verifyPin" class="space-y-4">
          <input 
            v-model="inputPin" 
            type="password"
            maxlength="8"
            placeholder="Enter Admin PIN (Default: 1234)"
            class="w-full bg-[#0a0e17] border border-white/10 text-center font-mono text-xl tracking-widest text-white rounded-xl py-3 focus:outline-none focus:border-[#10b981] transition"
          />

          <p v-if="pinError" class="text-xs font-mono font-semibold text-rose-400 bg-rose-950/30 border border-rose-500/30 py-2 rounded-lg">
            {{ pinError }}
          </p>

          <button 
            type="submit" 
            :disabled="isAuthenticating || !inputPin"
            class="w-full bg-[#10b981] hover:bg-[#4edea3] disabled:opacity-50 text-[#003824] font-mono font-bold py-3 rounded-xl uppercase tracking-wider transition shadow-lg"
          >
            <span v-if="isAuthenticating">VERIFYING...</span>
            <span v-else>UNLOCK ADMIN CONSOLE 🔓</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Authenticated Admin Content -->
    <main v-else class="max-w-7xl mx-auto px-6 pt-8 pb-16 space-y-8">
      
      <!-- Headline Stats Cards -->
      <div v-if="usageStats" class="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div class="glass-card rounded-2xl p-5">
          <p class="text-xs font-mono text-[#86948a] uppercase">Total Machines</p>
          <p class="text-3xl font-mono font-bold text-white mt-1">{{ usageStats.total_machines }}</p>
        </div>
        <div class="glass-card rounded-2xl p-5 glow-emerald">
          <p class="text-xs font-mono text-[#86948a] uppercase">Online Smart Plugs</p>
          <p class="text-3xl font-mono font-bold text-[#4edea3] mt-1">{{ usageStats.online_plugs }} / {{ smartPlugs.length }}</p>
        </div>
        <div class="glass-card rounded-2xl p-5 glow-rose">
          <p class="text-xs font-mono text-[#86948a] uppercase">Currently In Use</p>
          <p class="text-3xl font-mono font-bold text-[#ffb2b7] mt-1">{{ usageStats.status_breakdown.in_use }}</p>
        </div>
        <div class="glass-card rounded-2xl p-5 glow-amber">
          <p class="text-xs font-mono text-[#86948a] uppercase">Idle Full (Unloaded)</p>
          <p class="text-3xl font-mono font-bold text-[#fbbf24] mt-1">{{ usageStats.status_breakdown.idle_full }}</p>
        </div>
      </div>

      <!-- SECTION 1: Student Identity Resolver Table (USER_RESOLVER_V1) -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-mono font-bold text-white flex items-center gap-2">
              <span>USER_RESOLVER_V1 // LIVE_STUDENT_IDENTITIES</span>
            </h2>
            <p class="text-xs font-mono text-[#86948a]">Unmasked student identities and active laundry booking metrics.</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div 
            v-for="machine in adminMachines" 
            :key="machine.id"
            class="glass-card rounded-2xl p-5 flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="text-white font-mono font-bold text-sm">{{ machine.name }}</span>
                <span 
                  class="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full border"
                  :class="{
                    'bg-[#10b981]/20 text-[#4edea3] border-[#10b981]/30': machine.status === 'available',
                    'bg-rose-500/20 text-rose-400 border-rose-500/30': machine.status === 'in_use',
                    'bg-amber-500/20 text-amber-400 border-amber-500/30': machine.status === 'idle_full'
                  }"
                >
                  {{ machine.status }}
                </span>
              </div>

              <!-- Active User Identity -->
              <div class="bg-[#0a0e17] border border-white/10 rounded-xl p-3 my-3">
                <p class="text-[10px] font-mono text-[#86948a] uppercase">Active Student</p>
                <div v-if="machine.active_booking" class="mt-1">
                  <p class="text-sm font-mono font-bold text-[#c0c1ff] flex items-center gap-1.5">
                    🧑‍🎓 {{ machine.active_booking.user_name }}
                  </p>
                  <p v-if="machine.active_booking.user_email" class="text-xs font-mono text-[#86948a] truncate">
                    ✉️ {{ machine.active_booking.user_email }}
                  </p>
                  <p class="text-[10px] font-mono text-[#86948a] mt-1">
                    Started: {{ new Date(machine.active_booking.started_at).toLocaleTimeString() }}
                  </p>
                </div>
                <p v-else class="text-xs font-mono text-[#86948a]/60 italic mt-1">No active user (Available)</p>
              </div>

              <!-- Telemetry Metrics Snapshot -->
              <div v-if="machine.latest_telemetry" class="grid grid-cols-3 gap-2 text-center my-3 bg-[#181b25] p-2 rounded-xl border border-white/10">
                <div>
                  <p class="text-[9px] font-mono text-[#86948a]">VOLTS</p>
                  <p class="text-xs font-mono font-bold text-amber-400">{{ machine.latest_telemetry.voltage_v ?? 0 }}V</p>
                </div>
                <div>
                  <p class="text-[9px] font-mono text-[#86948a]">POWER</p>
                  <p class="text-xs font-mono font-bold text-rose-400">{{ machine.latest_telemetry.power_w ?? 0 }}W</p>
                </div>
                <div>
                  <p class="text-[9px] font-mono text-[#86948a]">CURRENT</p>
                  <p class="text-xs font-mono font-bold text-sky-400">{{ machine.latest_telemetry.current_ma ?? 0 }}mA</p>
                </div>
              </div>

              <!-- Queue Identities -->
              <div class="border-t border-white/10 pt-3 mt-2">
                <p class="text-[11px] font-mono text-[#86948a] mb-1.5">Waitlist Queue ({{ machine.queue.length }})</p>
                <div v-if="machine.queue.length > 0" class="space-y-1 max-h-20 overflow-y-auto pr-1">
                  <div v-for="q in machine.queue" :key="q.id" class="text-xs font-mono bg-[#0a0e17] px-2 py-1 rounded border border-white/10 flex items-center justify-between">
                    <span class="text-[#dfe2ef]">#{{ q.position }} {{ q.user_name }}</span>
                    <span class="text-[10px] text-[#86948a] uppercase">{{ q.status }}</span>
                  </div>
                </div>
                <p v-else class="text-[11px] font-mono text-[#86948a]/60 italic">Queue is empty</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 2: Smart Plug Manager (IOT_TELEMETRY // WIPRO_SMART_PLUG) -->
      <section class="space-y-4 pt-6 border-t border-white/10">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-lg font-mono font-bold text-white">
              IOT_TELEMETRY // WIPRO_SMART_PLUG
            </h2>
            <p class="text-xs font-mono text-[#86948a]">Configure device IP, Local Key, and power thresholds for local socket telemetry polling.</p>
          </div>
          <button 
            @click="openAddPlugModal"
            class="bg-[#10b981] hover:bg-[#4edea3] text-[#003824] font-mono font-bold text-xs px-4 py-2 rounded-xl transition flex items-center gap-1.5 uppercase tracking-wider"
          >
            ➕ Register Smart Plug
          </button>
        </div>

        <div class="glass-card rounded-2xl overflow-hidden">
          <table class="w-full text-left text-xs font-mono">
            <thead class="bg-[#181b25] text-[#86948a] uppercase border-b border-white/10">
              <tr>
                <th class="p-4">Assigned Machine</th>
                <th class="p-4">Status</th>
                <th class="p-4">IP Address</th>
                <th class="p-4">Device ID</th>
                <th class="p-4">Thresholds</th>
                <th class="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/10">
              <tr v-for="plug in smartPlugs" :key="plug.id" class="hover:bg-white/5 transition">
                <td class="p-4 font-bold text-white">
                  {{ machinesList.find(m => m.id === plug.machine_id)?.name || 'Unassigned' }}
                </td>
                <td class="p-4">
                  <span 
                    class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border"
                    :class="plug.is_online ? 'bg-[#10b981]/20 text-[#4edea3] border-[#10b981]/30' : 'bg-rose-500/20 text-rose-400 border-rose-500/30'"
                  >
                    {{ plug.is_online ? 'Online' : 'Offline' }}
                  </span>
                </td>
                <td class="p-4 text-[#dfe2ef]">{{ plug.ip_address }}</td>
                <td class="p-4 text-[#86948a] truncate max-w-[120px]">{{ plug.device_id }}</td>
                <td class="p-4 text-[#86948a]">
                  Run: {{ plug.power_threshold_running }}W | Idle: {{ plug.power_threshold_idle }}W
                </td>
                <td class="p-4 text-right space-x-2">
                  <button 
                    @click="testPlugConnection(plug.id)"
                    :disabled="testingPlugId === plug.id"
                    class="bg-[#181b25] hover:bg-[#262a34] text-[#4edea3] px-3 py-1 rounded-lg text-[11px] font-bold border border-white/10 transition"
                  >
                    {{ testingPlugId === plug.id ? 'Testing...' : '📡 Test LAN' }}
                  </button>
                  <button 
                    @click="openEditPlugModal(plug)"
                    class="bg-[#181b25] hover:bg-[#262a34] text-indigo-300 px-3 py-1 rounded-lg text-[11px] font-bold border border-white/10 transition"
                  >
                    ✏️ Edit
                  </button>
                  <button 
                    @click="deleteSmartPlug(plug.id)"
                    class="bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 px-3 py-1 rounded-lg text-[11px] font-bold border border-rose-500/30 transition"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
              <tr v-if="smartPlugs.length === 0">
                <td colspan="6" class="p-8 text-center text-[#86948a] italic">
                  No smart plugs registered yet. Click "Register Smart Plug" to pair your local Wipro plug.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <!-- Modal Form for Registering/Editing Plugs -->
    <div v-if="isModalOpen" class="fixed inset-0 z-50 bg-[#090D16]/90 backdrop-blur-xl flex items-center justify-center p-4">
      <div class="glass-card rounded-3xl p-6 max-w-lg w-full space-y-4 glow-emerald">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <h3 class="text-sm font-mono font-bold text-white uppercase">
            {{ editingPlugId ? 'EDIT_SMART_PLUG_CONFIG' : 'REGISTER_WIPRO_SMART_PLUG' }}
          </h3>
          <button @click="isModalOpen = false" class="text-[#86948a] hover:text-white font-mono">✕</button>
        </div>

        <form @submit.prevent="saveSmartPlug" class="space-y-3 font-mono text-xs">
          <div>
            <label class="block text-[#86948a] font-medium mb-1">Assign to Machine</label>
            <select v-model="plugForm.machine_id" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]">
              <option value="">-- Select Machine --</option>
              <option v-for="m in machinesList" :key="m.id" :value="m.id">{{ m.name }}</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[#86948a] font-medium mb-1">IP Address (Local LAN)</label>
              <input v-model="plugForm.ip_address" required placeholder="192.168.1.50" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
            </div>
            <div>
              <label class="block text-[#86948a] font-medium mb-1">Protocol Version</label>
              <select v-model="plugForm.protocol_version" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]">
                <option value="3.3">3.3 (Standard Wipro)</option>
                <option value="3.1">3.1 (Older)</option>
                <option value="3.4">3.4 (Newer Tuya)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-[#86948a] font-medium mb-1">Tuya Device ID</label>
            <input v-model="plugForm.device_id" required placeholder="bf1234567890abcdef" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
          </div>

          <div>
            <label class="block text-[#86948a] font-medium mb-1">Tuya Local Key</label>
            <input v-model="plugForm.local_key" required type="text" placeholder="16-character local key" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
          </div>

          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-[#86948a] font-medium mb-1">Run (W)</label>
              <input v-model.number="plugForm.power_threshold_running" type="number" step="0.1" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
            </div>
            <div>
              <label class="block text-[#86948a] font-medium mb-1">Idle (W)</label>
              <input v-model.number="plugForm.power_threshold_idle" type="number" step="0.1" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
            </div>
            <div>
              <label class="block text-[#86948a] font-medium mb-1">Soak (s)</label>
              <input v-model.number="plugForm.debounce_seconds" type="number" class="w-full bg-[#0a0e17] border border-white/10 rounded-xl p-2.5 text-white focus:outline-none focus:border-[#10b981]" />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-3 border-t border-white/10">
            <button type="button" @click="isModalOpen = false" class="px-4 py-2 bg-[#181b25] hover:bg-[#262a34] text-white rounded-xl font-bold">Cancel</button>
            <button type="submit" class="px-4 py-2 bg-[#10b981] hover:bg-[#4edea3] text-[#003824] rounded-xl font-bold uppercase">Save Plug</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style>
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
