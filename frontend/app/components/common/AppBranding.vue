<script setup>
import { Building2, School } from 'lucide-vue-next'
import AppLogo from '~/components/common/AppLogo.vue'

const props = defineProps({
  logoMode: {
    type: String,
    default: 'icon' // 'full' | 'icon'
  },
  showOrg: {
    type: Boolean,
    default: true
  },
  showHostel: {
    type: Boolean,
    default: true
  },
  compact: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const { institutionName, institutionShort, institutionLogo, hostelName, hostelLogo, hubLocation } = useHostelBranding()
</script>

<template>
  <div class="flex items-center gap-3">
    <!-- 1. WashQueue Logo (Icon or Full) -->
    <div class="shrink-0">
      <AppLogo
        :mode="logoMode"
        :dark-mode="darkMode"
        :size-class="compact ? 'h-8' : 'h-10'"
      />
    </div>

    <!-- 2. Vertical Divider & University/Org + Hostel Name -->
    <div
      v-if="showOrg || showHostel"
      class="flex items-center gap-3 border-l pl-3 transition-colors"
      :class="darkMode ? 'border-slate-800' : 'border-slate-200'"
    >
      <div class="flex items-center gap-2 min-w-0">
        <!-- Optional University / Org Logo or Icon Badge -->
        <div
          v-if="showOrg"
          class="w-7 h-7 rounded-lg shrink-0 flex items-center justify-center overflow-hidden"
          :class="darkMode ? 'bg-slate-800 text-sky-400 border border-slate-700' : 'bg-slate-100 text-sky-600 border border-slate-200/80 shadow-2xs'"
        >
          <img
            v-if="institutionLogo"
            :src="institutionLogo"
            alt="Org Logo"
            class="w-full h-full object-cover"
          />
          <School v-else class="w-4 h-4" />
        </div>

        <!-- Text Stack: Org Name, then Hostel Name -->
        <div class="min-w-0 flex flex-col justify-center">
          <!-- University / Organization Name -->
          <span
            v-if="showOrg"
            :class="[
              'font-extrabold tracking-tight truncate leading-tight',
              compact ? 'text-xs text-slate-800 dark:text-slate-200' : 'text-xs sm:text-sm text-slate-900 dark:text-white'
            ]"
            :title="institutionName"
          >
            {{ compact ? (institutionShort || institutionName) : institutionName }}
          </span>

          <!-- Hostel / Residence Hall Name -->
          <div
            v-if="showHostel"
            class="flex items-center gap-1.5 mt-0.5 text-[10px] sm:text-[11px] font-semibold text-slate-500 dark:text-slate-400 truncate"
          >
            <img
              v-if="hostelLogo"
              :src="hostelLogo"
              alt="Hostel Logo"
              class="w-3.5 h-3.5 rounded object-cover shrink-0"
            />
            <span class="truncate text-sky-600 dark:text-sky-400 font-bold">{{ hostelName }}</span>
            <span v-if="!compact" class="text-slate-300 dark:text-slate-700 shrink-0">•</span>
            <span v-if="!compact" class="truncate hidden lg:inline">{{ hubLocation }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
