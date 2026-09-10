<script setup>
import { computed } from 'vue'

const props = defineProps({
  mode: {
    type: String,
    default: 'full' // 'full' | 'icon'
  },
  darkMode: {
    type: Boolean,
    default: null // Auto-resolves from useAppTheme if not provided
  },
  sizeClass: {
    type: String,
    default: 'h-10'
  },
  showTagline: {
    type: Boolean,
    default: true
  }
})

// Auto-resolve theme if not explicitly passed
const { isDark: themeDark } = useAppTheme()
const isDarkEffective = computed(() => {
  if (props.darkMode !== null) return props.darkMode
  return themeDark.value
})

// Unique gradient IDs so multiple SVG logos on a page do not conflict
const uid = Math.random().toString(36).substring(2, 7)
const waveGradId = `wave-grad-${uid}`
const wqGradId = `wq-grad-${uid}`
</script>

<template>
  <div :class="['inline-flex items-center shrink-0 select-none', sizeClass]">
    <!-- 1. ICON ONLY MODE (Aspect Square 100x100) -->
    <svg
      v-if="mode === 'icon'"
      viewBox="10 10 100 100"
      class="h-full w-auto aspect-square overflow-visible"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient :id="wqGradId" x1="16" y1="16" x2="104" y2="104" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38BDF8"/>
          <stop offset="50%" stop-color="#0284C7"/>
          <stop offset="100%" stop-color="#0F172A"/>
        </linearGradient>
        <linearGradient :id="waveGradId" x1="45" y1="45" x2="75" y2="75" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38BDF8"/>
          <stop offset="100%" stop-color="#2DD4BF"/>
        </linearGradient>
      </defs>

      <g>
        <rect x="10" y="10" width="100" height="100" rx="28" fill="#191D24"/>
        
        <path d="M 38 52 A 26 26 0 0 1 82 52" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round"/>
        
        <path d="M 84 68 A 26 26 0 0 1 40 72" stroke="#0284C7" stroke-width="6.5" stroke-linecap="round"/>
        
        <path d="M 78 78 L 92 92" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round"/>

        <circle cx="92" cy="60" r="3.5" fill="#2DD4BF"/>
        
        <path d="M 50 60 C 54 54, 58 54, 62 60 C 66 66, 70 66, 74 60" :stroke="`url(#${waveGradId})`" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M 52 68 C 56 64, 59 64, 62 68 C 65 72, 68 72, 72 68" stroke="#38BDF8" stroke-width="3" stroke-linecap="round" opacity="0.7"/>
      </g>
    </svg>

    <!-- 2. FULL LOGO + TYPOGRAPHY MODE (440x120) -->
    <svg
      v-else
      viewBox="0 0 440 120"
      class="h-full w-auto max-w-full overflow-visible"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient :id="wqGradId" x1="16" y1="16" x2="104" y2="104" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38BDF8"/>
          <stop offset="50%" stop-color="#0284C7"/>
          <stop offset="100%" stop-color="#0F172A"/>
        </linearGradient>
        <linearGradient :id="waveGradId" x1="45" y1="45" x2="75" y2="75" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#38BDF8"/>
          <stop offset="100%" stop-color="#2DD4BF"/>
        </linearGradient>
      </defs>

      <!-- Washer Drum Icon Mark -->
      <g transform="translate(10, 10)">
        <rect x="0" y="0" width="100" height="100" rx="28" fill="#191D24"/>
        
        <path d="M 28 42 A 26 26 0 0 1 72 42" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round"/>
        
        <path d="M 74 58 A 26 26 0 0 1 30 62" stroke="#0284C7" stroke-width="6.5" stroke-linecap="round"/>
        
        <path d="M 68 68 L 82 82" stroke="#38BDF8" stroke-width="6.5" stroke-linecap="round"/>

        <circle cx="82" cy="50" r="3.5" fill="#2DD4BF"/>
        
        <path d="M 40 50 C 44 44, 48 44, 52 50 C 56 56, 60 56, 64 50" :stroke="`url(#${waveGradId})`" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M 42 58 C 46 54, 49 54, 52 58 C 55 62, 58 62, 62 58" stroke="#38BDF8" stroke-width="3" stroke-linecap="round" opacity="0.7"/>
      </g>

      <!-- Wordmark Typography -->
      <g transform="translate(130, 42)">
        <!-- Dynamic Adaptive 'Wash' text fill -->
        <text
          x="0"
          y="28"
          font-family="'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif"
          font-size="34"
          font-weight="800"
          :fill="isDarkEffective ? '#FFFFFF' : '#191D24'"
          letter-spacing="-1"
        >Wash</text>
        
        <!-- Sky Blue 'Queue' text fill -->
        <text
          x="86"
          y="28"
          font-family="'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif"
          font-size="34"
          font-weight="800"
          fill="#0284C7"
          letter-spacing="-1"
        >Queue</text>
        
        <!-- Subtitle Tagline -->
        <text
          v-if="showTagline"
          x="2"
          y="48"
          font-family="'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif"
          font-size="11"
          font-weight="700"
          fill="#94A3B8"
          letter-spacing="1.8"
        >HOSTEL LAUNDRY IOT</text>
      </g>
    </svg>
  </div>
</template>
