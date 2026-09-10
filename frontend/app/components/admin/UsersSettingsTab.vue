<script setup>
import { ref, computed } from 'vue'
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
  Trash2
} from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'
import AppBranding from '~/components/common/AppBranding.vue'

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
                    {{ user.hostel || 'Block B • Aryabhatta Hall' }}
                  </div>
                  <div class="text-[10px] text-slate-400 truncate max-w-[200px]" :title="user.university || 'Apex Institute of Technology'">
                    {{ user.university || 'Apex Institute of Technology' }}
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 text-sky-500 font-bold">
                <div class="flex items-center gap-1.5">
                  <span>{{ user.room_number || 'Room B-214' }}</span>
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
              <td colspan="5" class="py-8 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
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
