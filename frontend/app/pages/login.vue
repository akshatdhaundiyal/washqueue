<script setup>
import { ref, computed, watch, onMounted } from 'vue'
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
  Sparkles,
  ArrowLeft,
  Eye,
  EyeOff,
  ArrowUpRight,
  School,
  Building2,
  Home
} from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'
import AppBranding from '~/components/common/AppBranding.vue'
import {
  CAMPUS_DIRECTORY,
  DEFAULT_CAMPUS,
  getCollegesForUniversity,
  getHostelsForCollege
} from '~/data/campusDirectory'

const { institutionName, hostelName } = useHostelBranding()
const config = useRuntimeConfig()
const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'

// Persistent Theme Synchronization
const { isDark: darkMode, toggleTheme, setTheme } = useAppTheme()

// Mode: 'student' | 'admin'
const loginRole = ref('student')

// Student Auth State
const studentMode = ref('login') // 'login' | 'register'
const studentRoom = ref('')
const studentPassword = ref('')
const studentName = ref('')
const studentEmail = ref('')
const showPassword = ref(false)

// Campus Selection State for Registration
const selectedUniversity = ref(DEFAULT_CAMPUS.university)
const selectedCollege = ref(DEFAULT_CAMPUS.college)
const selectedHostel = ref(DEFAULT_CAMPUS.hostel)

const availableColleges = computed(() => {
  return getCollegesForUniversity(selectedUniversity.value)
})

const availableHostels = computed(() => {
  return getHostelsForCollege(selectedUniversity.value, selectedCollege.value)
})

// Synchronize cascading selections when parent changes
watch(selectedUniversity, (newUni) => {
  const colleges = getCollegesForUniversity(newUni)
  if (colleges.length > 0) {
    if (!colleges.some(c => c.name === selectedCollege.value)) {
      selectedCollege.value = colleges[0].name
    }
  }
})

watch(selectedCollege, (newCollege) => {
  const hostels = getHostelsForCollege(selectedUniversity.value, newCollege)
  if (hostels.length > 0) {
    if (!hostels.includes(selectedHostel.value)) {
      selectedHostel.value = hostels[0]
    }
  }
})

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

// Quick 1-Click Demo Logins
const fillStudentDemo = () => {
  clearFeedback()
  studentRole()
  studentRoom.value = '214'
  studentName.value = 'Akshat Dhaundiyal'
  studentPassword.value = 'hostel2026'
}

const fillAdminDemo = () => {
  clearFeedback()
  loginRole.value = 'admin'
  adminPin.value = '1234'
}

const studentRole = () => {
  loginRole.value = 'student'
  clearFeedback()
}

// Student Login Submission
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
      // Register Mode
      const payload = {
        name: studentName.value.trim(),
        room_number: studentRoom.value.trim().toUpperCase(),
        password: studentPassword.value,
        email: studentEmail.value.trim() || undefined,
        university: selectedUniversity.value,
        college: selectedCollege.value,
        hostel: selectedHostel.value
      }

      const res = await $fetch(`${apiBase}/api/auth/register`, {
        method: 'POST',
        body: payload
      })

      if (typeof window !== 'undefined') {
        localStorage.setItem('washqueue_student_user', JSON.stringify(res))
      }

      successMessage.value = `Account registered for Room ${res.room_number} (${res.hostel || selectedHostel.value})! Redirecting to laundry hub...`
      setTimeout(() => {
        navigateTo('/')
      }, 800)
    }
  } catch (err) {
    // If backend is unreachable or offline, allow seamless offline demo fallback
    if (!err.response && !err.data) {
      if (typeof window !== 'undefined') {
        localStorage.setItem(
          'washqueue_student_user',
          JSON.stringify({
            name: studentName.value.trim() || 'Akshat Dhaundiyal',
            room_number: studentRoom.value.trim().toUpperCase() || '214',
            role: 'student',
            university: selectedUniversity.value,
            college: selectedCollege.value,
            hostel: selectedHostel.value
          })
        )
      }
      successMessage.value = 'Offline session initialized! Redirecting...'
      setTimeout(() => navigateTo('/'), 600)
      return
    }
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
    // Fallback: If offline or default demo PIN 1234
    if (pin === '1234') {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('admin_pin', '1234')
      }
      successMessage.value = 'Operator PIN verified! Opening Console...'
      setTimeout(() => navigateTo('/admin'), 600)
      return
    }
    errorMessage.value = err.data?.detail || 'Invalid Admin PIN. (Default dev PIN is 1234)'
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

    <!-- MAIN LOGIN CARD -->
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

        <!-- COMMON ROLE SWITCHER TABS -->
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
        <!-- TAB 1: RESIDENT STUDENT LOGIN & REGISTRATION                       -->
        <!-- =================================================================== -->
        <div v-if="loginRole === 'student'" class="space-y-4">
          <!-- Sign In vs Register sub-toggle -->
          <div class="flex items-center justify-center gap-4 text-xs font-semibold pb-2 border-b border-slate-100 dark:border-slate-800">
            <button
              @click="studentMode = 'login'; clearFeedback()"
              :class="studentMode === 'login' ? 'text-sky-600 dark:text-sky-400 font-bold border-b-2 border-sky-600 pb-1 -mb-2.5' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'"
            >
              Resident Sign In
            </button>
            <button
              @click="studentMode = 'register'; clearFeedback()"
              :class="studentMode === 'register' ? 'text-sky-600 dark:text-sky-400 font-bold border-b-2 border-sky-600 pb-1 -mb-2.5' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800'"
            >
              New Resident Sign Up
            </button>
          </div>

          <form @submit.prevent="handleStudentSubmit" class="space-y-3.5 pt-1">
            <!-- Full Name (Only for Registration or optional double-sharing login) -->
            <div>
              <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                {{ studentMode === 'register' ? 'Full Resident Name' : 'Resident Name (Optional)' }}
              </label>
              <input
                v-model="studentName"
                type="text"
                :required="studentMode === 'register'"
                placeholder="e.g. Akshat Dhaundiyal"
                :class="[
                  'w-full px-3.5 py-2.5 rounded-xl border text-xs font-medium transition focus:outline-none focus:ring-2 focus:ring-sky-500/20',
                  darkMode
                    ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-sky-500'
                    : 'bg-slate-50/80 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-sky-500'
                ]"
              />
            </div>

            <!-- Cascading Campus Affiliation: University, College, Hostel (Registration Only) -->
            <div
              v-if="studentMode === 'register'"
              class="space-y-3 p-3.5 rounded-2xl border transition-colors"
              :class="darkMode ? 'bg-[#0c0e14]/70 border-slate-800' : 'bg-slate-50/80 border-slate-200'"
            >
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400 flex items-center gap-1.5">
                  <School class="w-3.5 h-3.5" />
                  Campus & Hostel Assignment
                </span>
                <span class="text-[10px] font-medium text-slate-400">Hostel Allocation</span>
              </div>

              <!-- 1. University Select -->
              <div>
                <label class="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                  University / Institution
                </label>
                <div class="relative">
                  <select
                    v-model="selectedUniversity"
                    class="w-full px-3 py-2 rounded-xl border text-xs font-semibold appearance-none transition focus:outline-none focus:ring-2 focus:ring-sky-500/20 pr-8 cursor-pointer"
                    :class="darkMode ? 'bg-[#151921] border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900 shadow-2xs'"
                  >
                    <option v-for="uni in CAMPUS_DIRECTORY" :key="uni.id" :value="uni.name">
                      {{ uni.name }} ({{ uni.shortName }})
                    </option>
                  </select>
                  <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-[10px]">
                    ▼
                  </div>
                </div>
              </div>

              <!-- 2. College / Department Select -->
              <div>
                <label class="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                  College / School / Department
                </label>
                <div class="relative">
                  <select
                    v-model="selectedCollege"
                    class="w-full px-3 py-2 rounded-xl border text-xs font-semibold appearance-none transition focus:outline-none focus:ring-2 focus:ring-sky-500/20 pr-8 cursor-pointer"
                    :class="darkMode ? 'bg-[#151921] border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900 shadow-2xs'"
                  >
                    <option v-for="col in availableColleges" :key="col.id" :value="col.name">
                      {{ col.name }}
                    </option>
                  </select>
                  <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-[10px]">
                    ▼
                  </div>
                </div>
              </div>

              <!-- 3. Hostel / Residence Hall Select -->
              <div>
                <label class="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                  Hostel / Residence Hall
                </label>
                <div class="relative">
                  <select
                    v-model="selectedHostel"
                    class="w-full px-3 py-2 rounded-xl border text-xs font-bold appearance-none transition focus:outline-none focus:ring-2 focus:ring-sky-500/20 pr-8 text-sky-600 dark:text-sky-400 cursor-pointer"
                    :class="darkMode ? 'bg-[#151921] border-slate-700' : 'bg-white border-slate-200 shadow-2xs'"
                  >
                    <option v-for="h in availableHostels" :key="h" :value="h">
                      {{ h }}
                    </option>
                  </select>
                  <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-sky-500 text-[10px]">
                    ▼
                  </div>
                </div>
                <p class="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                  Your account will be bound to this hostel's laundry hub.
                </p>
              </div>
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

            <!-- Email (Optional, only for register) -->
            <div v-if="studentMode === 'register'">
              <label class="text-[11px] font-bold text-slate-500 dark:text-slate-400 block mb-1">
                Email Address (Optional)
              </label>
              <input
                v-model="studentEmail"
                type="email"
                placeholder="student@hostel.internal"
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
              class="w-full mt-2 py-3 rounded-xl text-xs font-bold transition-all bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <span>{{ isLoading ? 'Authenticating...' : studentMode === 'login' ? 'Sign In as Resident' : 'Register Resident Account' }}</span>
              <ArrowRight class="w-3.5 h-3.5" />
            </button>
          </form>

          <!-- One-Tap Demo Fill Button -->
          <div class="pt-3 border-t border-slate-100 dark:border-slate-800 text-center">
            <button
              type="button"
              @click="fillStudentDemo"
              class="text-xs font-bold text-sky-600 dark:text-sky-400 hover:underline inline-flex items-center gap-1"
            >
              <Sparkles class="w-3.5 h-3.5 text-amber-500" />
              <span>One-Tap Resident Demo (Room 214 • Akshat)</span>
            </button>
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
              Access machine telemetry thresholds, Tuya local IoT controls, and SQLite database console.
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
              class="w-full py-3 rounded-xl text-xs font-bold transition-all bg-emerald-600 text-white hover:bg-emerald-500 shadow-md disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Lock class="w-3.5 h-3.5" />
              <span>{{ isLoading ? 'Verifying PIN...' : 'Unlock Operator Console' }}</span>
            </button>
          </form>

          <!-- One-Tap Admin Demo Fill Button -->
          <div class="pt-3 border-t border-slate-100 dark:border-slate-800 text-center">
            <button
              type="button"
              @click="fillAdminDemo"
              class="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline inline-flex items-center gap-1"
            >
              <Sparkles class="w-3.5 h-3.5 text-amber-500" />
              <span>One-Tap Operator Demo (PIN: 1234)</span>
            </button>
          </div>
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
