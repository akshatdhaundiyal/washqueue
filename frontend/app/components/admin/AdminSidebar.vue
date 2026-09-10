<script setup>
import {
  Shield,
  Layers,
  Zap,
  Database,
  Users,
  Sun,
  Moon,
  Lock
} from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'

const { institutionName, hostelName } = useHostelBranding()

const props = defineProps({
  currentAdminTab: {
    type: String,
    required: true
  },
  machinesCount: {
    type: Number,
    default: 0
  },
  plugsCount: {
    type: Number,
    default: 0
  },
  dbTarget: {
    type: String,
    default: 'sqlite'
  },
  usersCount: {
    type: Number,
    default: 0
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:currentAdminTab', 'set-theme', 'lock-session'])
</script>

<template>
  <aside
    :class="[
      'hidden md:flex w-64 lg:w-72 flex-col justify-between border-r shrink-0 h-screen sticky top-0 p-5 lg:p-6 transition-colors duration-200 z-30',
      darkMode ? 'bg-[#10131a] border-slate-800/80' : 'bg-white border-slate-200/80'
    ]"
  >
    <div class="space-y-7">
      <!-- Branding: WashQueue Logo + Operator Console & University/Hostel -->
      <div class="space-y-3 px-1 pt-1">
        <AppLogo mode="full" :dark-mode="darkMode" size-class="h-9" />
        
        <div
          class="flex items-center gap-2 px-2.5 py-1.5 rounded-xl border transition-colors"
          :class="darkMode ? 'bg-slate-800/40 border-slate-700/60' : 'bg-emerald-50/70 border-emerald-200/80'"
        >
          <div class="w-5 h-5 rounded-md flex items-center justify-center shrink-0 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
            <Shield class="w-3.5 h-3.5" />
          </div>
          <div class="min-w-0 flex-1">
            <span class="text-[11px] font-bold text-slate-800 dark:text-slate-200 block truncate leading-tight">
              {{ institutionName }}
            </span>
            <span class="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 block truncate">
              Operator Console • {{ hostelName }}
            </span>
          </div>
        </div>
      </div>

      <!-- Navigation Links -->
      <nav class="space-y-1">
        <!-- Tab 1: Fleet & Bookings -->
        <button
          @click="emit('update:currentAdminTab', 'fleet')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            currentAdminTab === 'fleet'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Layers class="w-4 h-4" />
            <span>Fleet & Bookings</span>
          </div>
          <span
            :class="[
              'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full tabular-nums',
              currentAdminTab === 'fleet'
                ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
            ]"
          >
            {{ machinesCount }}
          </span>
        </button>

        <!-- Tab 2: Smart Plugs & IoT -->
        <button
          @click="emit('update:currentAdminTab', 'iot')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            currentAdminTab === 'iot'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Zap class="w-4 h-4 text-amber-500" />
            <span>Smart Plugs & IoT</span>
          </div>
          <span
            :class="[
              'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full tabular-nums',
              currentAdminTab === 'iot'
                ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
                : 'bg-amber-50 text-amber-700 border border-amber-200/60 dark:bg-amber-500/15 dark:text-amber-400'
            ]"
          >
            {{ plugsCount }}
          </span>
        </button>

        <!-- Tab 3: Database Portal -->
        <button
          @click="emit('update:currentAdminTab', 'database')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            currentAdminTab === 'database'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Database class="w-4 h-4 text-sky-500" />
            <span>Database Portal</span>
          </div>
          <span
            :class="[
              'text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded-full',
              currentAdminTab === 'database'
                ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
                : 'bg-sky-50 text-sky-700 border border-sky-200/60 dark:bg-sky-500/15 dark:text-sky-400'
            ]"
          >
            {{ dbTarget }}
          </span>
        </button>

        <!-- Tab 4: Users & Settings -->
        <button
          @click="emit('update:currentAdminTab', 'users')"
          :class="[
            'w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all group',
            currentAdminTab === 'users'
              ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/60'
          ]"
        >
          <div class="flex items-center gap-3">
            <Users class="w-4 h-4 text-emerald-500" />
            <span>Users & Settings</span>
          </div>
          <span
            :class="[
              'text-[10px] font-mono font-bold px-2 py-0.5 rounded-full tabular-nums',
              currentAdminTab === 'users'
                ? 'bg-white/20 text-white dark:bg-slate-900/20 dark:text-slate-900'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200/60 dark:bg-emerald-500/15 dark:text-emerald-400'
            ]"
          >
            {{ usersCount }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Sidebar Bottom: Theme Switcher & Lock -->
    <div class="space-y-3 pt-4 border-t border-slate-200/80 dark:border-slate-800/80">
      <!-- Theme Switcher -->
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

      <!-- Lock Session Button -->
      <button
        @click="emit('lock-session')"
        :class="[
          'w-full p-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 border',
          darkMode
            ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
            : 'bg-rose-50 border-rose-200 text-rose-600 hover:bg-rose-100'
        ]"
      >
        <Lock class="w-3.5 h-3.5" />
        <span>Lock Admin Session</span>
      </button>
    </div>
  </aside>
</template>
