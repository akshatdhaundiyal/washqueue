<script setup>
import { ref, onMounted } from 'vue'
import {
  Waves,
  Disc,
  User,
  Settings,
  Sun,
  Moon,
  School,
  LogOut
} from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'

const { institutionName, hostelName } = useHostelBranding()

const studentUser = ref(null)

onMounted(() => {
  if (typeof localStorage !== 'undefined') {
    try {
      const raw = localStorage.getItem('washqueue_student_user')
      studentUser.value = raw ? JSON.parse(raw) : null
    } catch (e) {}
  }
})

const props = defineProps({
  activeTab: {
    type: String,
    required: true
  },
  freeMachinesCount: {
    type: Number,
    default: 0
  },
  myMachine: {
    type: Object,
    required: true
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:activeTab', 'open-settings', 'set-theme'])
</script>

<template>
  <aside
    :class="[
      'hidden md:flex w-64 lg:w-72 flex-col justify-between border-r shrink-0 h-screen sticky top-0 p-5 lg:p-6 transition-colors duration-200 z-30',
      darkMode ? 'bg-[#10131a] border-slate-800/80' : 'bg-white border-slate-200/80'
    ]"
  >
    <div class="space-y-7">
      <!-- App Logo & Title + University & Hostel Branding -->
      <div class="space-y-3 px-1 pt-1">
        <AppLogo mode="full" :dark-mode="darkMode" size-class="h-9" />
        
        <!-- University / Organization & Hostel Badge -->
        <div
          class="flex items-center gap-2 px-2.5 py-1.5 rounded-xl border transition-colors"
          :class="darkMode ? 'bg-slate-800/40 border-slate-700/60' : 'bg-slate-50 border-slate-200/80'"
        >
          <div class="w-5 h-5 rounded-md flex items-center justify-center shrink-0 bg-sky-500/10 text-sky-600 dark:text-sky-400">
            <School class="w-3.5 h-3.5" />
          </div>
          <div class="min-w-0 flex-1">
            <span class="text-[11px] font-bold text-slate-800 dark:text-slate-200 block truncate leading-tight">
              {{ institutionName }}
            </span>
            <span class="text-[10px] font-semibold text-slate-500 dark:text-slate-400 block truncate">
              {{ hostelName }}
            </span>
          </div>
        </div>
      </div>

      <!-- Main Navigation Links -->
      <nav class="space-y-1">
        <!-- Option 1: Home -->
        <button
          @click="emit('update:activeTab', 'home')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            activeTab === 'home'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Waves class="w-4 h-4" />
            <span>Home Status</span>
          </div>
          <span
            v-if="myMachine.claimed && myMachine.isOn"
            class="w-2 h-2 rounded-full bg-sky-500 animate-ping"
            title="Machine active"
          />
        </button>

        <!-- Option 2: Appliances Hub -->
        <button
          @click="emit('update:activeTab', 'machines')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            activeTab === 'machines'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Disc class="w-4 h-4" />
            <span>Appliances Hub</span>
          </div>
          <span
            v-if="freeMachinesCount > 0"
            :class="[
              'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full tabular-nums',
              activeTab === 'machines'
                ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200/60 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/20'
            ]"
          >
            {{ freeMachinesCount }} Free
          </span>
        </button>

        <!-- Option 3: Resident Profile -->
        <button
          @click="emit('update:activeTab', 'profile')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            activeTab === 'profile'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <User class="w-4 h-4" />
            <span>Resident Profile</span>
          </div>
        </button>

        <!-- Option 4: Settings -->
        <button
          @click="emit('open-settings')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Settings class="w-4 h-4" />
            <span>Settings</span>
          </div>
        </button>
      </nav>
    </div>

    <!-- Sidebar Bottom: Theme Switcher & Resident Card -->
    <div class="space-y-3 pt-4 border-t border-slate-200/80 dark:border-slate-800/80">
      <!-- Quick Theme Toggle Bar -->
      <div class="flex items-center justify-between px-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        <span>Theme</span>
        <div class="flex items-center p-0.5 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80">
          <button
            @click="emit('set-theme', 'light')"
            :class="[
              'p-1.5 rounded-full transition-all',
              !darkMode ? 'bg-white text-amber-500 shadow-xs' : 'text-slate-400 hover:text-slate-700 dark:hover:text-white'
            ]"
            title="Light Mode"
          >
            <Sun class="w-3.5 h-3.5" />
          </button>
          <button
            @click="emit('set-theme', 'dark')"
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

      <!-- Resident Quick Card with Sign Out / Switch Affordance -->
      <div
        @click="emit('update:activeTab', 'profile')"
        :class="[
          'p-3 rounded-2xl border flex items-center justify-between cursor-pointer transition-all hover:border-slate-300 dark:hover:border-slate-700 select-none group',
          darkMode ? 'bg-slate-800/40 border-slate-700/60' : 'bg-slate-50 border-slate-200/70 hover:bg-slate-100/70'
        ]"
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="relative shrink-0">
            <img
              src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop&crop=faces"
              alt="Avatar"
              class="w-9 h-9 rounded-full object-cover ring-2 ring-white dark:ring-slate-700"
            />
            <span
              :class="[
                'absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-slate-900',
                myMachine.claimed && myMachine.isOn ? 'bg-sky-500 animate-pulse' : 'bg-emerald-500'
              ]"
            />
          </div>
          <div class="min-w-0 flex-1">
            <h4 class="text-xs font-bold text-slate-900 dark:text-white truncate">
              {{ studentUser?.name || 'Resident' }}
            </h4>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {{ studentUser?.room_number ? `Room ${studentUser.room_number}` : 'Tap to sign in' }}
            </p>
          </div>
        </div>

        <NuxtLink
          to="/login"
          @click.stop
          class="p-1.5 rounded-xl border border-transparent group-hover:border-slate-200 dark:group-hover:border-slate-700 text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all"
          title="Sign out or switch account"
        >
          <LogOut class="w-3.5 h-3.5" />
        </NuxtLink>
      </div>
    </div>
  </aside>
</template>
