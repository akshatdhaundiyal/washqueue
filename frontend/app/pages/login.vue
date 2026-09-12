<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  Waves,
  Shield,
  User,
  KeyRound,
  Lock,
  ArrowRight,
  Sun,
  Moon,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Building2,
  QrCode,
  Clock,
  Phone,
  ShieldCheck,
  Sparkles,
  RefreshCw
} from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'
import AppBranding from '~/components/common/AppBranding.vue'

const { institutionName, hostelName } = useHostelBranding()
const config = useRuntimeConfig()
const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'
const route = useRoute()

// Persistent Theme Synchronization
const { isDark: darkMode, toggleTheme, setTheme } = useAppTheme()

// Mode: 'student' | 'admin'
const loginRole = ref('student')

// Student Auth State
const studentMode = ref('login') // 'login' | 'register'
const studentRoom = ref('')
const studentPassword = ref('')
const studentName = ref('')
const studentPhone = ref('')
const showPassword = ref(false)

// QR Onboarding Token Verification State
const registrationToken = ref('')
const verifiedHostel = ref('')
const isVerifyingToken = ref(false)
const isTokenValid = ref(false)
const isTokenExpired = ref(false)
const tokenError = ref('')
const remainingSeconds = ref(0)
let timerInterval = null

// Registration Request Approval State
const isRegistrationSubmitted = ref(false)
const registrationSubmittedData = ref(null)

// Admin Auth State
const adminPin = ref('')
const showAdminPin = ref(false)

// UI Feedback State
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const clearFeedback = () => {
  errorMessage.value = ''
  successMessage.value = ''
}

const studentRole = () => {
  loginRole.value = 'student'
  clearFeedback()
}

// Format Remaining Grace Time MM:SS
const formattedTimeRemaining = computed(() => {
  const m = Math.floor(remainingSeconds.value / 60)
  const s = remainingSeconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

const startGraceTimer = (seconds) => {
  if (timerInterval) clearInterval(timerInterval)
  remainingSeconds.value = seconds
  timerInterval = setInterval(() => {
    if (remainingSeconds.value > 0) {
      remainingSeconds.value--
    } else {
      clearInterval(timerInterval)
      isTokenExpired.value = true
      isTokenValid.value = false
      tokenError.value = 'Your registration session has expired. Please scan the current live QR code on the laundry desk.'
    }
  }, 1000)
}

// Verify incoming QR token from URL query params
const verifyTokenFromUrl = async () => {
  const token = (route.query.token || route.query.registration_token || route.query.t)?.toString()
  const mode = route.query.mode?.toString()

  if (mode === 'register' || token) {
    studentMode.value = 'register'
  }

  if (token) {
    registrationToken.value = token
    isVerifyingToken.value = true
    tokenError.value = ''
    try {
      const res = await $fetch(`${apiBase}/api/admin/onboarding-qr/verify`, {
        method: 'POST',
        body: { token }
      })

      if (res.status === 'valid') {
        isTokenValid.value = true
        isTokenExpired.value = false
        verifiedHostel.value = res.hostel_id || route.query.hostel?.toString() || hostelName.value
        startGraceTimer(res.remaining_seconds || 300)
      } else {
        isTokenValid.value = false
        tokenError.value = res.message || 'Scanned QR code is invalid or has expired.'
      }
    } catch (err) {
      isTokenValid.value = false
      tokenError.value = err.data?.detail || err.message || 'QR code verification failed. Please scan the live desk screen.'
    } finally {
      isVerifyingToken.value = false
    }
  }
}

onMounted(() => {
  verifyTokenFromUrl()
})

onUnmounted(() => {
  if (timerInterval) clearInterval(timerInterval)
})

watch(() => route.query, () => {
  verifyTokenFromUrl()
})

// Student Form Submission (Login / Register)
const handleStudentSubmit = async () => {
  clearFeedback()
  isLoading.value = true

  try {
    if (studentMode.value === 'login') {
      const payload = {
        room_number: studentRoom.value.trim().toUpperCase(),
        password: studentPassword.value,
        name: studentName.value.trim() || undefined
      }

      const res = await $fetch(`${apiBase}/api/auth/login`, {
        method: 'POST',
        body: payload
      })

      if (typeof window !== 'undefined') {
        localStorage.setItem('washqueue_student_user', JSON.stringify(res))
      }

      successMessage.value = `Welcome back, ${res.name || 'Resident'}! Redirecting to laundry hub...`
      setTimeout(() => {
        navigateTo('/')
      }, 700)
    } else {
      // Register Mode: Strict physical QR check
      if (!isTokenValid.value || !registrationToken.value) {
        errorMessage.value = 'A valid physical hostel QR code scan is required to register.'
        isLoading.value = false
        return
      }

      const payload = {
        name: studentName.value.trim(),
        room_number: studentRoom.value.trim().toUpperCase(),
        password: studentPassword.value,
        phone: studentPhone.value.trim() || undefined,
        registration_token: registrationToken.value,
        hostel: verifiedHostel.value || hostelName.value,
        university: institutionName.value
      }

      const res = await $fetch(`${apiBase}/api/auth/register`, {
        method: 'POST',
        body: payload
      })

      if (res.status === 'pending') {
        registrationSubmittedData.value = res
        isRegistrationSubmitted.value = true
        successMessage.value = `Registration request submitted for Room ${res.room_number}! Pending administrator review.`
      } else {
        if (typeof window !== 'undefined') {
          localStorage.setItem('washqueue_student_user', JSON.stringify(res))
        }
        successMessage.value = `Account registered for Room ${res.room_number}! Redirecting to hub...`
        setTimeout(() => {
          navigateTo('/')
        }, 800)
      }
    }
  } catch (err) {
    errorMessage.value = err.data?.detail || err.message || 'Authentication failed. Please check your credentials.'
  } finally {
    isLoading.value = false
  }
}

// Admin PIN Verification
const handleAdminSubmit = async () => {
  clearFeedback()
  isLoading.value = true

  const pin = adminPin.value.trim()
  if (!pin) {
    errorMessage.value = 'Please enter the Operator Security PIN.'
    isLoading.value = false
    return
  }

  try {
    const res = await $fetch(`${apiBase}/api/admin/verify-pin`, {
      method: 'POST',
      body: { pin }
    })

    if (res.valid) {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('admin_pin', pin)
      }
      successMessage.value = 'PIN verified! Opening Operator Console...'
      setTimeout(() => {
        navigateTo('/admin')
      }, 600)
    }
  } catch (err) {
    errorMessage.value = err.data?.detail || 'Invalid Admin PIN. Please try again.'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div
    :class="[
      'min-h-screen flex flex-col justify-between font-sans antialiased transition-colors duration-200',
      darkMode ? 'bg-[#0c0e14] text-slate-100' : 'bg-[#f6f8fa] text-slate-900'
    ]"
  >
    <!-- TOP NAVIGATION HEADER -->
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

      <div class="flex items-center gap-2">
        <!-- Guest Quick Link -->
        <NuxtLink
          to="/"
          :class="[
            'hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all',
            darkMode
              ? 'text-slate-400 hover:text-white hover:bg-slate-800/80'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          ]"
        >
          <span>Continue as Guest</span>
          <ArrowRight class="w-3 h-3" />
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

    <!-- MAIN LOGIN / REGISTER CARD -->
    <main class="flex-1 flex items-center justify-center p-4 sm:p-6 my-4">
      <div
        :class="[
          'w-full max-w-md rounded-[32px] border p-6 sm:p-8 transition-all shadow-xl',
          darkMode ? 'bg-[#151921] border-slate-800 shadow-black/40' : 'bg-white border-slate-200/80 shadow-[0_4px_25px_rgba(0,0,0,0.04)]'
        ]"
      >
        <!-- Card Header with Logo + Org & Hostel Identity -->
        <div class="text-center mb-6">
          <div class="flex justify-center mb-3">
            <AppLogo mode="icon" :dark-mode="darkMode" size-class="h-14 w-14" />
          </div>
          <h2 class="text-xl sm:text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            WashQueue Access
          </h2>
          <div class="flex items-center justify-center gap-1.5 mt-1 text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span class="font-bold text-slate-700 dark:text-slate-200">{{ institutionName }}</span>
            <span>•</span>
            <span class="text-sky-600 dark:text-sky-400 font-bold">{{ hostelName }}</span>
          </div>
          <p class="text-xs text-slate-400 dark:text-slate-500 mt-1.5">
            {{ loginRole === 'student' ? 'Sign in to reserve washers & track laundry in real-time' : 'Hostel Operator & Admin telemetry management console' }}
          </p>
        </div>

        <!-- ROLE SWITCHER TABS -->
        <div
          :class="[
            'grid grid-cols-2 p-1 rounded-2xl border mb-6 transition-colors',
            darkMode ? 'bg-[#10131a] border-slate-800' : 'bg-slate-100/90 border-slate-200/80'
          ]"
        >
          <button
            @click="studentRole"
            :class="[
              'py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2',
              loginRole === 'student'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            ]"
          >
            <User class="w-3.5 h-3.5" />
            <span>Resident Student</span>
          </button>

          <button
            @click="loginRole = 'admin'; clearFeedback()"
            :class="[
              'py-2.5 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2',
              loginRole === 'admin'
                ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            ]"
          >
            <Shield class="w-3.5 h-3.5" />
            <span>Hostel Admin</span>
          </button>
        </div>

        <!-- ALERT FEEDBACK -->
        <div
          v-if="errorMessage"
          class="mb-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2"
        >
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>

        <div
          v-if="successMessage"
          class="mb-4 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 text-emerald-700 dark:text-emerald-300 text-xs flex items-center gap-2"
        >
          <CheckCircle2 class="w-4 h-4 shrink-0" />
          <span>{{ successMessage }}</span>
        </div>

        <!-- =================================================================== -->
        <!-- TAB 1: RESIDENT STUDENT AUTH                                       -->
        <!-- =================================================================== -->
        <div v-if="loginRole === 'student'" class="space-y-4">
          <!-- Sign In vs Register sub-toggle -->
          <div class="flex items-center justify-center gap-6 text-xs font-semibold pb-2 border-b border-slate-100 dark:border-slate-800">
            <button
              @click="studentMode = 'login'; clearFeedback()"
              :class="studentMode === 'login' ? 'text-sky-600 dark:text-sky-400 font-bold border-b-2 border-sky-600 pb-1 -mb-2.5' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
            >
              Resident Sign In
            </button>
            <button
              @click="studentMode = 'register'; clearFeedback()"
              :class="studentMode === 'register' ? 'text-sky-600 dark:text-sky-400 font-bold border-b-2 border-sky-600 pb-1 -mb-2.5' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
            >
              New Resident Sign Up
            </button>
          </div>

          <!-- SUB-VIEW A: RESIDENT LOGIN -->
          <div v-if="studentMode === 'login'">
            <form @submit.prevent="handleStudentSubmit" class="space-y-3.5 pt-1">
              <!-- Room Number -->
              <div>
                <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                  Room Number
                </label>
                <input
                  v-model="studentRoom"
                  type="text"
                  required
                  placeholder="e.g. 214 or B-214"
                  :class="[
                    'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium uppercase transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                    darkMode
                      ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                      : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                  ]"
                />
              </div>

              <!-- Full Name (Optional for double-sharing rooms) -->
              <div>
                <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                  Resident Name <span class="font-normal text-slate-400">(Optional for single rooms)</span>
                </label>
                <input
                  v-model="studentName"
                  type="text"
                  placeholder="e.g. Akshat Dhaundiyal"
                  :class="[
                    'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                    darkMode
                      ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                      : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                  ]"
                />
              </div>

              <!-- Password -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block">
                    Password
                  </label>
                </div>
                <div class="relative">
                  <input
                    v-model="studentPassword"
                    :type="showPassword ? 'text' : 'password'"
                    required
                    placeholder="••••••••"
                    :class="[
                      'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20 pr-10',
                      darkMode
                        ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                        : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                    ]"
                  />
                  <button
                    type="button"
                    @click="showPassword = !showPassword"
                    class="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <EyeOff v-if="showPassword" class="w-4 h-4" />
                    <Eye v-else class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Submit Button -->
              <button
                type="submit"
                :disabled="isLoading"
                class="w-full mt-2 py-3 rounded-xl text-xs font-bold transition-all bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>{{ isLoading ? 'Authenticating...' : 'Sign In as Resident' }}</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </button>
            </form>

            <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-center">
              <p class="text-[11px] text-slate-500 dark:text-slate-400">
                New resident without an account?
                <button
                  type="button"
                  @click="studentMode = 'register'; clearFeedback()"
                  class="text-sky-600 dark:text-sky-400 font-bold hover:underline ml-1 inline-flex items-center gap-1"
                >
                  <QrCode class="w-3 h-3" />
                  <span>Scan Desk QR to Register</span>
                </button>
              </p>
            </div>
          </div>

          <!-- SUB-VIEW B: REGISTRATION SUBMITTED PENDING APPROVAL -->
          <div v-else-if="studentMode === 'register' && isRegistrationSubmitted" class="space-y-4 pt-1">
            <div
              :class="[
                'p-5 rounded-2xl border text-center transition-all',
                darkMode ? 'bg-[#10131a] border-slate-800' : 'bg-slate-50/90 border-slate-200'
              ]"
            >
              <div class="relative w-14 h-14 mx-auto mb-3 flex items-center justify-center rounded-2xl bg-amber-500/10 dark:bg-amber-400/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                <Clock class="w-7 h-7 animate-pulse" />
                <span class="absolute -top-1 -right-1 flex h-3 w-3">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                </span>
              </div>

              <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-300/60 dark:border-amber-700/60 mb-2">
                <span>Pending Administrator Approval</span>
              </div>

              <h3 class="text-base font-bold text-slate-900 dark:text-white">
                Registration Request Sent!
              </h3>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs mx-auto leading-relaxed">
                Your room registration has been submitted to the hostel administrator for review.
              </p>

              <!-- Resident Request Summary Card -->
              <div class="mt-4 p-3.5 rounded-xl text-left text-xs space-y-2 bg-white/70 dark:bg-slate-800/60 border border-slate-200/70 dark:border-slate-700/70">
                <div class="flex items-center justify-between">
                  <span class="text-slate-400 font-medium">Resident:</span>
                  <span class="font-bold text-slate-800 dark:text-slate-100">{{ registrationSubmittedData?.name }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-slate-400 font-medium">Room Number:</span>
                  <span class="font-bold font-mono text-sky-600 dark:text-sky-400">{{ registrationSubmittedData?.room_number }}</span>
                </div>
                <div v-if="registrationSubmittedData?.phone" class="flex items-center justify-between">
                  <span class="text-slate-400 font-medium">Mobile:</span>
                  <span class="font-medium text-slate-700 dark:text-slate-200">{{ registrationSubmittedData?.phone }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-slate-400 font-medium">Assigned Hostel:</span>
                  <span class="font-semibold text-slate-700 dark:text-slate-300">{{ registrationSubmittedData?.hostel || verifiedHostel || hostelName }}</span>
                </div>
              </div>

              <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-3 leading-relaxed">
                Once the administrator approves your room request, you will be able to sign in immediately using your password.
              </p>

              <!-- Return to Login Button -->
              <button
                type="button"
                @click="studentMode = 'login'; studentRoom = registrationSubmittedData?.room_number || ''; isRegistrationSubmitted = false; clearFeedback()"
                class="w-full mt-4 py-2.5 px-4 rounded-xl text-xs font-bold transition-all bg-sky-600 text-white hover:bg-sky-500 shadow-xs flex items-center justify-center gap-2 cursor-pointer"
              >
                <User class="w-3.5 h-3.5" />
                <span>Return to Resident Sign In</span>
              </button>
            </div>
          </div>

          <!-- SUB-VIEW C: REGISTRATION WITH VERIFIED QR CODE -->
          <div v-else-if="studentMode === 'register' && isTokenValid && !isTokenExpired" class="space-y-3.5 pt-1">
            <!-- Verified QR Banner with Active Countdown -->
            <div
              class="p-3.5 rounded-2xl border transition-colors bg-emerald-50/70 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/60"
            >
              <div class="flex items-center justify-between gap-2 mb-1">
                <span class="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 dark:text-emerald-300">
                  <ShieldCheck class="w-4 h-4" />
                  <span>Hostel Desk Scan Verified</span>
                </span>
                <!-- Session Countdown Pill -->
                <span class="inline-flex items-center gap-1 text-[11px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 border border-emerald-300/50 dark:border-emerald-700/50">
                  <Clock class="w-3 h-3 text-emerald-600 dark:text-emerald-400 animate-pulse" />
                  <span>{{ formattedTimeRemaining }}</span>
                </span>
              </div>
              <p class="text-[11px] text-emerald-800/80 dark:text-emerald-300/80">
                Locked to <strong class="text-emerald-900 dark:text-emerald-100">{{ verifiedHostel || hostelName }}</strong> laundry hub.
              </p>
            </div>

            <form @submit.prevent="handleStudentSubmit" class="space-y-3">
              <!-- Full Name -->
              <div>
                <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                  Full Resident Name
                </label>
                <input
                  v-model="studentName"
                  type="text"
                  required
                  placeholder="e.g. Akshat Dhaundiyal"
                  :class="[
                    'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                    darkMode
                      ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                      : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                  ]"
                />
              </div>

              <!-- Room Number -->
              <div>
                <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                  Room Number
                </label>
                <input
                  v-model="studentRoom"
                  type="text"
                  required
                  placeholder="e.g. 214 or B-214"
                  :class="[
                    'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium uppercase transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                    darkMode
                      ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                      : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                  ]"
                />
              </div>

              <!-- Mobile Phone (For Cycle WhatsApp/SMS Alerts) -->
              <div>
                <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                  Mobile Phone Number <span class="font-normal text-slate-400">(Optional • for cycle alerts)</span>
                </label>
                <div class="relative">
                  <input
                    v-model="studentPhone"
                    type="tel"
                    placeholder="e.g. 9876543210"
                    :class="[
                      'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                      darkMode
                        ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                        : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                    ]"
                  />
                  <Phone class="w-3.5 h-3.5 text-slate-400 absolute right-3 top-3 pointer-events-none" />
                </div>
              </div>

              <!-- Password -->
              <div>
                <div class="flex items-center justify-between mb-1">
                  <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block">
                    Create Password
                  </label>
                </div>
                <div class="relative">
                  <input
                    v-model="studentPassword"
                    :type="showPassword ? 'text' : 'password'"
                    required
                    placeholder="••••••••"
                    :class="[
                      'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20 pr-10',
                      darkMode
                        ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                        : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                    ]"
                  />
                  <button
                    type="button"
                    @click="showPassword = !showPassword"
                    class="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <EyeOff v-if="showPassword" class="w-4 h-4" />
                    <Eye v-else class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Submit Button -->
              <button
                type="submit"
                :disabled="isLoading"
                class="w-full mt-2 py-3 rounded-xl text-xs font-bold transition-all bg-emerald-600 text-white hover:bg-emerald-500 shadow-md disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
              >
                <span>{{ isLoading ? 'Registering Account...' : 'Complete Resident Registration' }}</span>
                <ArrowRight class="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

          <!-- SUB-VIEW C: VERIFICATION LOADING SPINNER -->
          <div v-else-if="studentMode === 'register' && isVerifyingToken" class="text-center py-8">
            <RefreshCw class="w-8 h-8 text-sky-500 animate-spin mx-auto mb-3" />
            <h3 class="text-sm font-bold text-slate-900 dark:text-white">Verifying Desk QR Code...</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Validating hostel signature with security station...
            </p>
          </div>

          <!-- SUB-VIEW D: NO QR TOKEN PROVIDED / EXPIRED GUIDANCE VIEW -->
          <div v-else-if="studentMode === 'register'" class="space-y-4 pt-1">
            <!-- Token Error / Expired Notice -->
            <div
              v-if="tokenError || isTokenExpired"
              class="p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2.5"
            >
              <AlertCircle class="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
              <div class="leading-relaxed">
                <strong class="font-bold block mb-0.5">Registration Scan Expired or Invalid</strong>
                <span>{{ tokenError || 'The scanned QR code has timed out. Please scan the newly refreshed QR code displayed at the laundry desk.' }}</span>
              </div>
            </div>

            <!-- Dynamic QR Guidance Card -->
            <div
              :class="[
                'p-5 rounded-2xl border text-center transition-all',
                darkMode ? 'bg-[#10131a] border-slate-800' : 'bg-slate-50/90 border-slate-200'
              ]"
            >
              <div class="relative w-14 h-14 mx-auto mb-3 flex items-center justify-center rounded-2xl bg-sky-500/10 dark:bg-sky-400/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
                <QrCode class="w-7 h-7" />
                <span class="absolute -top-1 -right-1 flex h-3 w-3">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-3 w-3 bg-sky-500"></span>
                </span>
              </div>

              <h3 class="text-sm font-bold text-slate-900 dark:text-white">
                Hostel Desk QR Required
              </h3>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs mx-auto leading-relaxed">
                To prevent unauthorized machine reservations, new resident registration is verified at the laundry station desk.
              </p>

              <!-- Step by Step instructions -->
              <div class="mt-4 space-y-2 text-left text-[11px] font-medium text-slate-600 dark:text-slate-300">
                <div class="flex items-center gap-2.5 p-2 rounded-xl bg-white/60 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
                  <span class="w-5 h-5 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-600 dark:text-sky-400 font-bold flex items-center justify-center text-[10px] shrink-0">1</span>
                  <span>Visit your hostel laundry room or reception desk.</span>
                </div>

                <div class="flex items-center gap-2.5 p-2 rounded-xl bg-white/60 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
                  <span class="w-5 h-5 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-600 dark:text-sky-400 font-bold flex items-center justify-center text-[10px] shrink-0">2</span>
                  <span>Scan the live 1-minute rotating QR code on the desk tablet screen.</span>
                </div>

                <div class="flex items-center gap-2.5 p-2 rounded-xl bg-white/60 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
                  <span class="w-5 h-5 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-600 dark:text-sky-400 font-bold flex items-center justify-center text-[10px] shrink-0">3</span>
                  <span>Your registration form will unlock with 5 minutes to set your password.</span>
                </div>
              </div>

              <!-- Return to Login Button -->
              <button
                type="button"
                @click="studentMode = 'login'; clearFeedback()"
                class="w-full mt-4 py-2.5 px-4 rounded-xl text-xs font-bold transition-all bg-sky-600 text-white hover:bg-sky-500 shadow-xs flex items-center justify-center gap-2 cursor-pointer"
              >
                <User class="w-3.5 h-3.5" />
                <span>Already Registered? Sign In</span>
              </button>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- TAB 2: HOSTEL OPERATOR / ADMIN PIN LOGIN                           -->
        <!-- =================================================================== -->
        <div v-else class="space-y-4">
          <div class="p-3.5 rounded-2xl bg-emerald-50/80 dark:bg-emerald-950/20 border border-emerald-200/60 dark:border-emerald-900/40 text-xs text-emerald-800 dark:text-emerald-300">
            <div class="font-bold flex items-center gap-1.5 mb-1">
              <KeyRound class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Operator Security PIN</span>
            </div>
            <p class="leading-relaxed font-normal text-[11px]">
              Access telemetry threshold calibrations, physical QR onboarding station, and resident registry.
            </p>
          </div>

          <form @submit.prevent="handleAdminSubmit" class="space-y-4">
            <div>
              <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                Admin Console PIN
              </label>
              <div class="relative">
                <input
                  v-model="adminPin"
                  :type="showAdminPin ? 'text' : 'password'"
                  maxlength="8"
                  required
                  placeholder="••••"
                  autofocus
                  :class="[
                    'w-full text-center tracking-[0.6em] text-lg font-mono py-2.5 rounded-xl border transition focus:outline-none focus:ring-2 focus:ring-emerald-500/20',
                    darkMode
                      ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-emerald-500'
                      : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-emerald-500'
                  ]"
                />
                <button
                  type="button"
                  @click="showAdminPin = !showAdminPin"
                  class="absolute right-3 top-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  <EyeOff v-if="showAdminPin" class="w-4 h-4" />
                  <Eye v-else class="w-4 h-4" />
                </button>
              </div>
            </div>

            <button
              type="submit"
              :disabled="isLoading || !adminPin"
              class="w-full py-3 rounded-xl text-xs font-bold transition-all bg-emerald-600 text-white hover:bg-emerald-500 shadow-md disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              <Lock class="w-3.5 h-3.5" />
              <span>{{ isLoading ? 'Verifying PIN...' : 'Unlock Operator Console' }}</span>
            </button>
          </form>
        </div>
      </div>
    </main>

    <!-- FOOTER -->
    <footer
      :class="[
        'w-full py-4 px-6 border-t text-center text-xs transition-colors',
        darkMode ? 'border-slate-800/80 text-slate-500' : 'border-slate-200/80 text-slate-500'
      ]"
    >
      <div class="max-w-md mx-auto flex items-center justify-between">
        <span>WashQueue Smart Laundry System</span>
        <NuxtLink to="/" class="font-semibold text-sky-600 dark:text-sky-400 hover:underline">
          Return to Hub →
        </NuxtLink>
      </div>
    </footer>
  </div>
</template>
