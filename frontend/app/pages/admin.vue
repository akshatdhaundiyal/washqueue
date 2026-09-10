<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  Layers,
  Zap,
  Database,
  Users,
  Shield,
  ArrowLeft,
  RefreshCw,
  Sun,
  Moon,
  Lock,
  KeyRound,
  Check,
  Activity
} from 'lucide-vue-next'
import AdminSidebar from '~/components/admin/AdminSidebar.vue'
import AdminTopHeader from '~/components/admin/AdminTopHeader.vue'
import AppBranding from '~/components/common/AppBranding.vue'
import AdminAuthOverlay from '~/components/admin/AdminAuthOverlay.vue'
import AdminMetricsBanner from '~/components/admin/AdminMetricsBanner.vue'
import FleetTab from '~/components/admin/FleetTab.vue'
import IotTab from '~/components/admin/IotTab.vue'
import DatabasePortalTab from '~/components/admin/DatabasePortalTab.vue'
import UsersSettingsTab from '~/components/admin/UsersSettingsTab.vue'
import PowerGraphModal from '~/components/admin/PowerGraphModal.vue'
import PlugFormModal from '~/components/admin/PlugFormModal.vue'
import ThresholdTunerModal from '~/components/admin/ThresholdTunerModal.vue'
import AdminToastStack from '~/components/admin/AdminToastStack.vue'

const config = useRuntimeConfig()
const apiBase = config.public.apiBaseUrl

// Global Theme State (Defaults to Light Mode)
const { isDark: darkMode, toggleTheme, setTheme } = useAppTheme()

// Admin Navigation Tab State
const currentAdminTab = ref('fleet') // 'fleet' | 'iot' | 'database' | 'users'

// Admin Auth State
const isAuthenticated = ref(false)
const inputPin = ref('')
const pinError = ref('')
const isAuthenticating = ref(false)

// Visual Threshold Tuner Studio State
const isTunerModalOpen = ref(false)
const tunerPlug = ref(null)
const tunerHistory = ref(null)
const tunerHistoryLoading = ref(false)

// Admin Data State
const adminMachines = ref([])
const smartPlugs = ref([])
const usageStats = ref(null)
const machinesList = ref([])
const allUsers = ref([])
const usersLoading = ref(false)
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

// 4-Hour Power Graph State
const isGraphModalOpen = ref(false)
const graphPlug = ref(null)
const activeHistory = ref(null)
const historyLoading = ref(false)

// Open 4-hour Power Graph
const openPowerGraph = async (plug) => {
  graphPlug.value = plug
  isGraphModalOpen.value = true
  historyLoading.value = true
  activeHistory.value = null

  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const data = await $fetch(`${apiBase}/api/smart-plugs/${plug.id}/history?hours=4`, { headers })
    activeHistory.value = data
  } catch (err) {
    addToast('Failed to load 4-hour telemetry history.', 'error')
  } finally {
    historyLoading.value = false
  }
}

// Open Visual Threshold Tuner Studio
const openThresholdTuner = async (plug) => {
  tunerPlug.value = plug
  isTunerModalOpen.value = true
  tunerHistoryLoading.value = true
  tunerHistory.value = null

  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const data = await $fetch(`${apiBase}/api/smart-plugs/${plug.id}/history?hours=4`, { headers })
    tunerHistory.value = data
  } catch (err) {
    addToast('Failed to load telemetry history for tuner.', 'error')
  } finally {
    tunerHistoryLoading.value = false
  }
}

// Save Calibration from Visual Tuner
const savePlugCalibration = async (calibrationData) => {
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const res = await $fetch(`${apiBase}/api/smart-plugs/${calibrationData.plug_id}/calibration`, {
      method: 'PATCH',
      headers,
      body: {
        power_threshold_running: calibrationData.power_threshold_running,
        power_threshold_idle: calibrationData.power_threshold_idle,
        debounce_seconds: calibrationData.debounce_seconds,
        apply_to_similar_machines: calibrationData.apply_to_similar_machines
      }
    })

    const target = smartPlugs.value.find(p => p.id === calibrationData.plug_id)
    if (target) {
      target.power_threshold_running = calibrationData.power_threshold_running
      target.power_threshold_idle = calibrationData.power_threshold_idle
      target.debounce_seconds = calibrationData.debounce_seconds
    }

    addToast(res.message || 'Threshold calibration saved!', 'success')
    isTunerModalOpen.value = false
    fetchAdminData(true)
  } catch (err) {
    addToast(err?.data?.detail || 'Failed to update calibration.', 'error')
  }
}

// Simulate Test Wash Cycle from Tuner Modal
const simulateTestCycle = async (plugId) => {
  if (!plugId) return
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const res = await $fetch(`${apiBase}/api/smart-plugs/${plugId}/simulate-cycle?minutes=25`, {
      method: 'POST',
      headers
    })
    addToast(res.message || 'Synthetic test wash cycle generated!', 'success')
    // Refresh tuner history immediately to update the SVG canvas
    if (tunerPlug.value) {
      await openThresholdTuner(tunerPlug.value)
    }
  } catch (err) {
    addToast(err?.data?.detail || 'Simulation failed.', 'error')
  }
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

// Verify Admin PIN
const verifyPin = async (pinValue) => {
  if (!pinValue) return
  inputPin.value = pinValue
  isAuthenticating.value = true
  pinError.value = ''

  try {
    const res = await $fetch(`${apiBase}/api/admin/verify-pin`, {
      method: 'POST',
      body: { pin: pinValue }
    })

    if (res.valid) {
      isAuthenticated.value = true
      sessionStorage.setItem('admin_pin', pinValue)
      addToast('Admin authenticated successfully!', 'success')
      fetchAdminData()
    }
  } catch (err) {
    pinError.value = err.data?.detail || 'Invalid Admin PIN.'
  } finally {
    isAuthenticating.value = false
  }
}

const lockAdminSession = () => {
  isAuthenticated.value = false
  inputPin.value = ''
  sessionStorage.removeItem('admin_pin')
  addToast('Admin session locked.', 'info')
}

const isSyncing = ref(false)
const pollingPlugId = ref(null)
const togglingSwitchId = ref(null)
const isAutoRefresh = ref(true)
let autoRefreshTimer = null

// Total power consumption across all plugs
const totalLivePower = computed(() => {
  return smartPlugs.value.reduce((sum, p) => {
    return sum + (p.latest_telemetry?.power_w || 0)
  }, 0).toFixed(1)
})

const averageVoltage = computed(() => {
  const activeVoltages = smartPlugs.value
    .map(p => p.latest_telemetry?.voltage_v)
    .filter(v => v !== null && v !== undefined && v > 0)
  if (activeVoltages.length === 0) return '0.0'
  const avg = activeVoltages.reduce((a, b) => a + b, 0) / activeVoltages.length
  return avg.toFixed(1)
})

// Auto-refresh interval
onMounted(() => {
  const savedPin = sessionStorage.getItem('admin_pin')
  if (savedPin) {
    inputPin.value = savedPin
    verifyPin(savedPin)
  }

  autoRefreshTimer = setInterval(() => {
    if (isAuthenticated.value && isAutoRefresh.value && !loading.value) {
      fetchAdminData(true) // Silent fallback fetch
    }
  }, 1000)
})

onUnmounted(() => {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer)
})

// Real-time Local Edge WebSocket live stream (< 10ms instantaneous telemetry push)
const { isConnected: isWsConnected } = useLocalWebSocket(apiBase, (event) => {
  if (event.type === 'telemetry_update' && event.plug_id) {
    const targetPlug = smartPlugs.value.find(p => p.id === event.plug_id)
    if (targetPlug) {
      targetPlug.latest_telemetry = event.telemetry
      targetPlug.is_online = event.is_online
    }

    // Dynamic graph append
    if (isGraphModalOpen.value && graphPlug.value?.id === event.plug_id && activeHistory.value) {
      const newPt = {
        timestamp: event.telemetry.recorded_at,
        power_w: event.telemetry.power_w || 0.0,
        voltage_v: event.telemetry.voltage_v,
        current_ma: event.telemetry.current_ma,
        source: event.telemetry.source || 'local'
      }
      activeHistory.value.series.push(newPt)
      if (newPt.source === 'local') activeHistory.value.local_points_count++
      else activeHistory.value.cloud_points_count++
      if (newPt.power_w > activeHistory.value.peak_power_w) {
        activeHistory.value.peak_power_w = newPt.power_w
      }
    }

    // Dynamic tuner append
    if (isTunerModalOpen.value && tunerPlug.value?.id === event.plug_id && tunerHistory.value) {
      const newPt = {
        timestamp: event.telemetry.recorded_at,
        power_w: event.telemetry.power_w || 0.0,
        voltage_v: event.telemetry.voltage_v,
        current_ma: event.telemetry.current_ma,
        source: event.telemetry.source || 'local'
      }
      tunerHistory.value.series.push(newPt)
    }
  } else if (event.type === 'machine_status_change') {
    fetchAdminData(true)
  } else if (event.type === 'calibration_updated' && event.plug_id) {
    const target = smartPlugs.value.find(p => p.id === event.plug_id)
    if (target) {
      target.power_threshold_running = event.power_threshold_running
      target.power_threshold_idle = event.power_threshold_idle
      target.debounce_seconds = event.debounce_seconds
    }
    addToast('Thresholds updated across active fleet nodes.', 'info')
  } else if (event.type === 'nudge_alert') {
    addToast(event.admin_message || event.message || 'Resident sent laundry collection ping.', 'info')
  }
})

// Fetch all Admin Data
const fetchAdminData = async (silent = false) => {
  if (!isAuthenticated.value) return
  if (!silent) loading.value = true
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

    if (dbStatus.value.tables.length === 0) {
      fetchDbStatus(dbTarget.value)
    }

    if (allUsers.value.length === 0) {
      fetchAllUsers()
    }
  } catch (err) {
    if (err.status === 403) {
      isAuthenticated.value = false
      sessionStorage.removeItem('admin_pin')
      pinError.value = 'Session expired. Please enter Admin PIN again.'
    } else if (!silent) {
      errorMsg.value = 'Failed to load admin data from server.'
    }
  } finally {
    if (!silent) loading.value = false
  }
}

// Fetch all registered users for Tab 4
const fetchAllUsers = async () => {
  usersLoading.value = true
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const users = await $fetch(`${apiBase}/api/admin/users`, { headers })
    allUsers.value = users
  } catch (err) {
    console.debug('Failed to fetch user directory:', err)
  } finally {
    usersLoading.value = false
  }
}

// Instantaneous Telemetry Poll on demand
const pollInstantTelemetry = async (plugId) => {
  pollingPlugId.value = plugId
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const res = await $fetch(`${apiBase}/api/smart-plugs/${plugId}/instant-telemetry`, { headers })
    addToast(`Telemetry updated: ${res.power_w}W, ${res.voltage_v}V`, 'success')
    fetchAdminData(true)
  } catch (err) {
    addToast('Failed to fetch instant telemetry.', 'error')
  } finally {
    pollingPlugId.value = null
  }
}

// Toggle smart plug relay switch remotely
const togglePlugSwitch = async (plugId, currentSwitchState) => {
  const nextState = !currentSwitchState
  togglingSwitchId.value = plugId
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    await $fetch(`${apiBase}/api/smart-plugs/${plugId}/switch?on=${nextState}`, { method: 'POST', headers })
    const target = smartPlugs.value.find(p => p.id === plugId)
    if (target) {
      if (!target.latest_telemetry) target.latest_telemetry = {}
      target.latest_telemetry.switch_on = nextState
      target.is_online = true
    }
    addToast(`Relay successfully turned ${nextState ? 'ON' : 'OFF'}!`, 'success')
    fetchAdminData(true)
  } catch (err) {
    addToast('Failed to toggle smart plug relay switch.', 'error')
  } finally {
    togglingSwitchId.value = null
  }
}

// Cloud Auto-Sync
const syncPlugsFromCloud = async () => {
  isSyncing.value = true
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const res = await $fetch(`${apiBase}/api/smart-plugs/sync-tuya-cloud`, {
      method: 'POST',
      headers
    })
    addToast(`Cloud Sync: ${res.message} (${res.plugs_synced} synced)`, 'success')
    fetchAdminData()
  } catch (err) {
    addToast('Failed to auto-sync with Tuya Cloud.', 'error')
  } finally {
    isSyncing.value = false
  }
}

// Force-clear machine
const forceClearMachine = async (machineId) => {
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    await $fetch(`${apiBase}/api/admin/machines/${machineId}/force-clear`, {
      method: 'POST',
      headers
    })
    addToast('Machine force cleared and unlocked.', 'success')
    fetchAdminData()
  } catch (err) {
    addToast('Failed to force clear machine.', 'error')
  }
}

// Trigger overdue scheduler tick manually
const triggerSchedulerTick = async () => {
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const res = await $fetch(`${apiBase}/api/scheduler/tick`, {
      method: 'POST',
      headers
    })
    addToast(`Scheduler tick complete: ${res.updated_machines.length} machine(s) transitioned to idle_full.`, 'info')
    fetchAdminData()
  } catch (err) {
    addToast('Failed to trigger scheduler tick.', 'error')
  }
}

// Open modal for new plug
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

// Open modal to edit plug
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

const saveSmartPlug = async (formData) => {
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const payload = {
      ...formData,
      machine_id: formData.machine_id ? formData.machine_id : null
    }

    if (editingPlugId.value) {
      await $fetch(`${apiBase}/api/smart-plugs/${editingPlugId.value}`, {
        method: 'PUT',
        headers,
        body: payload
      })
      addToast('Smart plug updated successfully.', 'success')
    } else {
      await $fetch(`${apiBase}/api/smart-plugs`, {
        method: 'POST',
        headers,
        body: payload
      })
      addToast('New smart plug registered.', 'success')
    }
    isModalOpen.value = false
    fetchAdminData()
  } catch (err) {
    addToast(err.data?.detail || 'Failed to save smart plug.', 'error')
  }
}

const deleteSmartPlug = async (plugId) => {
  if (!confirm('Are you sure you want to delete this smart plug registration?')) return
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    await $fetch(`${apiBase}/api/smart-plugs/${plugId}`, {
      method: 'DELETE',
      headers
    })
    addToast('Smart plug removed.', 'info')
    fetchAdminData()
  } catch (err) {
    addToast('Failed to delete smart plug.', 'error')
  }
}

// ==========================================
// Database Explorer & Portal State
// ==========================================
const dbTarget = ref('local')
const dbStatus = ref({ connected: true, dialect: 'sqlite', tables: [], error: null })
const dbStatusLoading = ref(false)
const selectedTable = ref('machines')
const tableData = ref({ total: 0, limit: 25, offset: 0, columns: [], rows: [] })
const tableLoading = ref(false)
const queryResult = ref(null)
const queryLoading = ref(false)
const queryError = ref('')

const fetchDbStatus = async (target = dbTarget.value) => {
  dbStatusLoading.value = true
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const data = await $fetch(`${apiBase}/api/admin/database/status?target=${target}`, { headers })
    dbStatus.value = data
    if (data.tables && data.tables.length > 0) {
      if (!data.tables.some(t => t.name === selectedTable.value)) {
        selectedTable.value = data.tables[0].name
      }
      fetchTableData(selectedTable.value, 0)
    }
  } catch (err) {
    dbStatus.value = { connected: false, dialect: 'unknown', tables: [], error: err?.data?.detail || err.message }
  } finally {
    dbStatusLoading.value = false
  }
}

const switchDbTarget = (target) => {
  dbTarget.value = target
  queryResult.value = null
  queryError.value = ''
  fetchDbStatus(target)
}

const fetchTableData = async (tableName = selectedTable.value, offset = 0) => {
  selectedTable.value = tableName
  tableLoading.value = true
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const data = await $fetch(`${apiBase}/api/admin/database/table-data?target=${dbTarget.value}&table_name=${tableName}&limit=25&offset=${offset}`, { headers })
    tableData.value = data
  } catch (err) {
    addToast(err?.data?.detail || 'Failed to load table records.', 'error')
  } finally {
    tableLoading.value = false
  }
}

const runCustomQuery = async (queryText) => {
  if (!queryText.trim()) return
  queryLoading.value = true
  queryError.value = ''
  const headers = { 'X-Admin-PIN': inputPin.value }
  try {
    const data = await $fetch(`${apiBase}/api/admin/database/query`, {
      method: 'POST',
      headers,
      body: { target: dbTarget.value, query: queryText }
    })
    queryResult.value = data
    addToast(`Query executed in ${data.execution_time_ms}ms (${data.row_count} rows)`, 'success')
  } catch (err) {
    queryError.value = err?.data?.detail || err.message || 'Failed to execute query.'
  } finally {
    queryLoading.value = false
  }
}

const exportQueryResults = () => {
  if (!queryResult.value || !queryResult.value.rows) return
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(queryResult.value.rows, null, 2))
  const downloadAnchor = document.createElement('a')
  downloadAnchor.setAttribute("href", dataStr)
  downloadAnchor.setAttribute("download", `washqueue_query_${dbTarget.value}_${Date.now()}.json`)
  document.body.appendChild(downloadAnchor)
  downloadAnchor.click()
  downloadAnchor.remove()
  addToast('Exported query results as JSON!', 'info')
}
</script>

<template>
  <div 
    :class="[
      'min-h-screen flex flex-col md:flex-row font-sans antialiased transition-colors duration-200',
      darkMode ? 'bg-[#0c0e14] text-slate-100' : 'bg-[#f6f8fa] text-slate-900'
    ]"
  >
    <!-- ========================================================================= -->
    <!-- UN-AUTHENTICATED STATE: FULL PAGE OVERLAY WITH UNLOCK CARD                -->
    <!-- ========================================================================= -->
    <div v-if="!isAuthenticated" class="w-full min-h-screen flex flex-col justify-between">
      <!-- Minimal Header with Full AppBranding -->
      <header
        :class="[
          'w-full px-5 py-4 border-b flex items-center justify-between transition-colors',
          darkMode ? 'bg-[#10131a]/80 border-slate-800/80 backdrop-blur-md' : 'bg-white/80 border-slate-200/80 backdrop-blur-md'
        ]"
      >
        <NuxtLink to="/" class="flex items-center gap-2.5 group">
          <AppBranding
            :compact="true"
            :dark-mode="darkMode"
            logo-mode="icon"
          />
        </NuxtLink>

        <div class="flex items-center gap-2.5">
          <NuxtLink
            to="/login"
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all',
              darkMode ? 'text-slate-400 hover:text-white hover:bg-slate-800/80' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            ]"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Login Portal</span>
          </NuxtLink>

          <!-- Theme Toggle -->
          <div class="flex items-center p-0.5 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80">
            <button
              @click="setTheme('light')"
              :class="[
                'p-1.5 rounded-full transition-all',
                !darkMode ? 'bg-white text-amber-500 shadow-xs' : 'text-slate-400 hover:text-slate-700 dark:hover:text-white'
              ]"
              title="Light Mode"
            >
              <Sun class="w-3.5 h-3.5" />
            </button>
            <button
              @click="setTheme('dark')"
              :class="[
                'p-1.5 rounded-full transition-all',
                darkMode ? 'bg-slate-900 text-sky-400 shadow-xs' : 'text-slate-400 hover:text-slate-700'
              ]"
              title="Dark Mode"
            >
              <Moon class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </header>

      <!-- Centered PIN Overlay -->
      <main class="flex-1 flex items-center justify-center p-4">
        <AdminAuthOverlay
          :dark-mode="darkMode"
          :pin-error="pinError"
          :is-authenticating="isAuthenticating"
          @verify-pin="verifyPin"
        />
      </main>

      <footer :class="['w-full py-4 text-center text-xs border-t transition-colors', darkMode ? 'border-slate-800 text-slate-500' : 'border-slate-200 text-slate-500']">
        WashQueue Telemetry & IoT Control Hub • Block B
      </footer>
    </div>

    <!-- ========================================================================= -->
    <!-- AUTHENTICATED ADMIN CONSOLE: DESKTOP SIDEBAR + HEADER + MAIN CONTENT      -->
    <!-- ========================================================================= -->
    <template v-else>
      <!-- DESKTOP LEFT SIDEBAR -->
      <AdminSidebar
        :current-admin-tab="currentAdminTab"
        :machines-count="adminMachines.length"
        :plugs-count="smartPlugs.length"
        :db-target="dbTarget"
        :users-count="allUsers.length"
        :dark-mode="darkMode"
        @update:current-admin-tab="currentAdminTab = $event"
        @set-theme="setTheme($event)"
        @lock-session="lockAdminSession"
      />

      <!-- RIGHT COLUMN: TOP HEADER + MAIN CONTENT -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- TOP HEADER (Mobile & Desktop) -->
        <AdminTopHeader
          :current-admin-tab="currentAdminTab"
          :is-ws-connected="isWsConnected"
          :loading="loading"
          :is-auto-refresh="isAutoRefresh"
          :dark-mode="darkMode"
          @refresh-data="fetchAdminData(false)"
          @update:is-auto-refresh="isAutoRefresh = $event"
          @lock-session="lockAdminSession"
        />

        <!-- MAIN SCROLLABLE DASHBOARD -->
        <main class="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 lg:p-10 pb-24 md:pb-10">
          <div class="max-w-7xl mx-auto space-y-6">
            <!-- Collapsible Quick Metrics Banner -->
            <AdminMetricsBanner
              :dark-mode="darkMode"
              :is-ws-connected="isWsConnected"
              :total-live-power="totalLivePower"
              :average-voltage="averageVoltage"
              :online-plugs-count="smartPlugs.filter(p => p.is_online).length"
              :total-plugs-count="smartPlugs.length"
              :active-machines-count="adminMachines.filter(m => m.status === 'in_use').length"
              :total-machines-count="adminMachines.length"
            />

            <!-- TAB 1: FLEET & BOOKINGS -->
            <FleetTab
              v-if="currentAdminTab === 'fleet'"
              :machines="adminMachines"
              :dark-mode="darkMode"
              @check-overdue="triggerSchedulerTick"
              @force-clear="forceClearMachine"
            />

            <!-- TAB 2: SMART PLUGS & IOT TELEMETRY -->
            <IotTab
              v-if="currentAdminTab === 'iot'"
              :smart-plugs="smartPlugs"
              :dark-mode="darkMode"
              :is-ws-connected="isWsConnected"
              :is-auto-refresh="isAutoRefresh"
              :is-syncing="isSyncing"
              :polling-plug-id="pollingPlugId"
              :toggling-switch-id="togglingSwitchId"
              @sync-cloud="syncPlugsFromCloud"
              @add-plug="openAddPlugModal"
              @toggle-switch="togglePlugSwitch"
              @poll-instant="pollInstantTelemetry"
              @open-graph="openPowerGraph"
              @open-tuner="openThresholdTuner"
              @edit-plug="openEditPlugModal"
              @delete-plug="deleteSmartPlug"
            />

            <!-- TAB 3: DUAL DATABASE PORTAL -->
            <DatabasePortalTab
              v-if="currentAdminTab === 'database'"
              :db-target="dbTarget"
              :db-status="dbStatus"
              :selected-table="selectedTable"
              :table-data="tableData"
              :table-loading="tableLoading"
              :query-result="queryResult"
              :query-loading="queryLoading"
              :query-error="queryError"
              :dark-mode="darkMode"
              @switch-target="switchDbTarget"
              @refresh-status="fetchDbStatus"
              @select-table="fetchTableData"
              @run-query="runCustomQuery"
              @export-json="exportQueryResults"
            />

            <!-- TAB 4: USERS & SYSTEM SETTINGS -->
            <UsersSettingsTab
              v-if="currentAdminTab === 'users'"
              :users="allUsers"
              :users-loading="usersLoading"
              :is-ws-connected="isWsConnected"
              :dark-mode="darkMode"
              @refresh-users="fetchAllUsers"
              @lock-session="lockAdminSession"
            />
          </div>
        </main>
      </div>

      <!-- MOBILE BOTTOM FLOATING DOCK (md:hidden) -->
      <div class="md:hidden fixed bottom-4 left-0 right-0 z-40 flex justify-center px-4 pointer-events-none">
        <div
          :class="[
            'p-1.5 rounded-full border flex items-center gap-1 shadow-xl backdrop-blur-md pointer-events-auto',
            darkMode ? 'bg-slate-900/95 border-slate-800 text-slate-300' : 'bg-white/95 border-slate-200/90 text-slate-700 shadow-slate-200/60'
          ]"
        >
          <button
            @click="currentAdminTab = 'fleet'"
            :class="[
              'px-3.5 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold transition-all',
              currentAdminTab === 'fleet' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
            ]"
          >
            <Layers class="w-3.5 h-3.5" /> Fleet
          </button>

          <button
            @click="currentAdminTab = 'iot'"
            :class="[
              'px-3.5 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold transition-all',
              currentAdminTab === 'iot' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
            ]"
          >
            <Zap class="w-3.5 h-3.5 text-amber-500" /> IoT
          </button>

          <button
            @click="currentAdminTab = 'database'"
            :class="[
              'px-3.5 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold transition-all',
              currentAdminTab === 'database' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
            ]"
          >
            <Database class="w-3.5 h-3.5 text-sky-500" /> DB
          </button>

          <button
            @click="currentAdminTab = 'users'"
            :class="[
              'px-3.5 py-2 rounded-full flex items-center gap-1.5 text-xs font-bold transition-all',
              currentAdminTab === 'users' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400'
            ]"
          >
            <Users class="w-3.5 h-3.5 text-emerald-500" /> Users
          </button>
        </div>
      </div>
    </template>

    <!-- 4-HOUR POWER GRAPH MODAL -->
    <PowerGraphModal
      :is-open="isGraphModalOpen"
      :plug="graphPlug"
      :history="activeHistory"
      :loading="historyLoading"
      :dark-mode="darkMode"
      @close="isGraphModalOpen = false"
    />

    <!-- VISUAL THRESHOLD CALIBRATION STUDIO MODAL (FOR NON-TECH ADMINS) -->
    <ThresholdTunerModal
      :is-open="isTunerModalOpen"
      :plug="tunerPlug"
      :history="tunerHistory"
      :history-loading="tunerHistoryLoading"
      :dark-mode="darkMode"
      @close="isTunerModalOpen = false"
      @save-calibration="savePlugCalibration"
      @simulate-cycle="simulateTestCycle"
    />

    <!-- MODAL FORM FOR REGISTERING/EDITING PLUGS -->
    <PlugFormModal
      :is-open="isModalOpen"
      :editing-plug-id="editingPlugId"
      :initial-form="plugForm"
      :machines-list="machinesList"
      :dark-mode="darkMode"
      @close="isModalOpen = false"
      @save="saveSmartPlug"
    />

    <!-- TOAST NOTIFICATIONS FLOATING STACK -->
    <AdminToastStack :toasts="toasts" />
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
  animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
</style>
