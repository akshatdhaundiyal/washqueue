<script setup>
import { ref, watch, onMounted } from 'vue'
import { Settings, X, Sun, Moon, KeyRound, ArrowUpRight, School, Lock, Building2, Trash2, AlertTriangle } from 'lucide-vue-next'

const { institutionName, hostelName } = useHostelBranding()
const config = useRuntimeConfig()
const apiBase = config.public?.apiBaseUrl || 'http://localhost:8000'

const studentUser = ref(null)
const isDeleting = ref(false)
const showDeleteConfirm = ref(false)

const loadStudentUser = () => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('washqueue_student_user')
      studentUser.value = stored ? JSON.parse(stored) : null
    } catch (e) {
      studentUser.value = null
    }
  }
}

onMounted(() => {
  loadStudentUser()
})

const props = defineProps({
  showSettings: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  pushAlertEnabled: {
    type: Boolean,
    default: true
  },
  anonymousBuzzEnabled: {
    type: Boolean,
    default: true
  }
})

watch(() => props.showSettings, (isOpen) => {
  if (isOpen) {
    showDeleteConfirm.value = false
    loadStudentUser()
  }
})

const emit = defineEmits([
  'close',
  'set-theme',
  'update:pushAlertEnabled',
  'update:anonymousBuzzEnabled'
])

const handleDeleteProfile = async () => {
  if (!studentUser.value) return
  isDeleting.value = true

  try {
    if (studentUser.value.id) {
      await $fetch(`${apiBase}/api/auth/profile/${studentUser.value.id}`, {
        method: 'DELETE'
      })
    }
  } catch (err) {
    console.error('Profile deletion error:', err)
  } finally {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('washqueue_student_user')
    }
    studentUser.value = null
    isDeleting.value = false
    showDeleteConfirm.value = false
    emit('close')
    navigateTo('/login')
  }
}
</script>

<template>
  <div
    v-if="showSettings"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn"
  >
    <div
      :class="[
        'w-full max-w-[380px] rounded-[32px] p-6 sm:p-7 border shadow-2xl transition-all',
        darkMode ? 'bg-[#151921] border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
      ]"
    >
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-3.5 border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300">
            <Settings class="w-4 h-4" />
          </div>
          <div>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white">App Settings</h3>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">WashQueue Preferences</p>
          </div>
        </div>
        <button
          @click="emit('close')"
          class="w-8 h-8 rounded-full border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Theme Mode Segmented Picker -->
      <div class="my-5 space-y-4">
        <div>
          <label class="text-[10px] uppercase font-bold tracking-wider text-slate-400 dark:text-slate-500 block mb-2">
            Theme Appearance
          </label>
          <div class="grid grid-cols-2 p-1 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700">
            <button
              @click="emit('set-theme', 'light')"
              :class="[
                'py-2 px-3 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1.5',
                !darkMode ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
              ]"
            >
              <Sun class="w-3.5 h-3.5 text-amber-500" />
              <span>Light</span>
            </button>
            <button
              @click="emit('set-theme', 'dark')"
              :class="[
                'py-2 px-3 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1.5',
                darkMode ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:text-slate-900'
              ]"
            >
              <Moon class="w-3.5 h-3.5 text-sky-400" />
              <span>Dark</span>
            </button>
          </div>
        </div>

        <!-- Additional Settings Toggles -->
        <div class="space-y-3 pt-2">
          <div class="flex items-center justify-between text-xs font-medium">
            <span class="text-slate-700 dark:text-slate-300">Push Alert on 0W Motor Stop</span>
            <input
              type="checkbox"
              :checked="pushAlertEnabled"
              @change="emit('update:pushAlertEnabled', $event.target.checked)"
              class="w-4 h-4 accent-slate-900 dark:accent-white cursor-pointer"
            />
          </div>
          <div class="flex items-center justify-between text-xs font-medium pt-2 border-t border-slate-100 dark:border-slate-800">
            <span class="text-slate-700 dark:text-slate-300">Allow Anonymous Peer Buzzes</span>
            <input
              type="checkbox"
              :checked="anonymousBuzzEnabled"
              @change="emit('update:anonymousBuzzEnabled', $event.target.checked)"
              class="w-4 h-4 accent-slate-900 dark:accent-white cursor-pointer"
            />
          </div>
        </div>

        <!-- Campus & Hostel Affiliation (Read-only for residents) -->
        <div class="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2.5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1.5">
              <School class="w-3.5 h-3.5 text-sky-500" />
              <label class="text-[10px] uppercase font-bold tracking-wider text-slate-400 dark:text-slate-500">
                Institutional Affiliation
              </label>
            </div>
            <span class="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200/80 dark:border-slate-700/80">
              <Lock class="w-2.5 h-2.5" />
              <span>Locked</span>
            </span>
          </div>

          <div class="p-3 rounded-2xl border space-y-2.5 bg-slate-50/70 dark:bg-slate-800/40 border-slate-200/80 dark:border-slate-800">
            <!-- University & College -->
            <div>
              <span class="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 block">University & College</span>
              <p class="text-xs font-bold text-slate-800 dark:text-slate-200">
                {{ studentUser?.university || institutionName }}
              </p>
              <p class="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                {{ studentUser?.college || 'School of Engineering & Technology' }}
              </p>
            </div>

            <!-- Assigned Hostel -->
            <div class="pt-2 border-t border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
              <div>
                <span class="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 block">Assigned Hostel Hall</span>
                <span class="text-xs font-bold text-sky-600 dark:text-sky-400">
                  {{ studentUser?.hostel || hostelName }}
                </span>
              </div>
              <div v-if="studentUser?.room_number" class="text-right">
                <span class="text-[10px] uppercase font-bold text-slate-400 dark:text-slate-500 block">Room</span>
                <span class="text-xs font-mono font-bold text-slate-700 dark:text-slate-300">
                  {{ studentUser.room_number }}
                </span>
              </div>
            </div>
          </div>
          <p class="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed px-0.5">
            Hostel assignments are managed by administration and cannot be modified by residents.
          </p>
        </div>

        <!-- Quick Navigation Shortcuts -->
        <!-- Sign In / Switch Resident Account -->
        <div class="pt-3 border-t border-slate-100 dark:border-slate-800">
          <NuxtLink
            to="/login"
            class="w-full py-2 px-3.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-bold flex items-center justify-between text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <div class="flex items-center gap-2.5">
              <KeyRound class="w-3.5 h-3.5 text-amber-500" />
              <span>Sign In / Switch Resident</span>
            </div>
            <ArrowUpRight class="w-3.5 h-3.5 text-slate-400" />
          </NuxtLink>
        </div>

        <!-- Self-Profile Deletion (Student Residents) with Confirmation -->
        <div v-if="studentUser" class="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
          <!-- Confirmation Dialog Card -->
          <div
            v-if="showDeleteConfirm"
            class="p-3.5 rounded-2xl border border-rose-200 dark:border-rose-900/70 bg-rose-50/90 dark:bg-rose-950/40 space-y-2.5 animate-fadeIn"
          >
            <div class="flex items-start gap-2.5">
              <AlertTriangle class="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h4 class="text-xs font-bold text-rose-900 dark:text-rose-200">
                  Permanently delete your profile?
                </h4>
                <p class="text-[11px] text-rose-700 dark:text-rose-300/80 mt-0.5 leading-snug">
                  This will delete the account for <span class="font-bold">{{ studentUser.name }}</span> (Room {{ studentUser.room_number || 'N/A' }}), clear active queue bookings, and remove your resident credentials.
                </p>
              </div>
            </div>

            <div class="flex items-center gap-2 pt-1">
              <button
                @click="showDeleteConfirm = false"
                :disabled="isDeleting"
                class="flex-1 py-1.5 px-3 rounded-xl border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800 transition"
              >
                Cancel
              </button>
              <button
                @click="handleDeleteProfile"
                :disabled="isDeleting"
                class="flex-1 py-1.5 px-3 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-xs transition flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Trash2 class="w-3 h-3" />
                <span>{{ isDeleting ? 'Deleting...' : 'Yes, Delete' }}</span>
              </button>
            </div>
          </div>

          <!-- Trigger Delete Button -->
          <button
            v-else
            @click="showDeleteConfirm = true"
            class="w-full py-2 px-3.5 rounded-xl border border-rose-200/80 dark:border-rose-900/50 text-xs font-bold flex items-center justify-between text-rose-600 dark:text-rose-400 hover:bg-rose-50/80 dark:hover:bg-rose-950/30 transition-colors"
          >
            <div class="flex items-center gap-2.5">
              <Trash2 class="w-3.5 h-3.5 text-rose-500" />
              <span>Delete Resident Profile</span>
            </div>
            <span class="text-[9px] uppercase font-mono font-bold tracking-wider px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-900/40 text-rose-600 dark:text-rose-400">
              Confirm
            </span>
          </button>
        </div>
      </div>

      <!-- Done Button -->
      <button
        @click="emit('close')"
        class="w-full py-2.5 rounded-full text-xs font-bold bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:opacity-90 transition-all mt-2"
      >
        Done
      </button>
    </div>
  </div>
</template>
