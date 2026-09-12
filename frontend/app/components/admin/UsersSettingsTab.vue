<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  RefreshCw,
  Search,
  Lock,
  School,
  Building2,
  Upload,
  Image as ImageIcon,
  RotateCcw,
  Check,
  Sparkles,
  Trash2,
  Globe,
  Clock,
  AlertCircle,
  QrCode,
  Maximize2,
  Copy
} from 'lucide-vue-next'
import QRCode from 'qrcode'
import AppLogo from '~/components/common/AppLogo.vue'
import AppBranding from '~/components/common/AppBranding.vue'
import AdminQrKioskModal from '~/components/admin/AdminQrKioskModal.vue'

const props = defineProps({
  users: {
    type: Array,
    default: () => []
  },
  usersLoading: {
    type: Boolean,
    default: false
  },
  isWsConnected: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  adminPin: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['refresh-users', 'lock-session'])

const {
  institutionName,
  institutionShort,
  institutionLogo,
  hostelName,
  hostelLogo,
  hubLocation,
  resetDefaults
} = useHostelBranding()

const showSavedFeedback = ref(false)
let saveFeedbackTimer = null

const triggerSavedNotice = () => {
  if (saveFeedbackTimer) clearTimeout(saveFeedbackTimer)
  showSavedFeedback.value = true
  saveFeedbackTimer = setTimeout(() => {
    showSavedFeedback.value = false
  }, 2500)
}

const handleOrgLogoUpload = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (event) => {
    institutionLogo.value = event.target?.result || ''
    triggerSavedNotice()
  }
  reader.readAsDataURL(file)
}

const handleHostelLogoUpload = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (event) => {
    hostelLogo.value = event.target?.result || ''
    triggerSavedNotice()
  }
  reader.readAsDataURL(file)
}

const clearOrgLogo = () => {
  institutionLogo.value = ''
  triggerSavedNotice()
}

const clearHostelLogo = () => {
  hostelLogo.value = ''
  triggerSavedNotice()
}

const handleResetDefaults = () => {
  resetDefaults()
  triggerSavedNotice()
}

// Timezone & Regional Clock State
const {
  selectedTimezone,
  is24Hour,
  activeTimezoneLabel,
  availablePresets,
  defaultTimezone,
  isValidTimezone,
  setTimezone,
  setTimeFormat,
  resetToDefault: resetTimezoneDefault,
  formatDate,
  formatTimeWithSeconds,
  formatDateTime,
  getTimezoneAbbr,
  getTimezoneOffsetStr
} = useAppTimezone()

const customTimezoneInput = ref('')
const customTzError = ref('')
const showTimezoneSavedFeedback = ref(false)
let tzFeedbackTimer = null

const triggerTimezoneSavedNotice = () => {
  if (tzFeedbackTimer) clearTimeout(tzFeedbackTimer)
  showTimezoneSavedFeedback.value = true
  tzFeedbackTimer = setTimeout(() => {
    showTimezoneSavedFeedback.value = false
  }, 2500)
}

const syncTimezoneToBackend = async (tz) => {
  if (!props.adminPin) return
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
    await $fetch(`${apiBase}/api/admin/settings`, {
      method: 'POST',
      headers: { 'X-Admin-PIN': props.adminPin },
      body: { timezone: tz }
    })
  } catch (err) {
    console.error('Failed to sync timezone to backend:', err)
  }
}

const handlePresetChange = async (event) => {
  const tz = event.target.value
  if (tz) {
    customTzError.value = ''
    setTimezone(tz)
    triggerTimezoneSavedNotice()
    await syncTimezoneToBackend(tz)
  }
}

const handleApplyCustomTimezone = async () => {
  customTzError.value = ''
  const tz = customTimezoneInput.value.trim()
  if (!tz) return
  if (!isValidTimezone(tz)) {
    customTzError.value = `Invalid IANA timezone: "${tz}". Examples: "America/New_York", "Asia/Kathmandu", "Europe/Rome".`
    return
  }
  setTimezone(tz)
  triggerTimezoneSavedNotice()
  await syncTimezoneToBackend(tz)
  customTimezoneInput.value = ''
}

const handleToggle24Hour = (is24) => {
  setTimeFormat(is24)
  triggerTimezoneSavedNotice()
}

const handleResetTimezone = async () => {
  resetTimezoneDefault()
  customTimezoneInput.value = ''
  customTzError.value = ''
  triggerTimezoneSavedNotice()
  await syncTimezoneToBackend(defaultTimezone)
}

// Live Regional Clock Preview
const liveClockTime = ref('')
const liveClockDate = ref('')
let clockInterval = null

const refreshLiveClock = () => {
  const now = new Date()
  liveClockTime.value = formatTimeWithSeconds(now)
  liveClockDate.value = formatDate(now)
}

onMounted(() => {
  refreshLiveClock()
  clockInterval = setInterval(refreshLiveClock, 1000)
  fetchOnboardingQr()
  startQrRotationTicker()
  fetchPendingUsers()
})

onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
  if (qrTickerInterval) clearInterval(qrTickerInterval)
})

// Resident Onboarding QR Station State
const qrData = ref(null)
const qrSecondsRemaining = ref(60)
const qrLoading = ref(false)
const qrSvgPreview = ref('')
const customBaseUrl = ref('')
const isKioskOpen = ref(false)
const qrCopied = ref(false)
let qrTickerInterval = null

const fetchOnboardingQr = async () => {
  if (!props.adminPin) return
  qrLoading.value = true
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
    const query = customBaseUrl.value.trim() ? `?base_url=${encodeURIComponent(customBaseUrl.value.trim())}` : ''
    const data = await $fetch(`${apiBase}/api/admin/onboarding-qr${query}`, {
      headers: { 'X-Admin-PIN': props.adminPin }
    })
    qrData.value = data
    qrSecondsRemaining.value = data.ttl_seconds || 60
    
    // Generate inline SVG
    qrSvgPreview.value = await QRCode.toString(data.default_url, {
      type: 'svg',
      margin: 1,
      color: {
        dark: props.darkMode ? '#ffffff' : '#0f172a',
        light: '#00000000'
      }
    })
  } catch (err) {
    console.error('Failed to fetch onboarding QR:', err)
  } finally {
    qrLoading.value = false
  }
}

const copyQrUrl = async () => {
  if (!qrData.value?.default_url) return
  try {
    await navigator.clipboard.writeText(qrData.value.default_url)
    qrCopied.value = true
    setTimeout(() => { qrCopied.value = false }, 2000)
  } catch (e) {}
}

const startQrRotationTicker = () => {
  if (qrTickerInterval) clearInterval(qrTickerInterval)
  qrTickerInterval = setInterval(() => {
    if (qrSecondsRemaining.value > 1) {
      qrSecondsRemaining.value--
    } else {
      fetchOnboardingQr()
    }
  }, 1000)
}

const userSearchQuery = ref('')

const filteredUsers = computed(() => {
  if (!userSearchQuery.value.trim()) return props.users
  const q = userSearchQuery.value.toLowerCase().trim()
  return props.users.filter(u => {
    return (
      (u.name && u.name.toLowerCase().includes(q)) ||
      (u.room_number && u.room_number.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q)) ||
      (u.role && u.role.toLowerCase().includes(q)) ||
      (u.hostel && u.hostel.toLowerCase().includes(q)) ||
      (u.university && u.university.toLowerCase().includes(q)) ||
      (u.college && u.college.toLowerCase().includes(q))
    )
  })
})

const pendingUsers = ref([])
const pendingLoading = ref(false)
const actionInProgressId = ref(null)

const fetchPendingUsers = async () => {
  if (!props.adminPin) return
  pendingLoading.value = true
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
    const data = await $fetch(`${apiBase}/api/admin/pending-registrations`, {
      headers: { 'X-Admin-PIN': props.adminPin }
    })
    pendingUsers.value = data || []
  } catch (err) {
    console.error('Failed to fetch pending registrations:', err)
  } finally {
    pendingLoading.value = false
  }
}

const approveUser = async (user) => {
  if (!props.adminPin) return
  actionInProgressId.value = user.id
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
    await $fetch(`${apiBase}/api/admin/registrations/${user.id}/approve`, {
      method: 'POST',
      headers: { 'X-Admin-PIN': props.adminPin }
    })
    await Promise.all([
      fetchPendingUsers(),
      emit('refresh-users')
    ])
  } catch (err) {
    console.error('Failed to approve registration:', err)
    alert(err.data?.detail || 'Failed to approve registration.')
  } finally {
    actionInProgressId.value = null
  }
}

const rejectUser = async (user) => {
  if (!props.adminPin) return
  if (!confirm(`Are you sure you want to reject the registration request for ${user.name} (Room ${user.room_number})?`)) {
    return
  }
  actionInProgressId.value = user.id
  try {
    const config = useRuntimeConfig()
    const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
    await $fetch(`${apiBase}/api/admin/registrations/${user.id}/reject`, {
      method: 'POST',
      headers: { 'X-Admin-PIN': props.adminPin }
    })
    await Promise.all([
      fetchPendingUsers(),
      emit('refresh-users')
    ])
  } catch (err) {
    console.error('Failed to reject registration:', err)
    alert(err.data?.detail || 'Failed to reject registration.')
  } finally {
    actionInProgressId.value = null
  }
}
</script>

<template>
  <section class="space-y-6 animate-fadeIn">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-lg font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
          USER_DIRECTORY // SYSTEM_DIAGNOSTICS
        </h2>
        <p class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Hostel resident registry, search directory, cloud sync health diagnostics, and session security.
        </p>
      </div>

      <button 
        @click="emit('refresh-users')"
        class="px-4 py-2 border font-mono font-bold text-xs rounded-xl transition flex items-center gap-2 active:scale-95"
        :class="darkMode ? 'bg-[#121824] border-slate-800 text-slate-400 hover:text-white' : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 shadow-xs'"
      >
        <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': usersLoading }" />
        <span>Refresh User Directory</span>
      </button>
    </div>

    <!-- ========================================================================= -->
    <!-- 1. ORGANIZATION & HOSTEL IDENTITY CONFIGURATION (NEW)                     -->
    <!-- ========================================================================= -->
    <div
      :class="[
        'rounded-3xl p-6 border space-y-6 transition-all',
        darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'
      ]"
    >
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-sm">
            <School class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
              INSTITUTION_&_HOSTEL_BRANDING
            </h3>
            <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              Customize organization name/logo and hostel hall name/logo across all resident and admin interfaces.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Saved Toast feedback indicator -->
          <transition name="fade">
            <span
              v-if="showSavedFeedback"
              class="px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 flex items-center gap-1.5"
            >
              <Check class="w-3.5 h-3.5" /> Saved Live ✓
            </span>
          </transition>

          <button
            @click="handleResetDefaults"
            class="px-3.5 py-1.5 border font-mono font-bold text-xs rounded-xl transition flex items-center gap-1.5 active:scale-95"
            :class="darkMode ? 'border-white/10 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100'"
            title="Reset to default institution & hostel names"
          >
            <RotateCcw class="w-3 h-3" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      <!-- Two-Column Grid: Organization vs Hostel -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <!-- Column A: Organization / University -->
        <div class="space-y-4 p-5 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-50 border-slate-200/80'">
          <div class="flex items-center gap-2">
            <Building2 class="w-4 h-4 text-sky-500" />
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Organization / University
            </span>
          </div>

          <!-- Org Name -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Organization Name
            </label>
            <input
              v-model="institutionName"
              @input="triggerSavedNotice"
              type="text"
              placeholder="e.g. Stanford University or Apex Tech"
              class="w-full px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-sky-500 transition"
              :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
            />
          </div>

          <!-- Org Short Code -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Short Code / Acronym (for mobile headers)
            </label>
            <input
              v-model="institutionShort"
              @input="triggerSavedNotice"
              type="text"
              placeholder="e.g. AIT or STANFORD"
              class="w-full px-3.5 py-2 rounded-xl border text-xs font-mono uppercase focus:outline-none focus:border-sky-500 transition"
              :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
            />
          </div>

          <!-- Org Logo (URL or Upload) -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Organization Logo
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model="institutionLogo"
                @input="triggerSavedNotice"
                type="text"
                placeholder="Image URL (https://...)"
                class="flex-1 px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-sky-500 transition"
                :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
              />

              <!-- File Upload Trigger -->
              <label
                class="px-3 py-2 rounded-xl border text-xs font-mono font-bold cursor-pointer transition flex items-center gap-1.5 shrink-0"
                :class="darkMode ? 'bg-[#121824] border-white/10 hover:border-white/30 text-slate-300 hover:text-white' : 'bg-white border-slate-300 hover:bg-slate-100 text-slate-700'"
                title="Upload local logo image"
              >
                <Upload class="w-3.5 h-3.5 text-sky-500" />
                <span class="hidden sm:inline">Upload</span>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="handleOrgLogoUpload"
                />
              </label>

              <button
                v-if="institutionLogo"
                @click="clearOrgLogo"
                class="p-2 rounded-xl border text-rose-500 hover:bg-rose-500/10 transition shrink-0"
                :class="darkMode ? 'border-rose-500/30' : 'border-rose-200'"
                title="Remove logo"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Preview Org Logo if present -->
            <div v-if="institutionLogo" class="mt-2.5 flex items-center gap-2.5">
              <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Active Logo:</span>
              <img
                :src="institutionLogo"
                alt="Org Logo Preview"
                class="h-7 w-7 rounded-lg object-cover border border-slate-300 dark:border-slate-700"
              />
            </div>
          </div>
        </div>

        <!-- Column B: Hostel / Residence Hall -->
        <div class="space-y-4 p-5 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-50 border-slate-200/80'">
          <div class="flex items-center gap-2">
            <School class="w-4 h-4 text-emerald-500" />
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Hostel / Residence Hall
            </span>
          </div>

          <!-- Hostel Name -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Hostel / Hall Name
            </label>
            <input
              v-model="hostelName"
              @input="triggerSavedNotice"
              type="text"
              placeholder="e.g. Block B • Aryabhatta Hall"
              class="w-full px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-emerald-500 transition"
              :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
            />
          </div>

          <!-- Hub Floor / Location -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Hub Location / Floor
            </label>
            <input
              v-model="hubLocation"
              @input="triggerSavedNotice"
              type="text"
              placeholder="e.g. 2nd Floor Laundry Hub"
              class="w-full px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-emerald-500 transition"
              :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
            />
          </div>

          <!-- Hostel Crest / Logo (URL or Upload) -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Hostel Crest / Hall Logo
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model="hostelLogo"
                @input="triggerSavedNotice"
                type="text"
                placeholder="Image URL (https://...)"
                class="flex-1 px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-emerald-500 transition"
                :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
              />

              <!-- File Upload Trigger -->
              <label
                class="px-3 py-2 rounded-xl border text-xs font-mono font-bold cursor-pointer transition flex items-center gap-1.5 shrink-0"
                :class="darkMode ? 'bg-[#121824] border-white/10 hover:border-white/30 text-slate-300 hover:text-white' : 'bg-white border-slate-300 hover:bg-slate-100 text-slate-700'"
                title="Upload local hostel crest/logo"
              >
                <Upload class="w-3.5 h-3.5 text-emerald-500" />
                <span class="hidden sm:inline">Upload</span>
                <input
                  type="file"
                  accept="image/*"
                  class="hidden"
                  @change="handleHostelLogoUpload"
                />
              </label>

              <button
                v-if="hostelLogo"
                @click="clearHostelLogo"
                class="p-2 rounded-xl border text-rose-500 hover:bg-rose-500/10 transition shrink-0"
                :class="darkMode ? 'border-rose-500/30' : 'border-rose-200'"
                title="Remove hostel logo"
              >
                <Trash2 class="w-3.5 h-3.5" />
              </button>
            </div>

            <!-- Preview Hostel Logo if present -->
            <div v-if="hostelLogo" class="mt-2.5 flex items-center gap-2.5">
              <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Active Crest:</span>
              <img
                :src="hostelLogo"
                alt="Hostel Logo Preview"
                class="h-7 w-7 rounded-lg object-cover border border-slate-300 dark:border-slate-700"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Live Identity Preview Card -->
      <div class="pt-4 border-t" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-2 mb-3">
          <Sparkles class="w-4 h-4 text-amber-500" />
          <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
            Live System Header Preview
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Light Theme Preview -->
          <div class="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs space-y-2">
            <span class="text-[10px] font-mono text-slate-400 uppercase font-bold block">Light Mode Header</span>
            <div class="p-2.5 bg-[#f6f8fa] rounded-xl border border-slate-200/80">
              <AppBranding :dark-mode="false" logo-mode="icon" />
            </div>
          </div>

          <!-- Dark Theme Preview -->
          <div class="p-4 rounded-2xl bg-[#0c0e14] border border-slate-800 shadow-2xs space-y-2">
            <span class="text-[10px] font-mono text-slate-500 uppercase font-bold block">Dark Mode Header</span>
            <div class="p-2.5 bg-[#10131a] rounded-xl border border-slate-800">
              <AppBranding :dark-mode="true" logo-mode="icon" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- 2. TIMEZONE & REGIONAL CLOCK SETTINGS (NEW)                               -->
    <!-- ========================================================================= -->
    <div
      :class="[
        'rounded-3xl p-6 border space-y-6 transition-all',
        darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'
      ]"
    >
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-rose-600 flex items-center justify-center text-white shadow-sm">
            <Globe class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
              TIMEZONE_&_REGIONAL_CLOCK_SETTINGS
            </h3>
            <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              Default standard is <strong class="text-amber-500">IST (Asia/Kolkata • UTC+05:30)</strong>. All telemetry readings, booking starts, and queue times auto-convert to this timezone.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Saved indicator -->
          <transition name="fade">
            <span
              v-if="showTimezoneSavedFeedback"
              class="px-3 py-1 rounded-full text-[11px] font-mono font-bold bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 flex items-center gap-1.5"
            >
              <Check class="w-3.5 h-3.5" /> Timezone Updated ✓
            </span>
          </transition>

          <button
            @click="handleResetTimezone"
            class="px-3.5 py-1.5 border font-mono font-bold text-xs rounded-xl transition flex items-center gap-1.5 active:scale-95"
            :class="darkMode ? 'border-white/10 text-slate-400 hover:text-white hover:bg-slate-800' : 'border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100'"
            title="Reset to default IST (Asia/Kolkata)"
          >
            <RotateCcw class="w-3 h-3" />
            <span>Reset to IST</span>
          </button>
        </div>
      </div>

      <!-- Controls Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Preset Dropdown (col-span-7) -->
        <div class="lg:col-span-7 space-y-4 p-5 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-50 border-slate-200/80'">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Clock class="w-4 h-4 text-amber-500" />
              <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                Active Timezone Selection
              </span>
            </div>
            <!-- Active offset pill -->
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-500 border border-amber-500/30">
              {{ getTimezoneAbbr() }} • {{ getTimezoneOffsetStr() }}
            </span>
          </div>

          <!-- Timezone Preset Dropdown -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Select Preset Region (Default: IST)
            </label>
            <select
              :value="selectedTimezone"
              @change="handlePresetChange"
              class="w-full px-3.5 py-2.5 rounded-xl border text-xs font-mono focus:outline-none focus:border-amber-500 transition cursor-pointer"
              :class="darkMode ? 'bg-[#121824] border-white/10 text-white' : 'bg-white border-slate-300 text-slate-900'"
            >
              <option v-for="preset in availablePresets" :key="preset.value" :value="preset.value">
                {{ preset.label }}
              </option>
            </select>
          </div>

          <!-- Custom IANA Timezone Input -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Or Enter Custom IANA Timezone Identifier
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model="customTimezoneInput"
                type="text"
                placeholder="e.g. America/Toronto, Asia/Kathmandu, Pacific/Auckland"
                @keyup.enter="handleApplyCustomTimezone"
                class="flex-1 px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-amber-500 transition"
                :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
              />
              <button
                @click="handleApplyCustomTimezone"
                class="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 hover:bg-amber-400 font-mono font-bold text-xs transition active:scale-95 shrink-0"
              >
                Apply
              </button>
            </div>
            <p v-if="customTzError" class="text-[11px] font-mono text-rose-500 mt-1 flex items-center gap-1">
              <AlertCircle class="w-3 h-3 shrink-0" /> {{ customTzError }}
            </p>
          </div>

          <!-- 12h / 24h Clock Format Switch -->
          <div class="flex items-center justify-between pt-2 border-t" :class="darkMode ? 'border-white/5' : 'border-slate-200/60'">
            <div>
              <span class="text-xs font-mono font-bold block" :class="darkMode ? 'text-slate-200' : 'text-slate-800'">
                Clock Display Format
              </span>
              <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
                Choose 12-hour (AM/PM) or 24-hour military clock
              </span>
            </div>
            <div class="flex items-center gap-1 p-1 rounded-xl border" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200'">
              <button
                @click="handleToggle24Hour(false)"
                class="px-3 py-1 text-xs font-mono font-bold rounded-lg transition"
                :class="!is24Hour ? (darkMode ? 'bg-amber-500 text-slate-950' : 'bg-slate-900 text-white shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')"
              >
                12-Hour
              </button>
              <button
                @click="handleToggle24Hour(true)"
                class="px-3 py-1 text-xs font-mono font-bold rounded-lg transition"
                :class="is24Hour ? (darkMode ? 'bg-amber-500 text-slate-950' : 'bg-slate-900 text-white shadow-xs') : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')"
              >
                24-Hour
              </button>
            </div>
          </div>
        </div>

        <!-- Live Regional Clock Preview (col-span-5) -->
        <div class="lg:col-span-5 p-5 rounded-2xl border flex flex-col justify-between" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-gradient-to-br from-amber-500/5 via-slate-50 to-slate-50 border-slate-200/80'">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                Live Regional Clock Preview
              </span>
            </div>

            <!-- Big Live Time Display -->
            <div class="my-4">
              <div class="text-3xl sm:text-4xl font-black font-mono tracking-tight text-slate-900 dark:text-white tabular-nums">
                {{ liveClockTime }}
              </div>
              <div class="text-xs font-mono font-bold text-slate-500 dark:text-slate-400 mt-1">
                {{ liveClockDate }}
              </div>
            </div>
          </div>

          <!-- Timezone Details Summary -->
          <div class="space-y-2 pt-4 border-t" :class="darkMode ? 'border-white/10' : 'border-slate-200/80'">
            <div class="flex justify-between text-xs font-mono">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Active IANA Zone:</span>
              <span class="font-bold text-amber-500 truncate max-w-[180px]">{{ selectedTimezone }}</span>
            </div>
            <div class="flex justify-between text-xs font-mono">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">UTC Offset:</span>
              <span class="font-bold" :class="darkMode ? 'text-slate-200' : 'text-slate-700'">{{ getTimezoneOffsetStr() }}</span>
            </div>
            <div class="flex justify-between text-xs font-mono">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Applies To:</span>
              <span class="font-bold text-emerald-500">All Cloud & Local Events</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- 3. RESIDENT ONBOARDING QR STATION (1-MINUTE ROTATING KIOSK)               -->
    <!-- ========================================================================= -->
    <div
      :class="[
        'rounded-3xl p-6 border space-y-6 transition-all',
        darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'
      ]"
    >
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-sm">
            <QrCode class="w-5 h-5" />
          </div>
          <div>
            <h3 class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
              RESIDENT_ONBOARDING_QR_STATION
            </h3>
            <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              Physical laundry room registration kiosk. Rotates every 60 seconds to restrict onboarding strictly to in-person residents.
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Launch Fullscreen Kiosk Mode -->
          <button
            @click="isKioskOpen = true"
            class="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-indigo-600 text-white font-mono font-bold text-xs shadow-sm hover:scale-[1.02] active:scale-95 transition flex items-center gap-1.5 cursor-pointer"
          >
            <Maximize2 class="w-3.5 h-3.5" />
            <span>Launch Kiosk Mode</span>
          </button>
        </div>
      </div>

      <!-- Station Body: 2 Columns (Controls + Live Preview) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        <!-- Col 1: Config & Rotation Ticker (col-span-7) -->
        <div class="lg:col-span-7 space-y-4 p-5 rounded-2xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-50 border-slate-200/80'">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Hostel Registration Station
            </span>
            <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-400 border border-sky-500/30">
              Assigned Hall: {{ hostelName }}
            </span>
          </div>

          <!-- Base URL input -->
          <div>
            <label class="text-[11px] font-mono font-bold block mb-1.5" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">
              Hostel Web Domain / Network Base URL
            </label>
            <div class="flex items-center gap-2">
              <input
                v-model="customBaseUrl"
                @change="fetchOnboardingQr"
                type="text"
                :placeholder="qrData?.lan_ip ? `http://${qrData.lan_ip}:3000 (or https://washqueue.mastersunion.org)` : 'e.g. https://washqueue.mastersunion.org'"
                class="flex-1 px-3.5 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-sky-500 transition"
                :class="darkMode ? 'bg-[#121824] border-white/10 text-white placeholder-zinc-600' : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'"
              />
              <button
                @click="fetchOnboardingQr"
                class="px-3.5 py-2 rounded-xl border font-mono font-bold text-xs transition active:scale-95 shrink-0"
                :class="darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100'"
              >
                Update
              </button>
            </div>
            <p class="text-[10px] font-mono text-slate-400 dark:text-slate-500 mt-1">
              Ensure this URL is reachable from student smartphones connected to campus/room Wi-Fi or mobile data.
            </p>
          </div>

          <!-- Live Rotation Ticker -->
          <div class="p-3.5 rounded-xl border space-y-2" :class="darkMode ? 'bg-[#121824] border-white/5' : 'bg-white border-slate-200'">
            <div class="flex items-center justify-between text-xs font-mono">
              <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Cryptographic Token Rotation:</span>
              <span class="text-amber-500 font-bold tabular-nums">{{ qrSecondsRemaining }}s until refresh</span>
            </div>
            <div class="w-full bg-slate-200 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div
                class="bg-gradient-to-r from-sky-500 via-amber-500 to-rose-500 h-full rounded-full transition-all duration-1000 ease-linear"
                :style="{ width: `${(qrSecondsRemaining / 60) * 100}%` }"
              />
            </div>
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-400 dark:text-slate-500">
              <span>Rotation: 60 Seconds</span>
              <span>Student Grace Window: 5 Minutes</span>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center gap-2 pt-1">
            <button
              @click="fetchOnboardingQr"
              :disabled="qrLoading"
              class="px-3 py-1.5 rounded-xl border text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95 cursor-pointer"
              :class="darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100'"
            >
              <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': qrLoading }" />
              <span>Rotate Token Now</span>
            </button>

            <button
              @click="copyQrUrl"
              class="px-3 py-1.5 rounded-xl border text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95 cursor-pointer"
              :class="qrCopied ? 'bg-emerald-500 text-white border-emerald-600' : (darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100')"
            >
              <Check v-if="qrCopied" class="w-3.5 h-3.5" />
              <Copy v-else class="w-3.5 h-3.5" />
              <span>{{ qrCopied ? 'Copied Link!' : 'Copy Active Link' }}</span>
            </button>
          </div>
        </div>

        <!-- Col 2: Live QR Preview Box (col-span-5) -->
        <div class="lg:col-span-5 p-5 rounded-2xl border flex flex-col items-center justify-center text-center" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-50 border-slate-200/80'">
          <div 
            v-if="qrSvgPreview"
            v-html="qrSvgPreview" 
            class="w-44 h-44 sm:w-48 sm:h-48 flex items-center justify-center [&>svg]:w-full [&>svg]:h-full p-2 bg-white rounded-2xl border border-slate-200 shadow-sm"
          />
          <div v-else class="w-44 h-44 flex items-center justify-center">
            <RefreshCw class="w-6 h-6 animate-spin text-slate-400" />
          </div>

          <p class="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-3">
            {{ hostelName }}
          </p>
          <p class="text-[10px] font-mono text-slate-500 dark:text-slate-400 mt-0.5">
            Auto-rotates in <strong class="text-amber-500 font-bold">{{ qrSecondsRemaining }}s</strong>
          </p>
        </div>
      </div>
    </div>

    <!-- Full-Screen Kiosk Mode Modal -->
    <AdminQrKioskModal
      :is-open="isKioskOpen"
      :qr-url="qrData?.default_url"
      :seconds-remaining="qrSecondsRemaining"
      :dark-mode="darkMode"
      @close="isKioskOpen = false"
      @refresh-now="fetchOnboardingQr"
    />

    <!-- ========================================================================= -->
    <!-- 4. PENDING REGISTRATION APPROVALS QUEUE                                    -->
    <!-- ========================================================================= -->
    <div
      class="rounded-3xl p-5 border space-y-4 transition-all"
      :class="[
        pendingUsers.length > 0
          ? (darkMode ? 'bg-amber-950/20 border-amber-500/40 shadow-lg shadow-amber-950/20' : 'bg-amber-50/70 border-amber-300 shadow-sm')
          : (darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs')
      ]"
    >
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-2.5">
          <div
            class="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-bold transition-colors"
            :class="pendingUsers.length > 0 ? 'bg-amber-500 text-white shadow-xs' : (darkMode ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500')"
          >
            <Clock class="w-4 h-4" :class="{ 'animate-pulse': pendingUsers.length > 0 }" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
                PENDING_REGISTRATION_REQUESTS
              </h3>
              <span
                class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold"
                :class="pendingUsers.length > 0 ? 'bg-amber-500 text-white animate-pulse' : (darkMode ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500')"
              >
                {{ pendingUsers.length }} Awaiting Approval
              </span>
            </div>
            <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              New hostel residents who scanned the desk QR code and are awaiting operator authorization.
            </p>
          </div>
        </div>

        <button
          @click="fetchPendingUsers"
          :disabled="pendingLoading"
          class="px-3 py-1.5 border font-mono font-bold text-xs rounded-xl transition flex items-center gap-1.5 active:scale-95 cursor-pointer shrink-0 self-start sm:self-auto"
          :class="darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100'"
        >
          <RefreshCw class="w-3 h-3" :class="{ 'animate-spin': pendingLoading }" />
          <span>Refresh Requests</span>
        </button>
      </div>

      <!-- Pending List Content -->
      <div v-if="pendingUsers.length === 0" class="py-5 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        <p class="font-medium">No pending registration requests at this time.</p>
        <p class="text-[10px] text-slate-500 dark:text-slate-600 mt-1">When students scan the laundry desk QR code, their room requests appear here for approval.</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        <div
          v-for="user in pendingUsers"
          :key="user.id"
          class="p-4 rounded-2xl border transition-all flex flex-col justify-between gap-3"
          :class="darkMode ? 'bg-[#0c1017] border-amber-500/30' : 'bg-white border-amber-200 shadow-xs'"
        >
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-sm" :class="darkMode ? 'text-white' : 'text-slate-900'">{{ user.name }}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-sky-500/15 text-sky-500 border border-sky-500/30">
                  Room {{ user.room_number }}
                </span>
              </div>
              <div class="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-1.5 space-y-0.5">
                <p v-if="user.phone" class="flex items-center gap-1.5">
                  <span>📱 Mobile:</span>
                  <strong class="text-slate-700 dark:text-slate-200">{{ user.phone }}</strong>
                </p>
                <p class="flex items-center gap-1.5">
                  <span>🏢 Hall:</span>
                  <span>{{ user.hostel || hostelName }}</span>
                </p>
                <p class="text-[10px] text-slate-400">
                  Requested: {{ formatDateTime(user.created_at) }}
                </p>
              </div>
            </div>

            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-500 border border-amber-500/30 shrink-0">
              Pending
            </span>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center justify-end gap-2 pt-2 border-t" :class="darkMode ? 'border-white/5' : 'border-slate-100'">
            <button
              @click="rejectUser(user)"
              :disabled="actionInProgressId === user.id"
              class="px-3 py-1.5 rounded-xl border text-xs font-mono font-bold transition flex items-center gap-1.5 text-rose-500 hover:bg-rose-500/10 cursor-pointer disabled:opacity-50"
              :class="darkMode ? 'border-rose-500/30' : 'border-rose-200'"
            >
              ✕ Reject
            </button>
            <button
              @click="approveUser(user)"
              :disabled="actionInProgressId === user.id"
              class="px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold transition flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs cursor-pointer disabled:opacity-50"
            >
              <RefreshCw v-if="actionInProgressId === user.id" class="w-3 h-3 animate-spin" />
              <Check v-else class="w-3 h-3" />
              <span>{{ actionInProgressId === user.id ? 'Approving...' : 'Approve Resident' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Student Users Registry Table with Live Search Filter -->
    <div class="rounded-3xl p-5 border space-y-4" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div>
          <span class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
            Registered Student Accounts ({{ users.length }})
          </span>
          <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Auto-synced from SQLite / PostgreSQL</p>
        </div>

        <!-- Real-time Search Input -->
        <div class="relative w-full sm:w-80">
          <Search class="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" :class="darkMode ? 'text-slate-500' : 'text-slate-400'" />
          <input
            v-model="userSearchQuery"
            type="text"
            placeholder="Search name, room (e.g. B-214)..."
            class="w-full pl-10 pr-9 py-2 rounded-xl border text-xs font-mono focus:outline-none focus:border-[#10b981] transition"
            :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white placeholder-zinc-600' : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400'"
          />
          <button
            v-if="userSearchQuery"
            @click="userSearchQuery = ''"
            class="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-slate-400 hover:text-slate-600 dark:hover:text-white"
          >
            ✕
          </button>
        </div>
      </div>

      <div class="flex items-center justify-between text-xs font-mono px-1" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        <span>Showing {{ filteredUsers.length }} of {{ users.length }} registered residents</span>
        <span v-if="userSearchQuery" class="text-emerald-500 font-bold">Filtered active</span>
      </div>

      <div class="overflow-x-auto rounded-2xl border" :class="darkMode ? 'border-white/10 bg-[#0a0e17]' : 'border-slate-200 bg-slate-50'">
        <table class="w-full text-left font-mono text-xs">
          <thead class="uppercase text-[10px] border-b" :class="darkMode ? 'bg-[#121824] text-slate-400 border-white/10' : 'bg-slate-100 text-slate-600 border-slate-200'">
            <tr>
              <th class="px-4 py-3">Resident Name</th>
              <th class="px-4 py-3">Campus & Hostel</th>
              <th class="px-4 py-3">Hostel Room</th>
              <th class="px-4 py-3">Email Address</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3">System Role</th>
              <th class="px-4 py-3 text-right">User ID</th>
            </tr>
          </thead>
          <tbody class="divide-y" :class="darkMode ? 'divide-white/5 text-zinc-300' : 'divide-slate-200 text-slate-700'">
            <tr v-for="user in filteredUsers" :key="user.id" class="hover:bg-white/[0.02] transition">
              <td class="px-4 py-3 font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
                {{ user.name }}
              </td>
              <td class="px-4 py-3">
                <div class="space-y-0.5">
                  <div class="font-bold text-xs" :class="darkMode ? 'text-slate-200' : 'text-slate-800'">
                    {{ user.hostel || '—' }}
                  </div>
                  <div class="text-[10px] text-slate-400 truncate max-w-[200px]" :title="user.university || '—'">
                    {{ user.university || '—' }}
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-sky-500 font-bold">
                <div class="flex items-center gap-1.5">
                  <span>{{ user.room_number ? `Room ${user.room_number}` : '—' }}</span>
                  <span 
                    v-if="users.filter(u => u.room_number && u.room_number === user.room_number).length > 1"
                    class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                    title="Double / Shared Room"
                  >
                    Shared
                  </span>
                </div>
              </td>
              <td class="px-4 py-3" :class="darkMode ? 'text-slate-400' : 'text-slate-600'">
                {{ user.email }}
              </td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border"
                  :class="user.status === 'pending' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : (user.status === 'rejected' ? 'bg-rose-500/20 text-rose-400 border-rose-500/30' : 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30')"
                >
                  {{ user.status || 'approved' }}
                </span>
              </td>
              <td class="px-4 py-3">
                <span 
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border"
                  :class="user.role === 'admin' ? 'bg-purple-500/20 text-purple-400 border-purple-500/30' : 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30'"
                >
                  {{ user.role || 'student' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right text-[10px] font-mono" :class="darkMode ? 'text-slate-500' : 'text-slate-400'">
                {{ user.id.slice(0, 8) }}...
              </td>
            </tr>
            <tr v-if="filteredUsers.length === 0">
              <td colspan="6" class="py-8 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
                No residents matching search query "{{ userSearchQuery }}".
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- System & Network Diagnostics Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <!-- WebSocket Health Card -->
      <div class="rounded-3xl p-5 border space-y-2" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
        <span class="text-xs font-mono font-bold uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">WebSocket Status</span>
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full" :class="isWsConnected ? 'bg-emerald-500' : 'bg-rose-500'"></span>
          <span class="font-mono font-bold text-sm" :class="darkMode ? 'text-white' : 'text-slate-900'">
            {{ isWsConnected ? 'Active (<10ms Push)' : 'Disconnected (Using 1s Poll)' }}
          </span>
        </div>
        <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Persistent socket broadcasts state changes directly to browsers with zero request lag.
        </p>
      </div>

      <!-- Cloud Sync Health Card -->
      <div class="rounded-3xl p-5 border space-y-2" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
        <span class="text-xs font-mono font-bold uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Cloud Sync & Buffer</span>
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
          <span class="font-mono font-bold text-sm" :class="darkMode ? 'text-white' : 'text-slate-900'">
            Supabase Sync Ready
          </span>
        </div>
        <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Offline buffer replays state changes automatically if hostel Wi-Fi connection drops.
        </p>
      </div>

      <!-- Session Lock Card -->
      <div class="rounded-3xl p-5 border space-y-2 flex flex-col justify-between" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
        <div>
          <span class="text-xs font-mono font-bold uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Operator Session</span>
          <span class="font-mono font-bold text-sm text-emerald-500 block">Authenticated</span>
          <p class="text-[11px] font-mono mt-1" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            PIN is stored in temporary session storage. Click below to lock this terminal immediately.
          </p>
        </div>
        <button 
          @click="emit('lock-session')"
          class="w-full py-2 bg-rose-500/10 border border-rose-500/30 text-rose-500 hover:bg-rose-500/20 text-xs font-mono font-bold rounded-xl transition active:scale-95 flex items-center justify-center gap-1.5 mt-3"
        >
          <Lock class="w-3.5 h-3.5" />
          <span>Lock Admin Session</span>
        </button>
      </div>
    </div>
  </section>
</template>
