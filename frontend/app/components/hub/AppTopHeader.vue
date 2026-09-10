<script setup>
import { Bell, Settings, Sparkle } from 'lucide-vue-next'
import AppBranding from '~/components/common/AppBranding.vue'

const { institutionName, hostelName } = useHostelBranding()

const props = defineProps({
  activeTab: {
    type: String,
    required: true
  },
  myMachine: {
    type: Object,
    required: true
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  formattedDate: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['open-settings', 'view-profile', 'notify-click'])
</script>

<template>
  <div>
    <!-- ======================================================================= -->
    <!-- MOBILE TOP HEADER (md:hidden)                                           -->
    <!-- Logo + Org/Hostel Identity + Notification Bell + Settings + Avatar       -->
    <!-- ======================================================================= -->
    <header
      :class="[
        'md:hidden flex items-center justify-between px-4 py-3 border-b sticky top-0 z-30 transition-colors',
        darkMode ? 'bg-[#10131a]/95 border-slate-800 backdrop-blur-md' : 'bg-white/95 border-slate-200 backdrop-blur-md shadow-xs'
      ]"
    >
      <!-- Logo + University & Hostel Branding -->
      <AppBranding
        :compact="true"
        :dark-mode="darkMode"
        logo-mode="icon"
      />

      <div class="flex items-center gap-2">
        <!-- Notification Bell Button -->
        <button
          @click="emit('notify-click')"
          :class="[
            'w-9 h-9 rounded-full border flex items-center justify-center relative transition-all',
            darkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-white border-slate-200 text-slate-700 shadow-xs'
          ]"
          title="Notifications"
        >
          <Bell class="w-4 h-4" />
          <span
            v-if="myMachine.claimed"
            class="w-2 h-2 rounded-full bg-sky-500 absolute top-2 right-2 animate-ping"
          />
        </button>

        <!-- Settings Button -->
        <button
          @click="emit('open-settings')"
          :class="[
            'w-9 h-9 rounded-full border flex items-center justify-center transition-all',
            darkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-white border-slate-200 text-slate-700 shadow-xs'
          ]"
          title="Settings"
        >
          <Settings class="w-4 h-4" />
        </button>

        <!-- User Avatar: SOLE mobile entry to Profile -->
        <button
          @click="emit('view-profile')"
          class="relative cursor-pointer focus:outline-none rounded-full"
          title="View Resident Profile"
        >
          <img
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop&crop=faces"
            alt="Akshat Profile"
            :class="[
              'w-9 h-9 rounded-full object-cover ring-2 transition-all',
              activeTab === 'profile' ? 'ring-slate-900 dark:ring-white scale-105' : 'ring-slate-200 dark:ring-slate-700'
            ]"
          />
          <span
            :class="[
              'absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-slate-900',
              myMachine.claimed && myMachine.isOn ? 'bg-sky-500 animate-pulse' : 'bg-emerald-500'
            ]"
          />
        </button>
      </div>
    </header>

    <!-- ======================================================================= -->
    <!-- DESKTOP TOP HEADER (hidden md:flex)                                     -->
    <!-- Breadcrumb, live telemetry badge, notifications, settings, avatar       -->
    <!-- ======================================================================= -->
    <header
      :class="[
        'hidden md:flex h-16 border-b shrink-0 items-center justify-between px-6 lg:px-10 sticky top-0 z-20 transition-colors',
        darkMode ? 'bg-[#0c0e14]/90 border-slate-800/80 backdrop-blur-md' : 'bg-[#f6f8fa]/95 border-slate-200/80 backdrop-blur-md'
      ]"
    >
      <!-- Left: Branding, Date, Hub Location, & IoT Telemetry Pill -->
      <div class="flex items-center gap-2.5">
        <span class="text-xs font-extrabold text-slate-800 dark:text-slate-200">
          {{ institutionName }}
        </span>
        <span class="text-slate-300 dark:text-slate-700">•</span>
        <span class="text-xs font-bold text-sky-600 dark:text-sky-400">
          {{ hostelName }}
        </span>
        <span class="text-slate-300 dark:text-slate-700">•</span>
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">
          {{ formattedDate }}
        </span>
        <span class="text-slate-300 dark:text-slate-700">•</span>
        <div class="flex items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-200/80 dark:border-slate-700 shadow-2xs">
          <Sparkle class="w-3.5 h-3.5 text-amber-500" />
          <span>Smart Plug Telemetry Connected</span>
        </div>
      </div>

      <!-- Right: Action Controls -->
      <div class="flex items-center gap-2.5">
        <!-- Notification Bell Button -->
        <button
          @click="emit('notify-click')"
          :class="[
            'w-10 h-10 rounded-full border flex items-center justify-center relative transition-all',
            darkMode
              ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700'
              : 'bg-white border-slate-200 text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900'
          ]"
          title="Notifications & Alerts"
        >
          <Bell class="w-4 h-4" />
          <span
            v-if="myMachine.claimed"
            class="w-2.5 h-2.5 rounded-full bg-sky-500 absolute top-2.5 right-2.5 animate-ping"
          />
        </button>

        <!-- Settings Button -->
        <button
          @click="emit('open-settings')"
          :class="[
            'w-10 h-10 rounded-full border flex items-center justify-center transition-all',
            darkMode
              ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700'
              : 'bg-white border-slate-200 text-slate-700 shadow-xs hover:bg-slate-50 hover:text-slate-900'
          ]"
          title="Preferences & Settings"
        >
          <Settings class="w-4 h-4" />
        </button>

        <!-- Profile Avatar in Header -->
        <button
          @click="emit('view-profile')"
          class="relative cursor-pointer focus:outline-none rounded-full ml-1"
          title="View Profile"
        >
          <img
            src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=120&h=120&fit=crop&crop=faces"
            alt="Akshat Profile"
            :class="[
              'w-10 h-10 rounded-full object-cover ring-2 transition-all',
              activeTab === 'profile' ? 'ring-slate-900 dark:ring-white scale-105' : 'ring-slate-200 dark:ring-slate-700'
            ]"
          />
          <span
            :class="[
              'absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white dark:border-slate-900',
              myMachine.claimed && myMachine.isOn ? 'bg-sky-500 animate-pulse' : 'bg-emerald-500'
            ]"
          />
        </button>
      </div>
    </header>
  </div>
</template>
