<script setup>
import { ref, computed, watch } from 'vue'
import { X, QrCode, RefreshCw, Copy, Check, ShieldCheck, Sparkles, Building2, School } from 'lucide-vue-next'
import QRCode from 'qrcode'
import AppLogo from '~/components/common/AppLogo.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  qrUrl: {
    type: String,
    default: ''
  },
  secondsRemaining: {
    type: Number,
    default: 60
  },
  hostelId: {
    type: String,
    default: 'block-b'
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'refresh-now'])

const { institutionName, hostelName } = useHostelBranding()

const qrSvg = ref('')
const copied = ref(false)
let copyTimer = null

const generateQr = async () => {
  if (!props.qrUrl) return
  try {
    qrSvg.value = await QRCode.toString(props.qrUrl, {
      type: 'svg',
      margin: 1,
      color: {
        dark: props.darkMode ? '#ffffff' : '#0f172a',
        light: '#00000000'
      }
    })
  } catch (err) {
    console.error('QR code render error:', err)
  }
}

watch(() => [props.qrUrl, props.darkMode], generateQr, { immediate: true })

const handleCopyLink = async () => {
  if (!props.qrUrl) return
  try {
    await navigator.clipboard.writeText(props.qrUrl)
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {}
}

const progressPercent = computed(() => {
  return Math.min(100, Math.max(0, (props.secondsRemaining / 60) * 100))
})
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-fadeIn"
    @click.self="emit('close')"
  >
    <div
      :class="[
        'w-full max-w-xl rounded-[36px] p-6 sm:p-10 border shadow-2xl transition-all relative overflow-hidden text-center flex flex-col items-center',
        darkMode ? 'bg-[#0e121a] border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
      ]"
    >
      <!-- Close / Exit Kiosk Button -->
      <button
        @click="emit('close')"
        class="absolute top-6 right-6 w-10 h-10 rounded-full border border-slate-200 dark:border-slate-800 flex items-center justify-center text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all active:scale-95 cursor-pointer"
        title="Exit Kiosk Mode"
      >
        <X class="w-5 h-5" />
      </button>

      <!-- Hostel Crest & Top Header -->
      <div class="flex items-center gap-2 mb-2 px-3 py-1 rounded-full border text-[11px] font-mono font-bold" :class="darkMode ? 'bg-sky-500/10 border-sky-500/20 text-sky-400' : 'bg-sky-50 border-sky-200 text-sky-700'">
        <ShieldCheck class="w-3.5 h-3.5" />
        <span>OFFICIAL HOSTEL ONBOARDING KIOSK</span>
      </div>

      <h2 class="text-xl sm:text-2xl font-black tracking-tight">
        {{ hostelName }}
      </h2>
      <p class="text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400 mt-0.5">
        {{ institutionName }} • Laundry Registration
      </p>

      <!-- Instruction Pill -->
      <div class="mt-5 mb-4 px-4 py-2 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-xs font-semibold flex items-center gap-2">
        <Sparkles class="w-4 h-4 shrink-0" />
        <span>Scan with your phone camera to register your room</span>
      </div>

      <!-- Vector QR Code Container with High Contrast Framing -->
      <div class="p-5 rounded-3xl border shadow-inner my-2 relative" :class="darkMode ? 'bg-[#141923] border-slate-700/80' : 'bg-slate-50 border-slate-200'">
        <div 
          v-if="qrSvg"
          v-html="qrSvg" 
          class="w-60 h-60 sm:w-68 sm:h-68 flex items-center justify-center [&>svg]:w-full [&>svg]:h-full"
        />
        <div v-else class="w-60 h-60 flex items-center justify-center">
          <RefreshCw class="w-8 h-8 animate-spin text-slate-400" />
        </div>
      </div>

      <!-- 60-Second Rotation Progress Ring / Bar -->
      <div class="w-full max-w-xs my-4 space-y-2">
        <div class="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
          <div
            class="bg-gradient-to-r from-amber-500 to-rose-500 h-full rounded-full transition-all duration-1000 ease-linear"
            :style="{ width: `${progressPercent}%` }"
          />
        </div>
        <div class="flex items-center justify-between text-xs font-mono font-bold">
          <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Code expires in:</span>
          <span class="text-amber-500 tabular-nums">{{ secondsRemaining }}s</span>
        </div>
      </div>

      <!-- Security Notice -->
      <p class="text-[11px] font-mono text-slate-400 dark:text-slate-500 max-w-sm leading-relaxed mb-4">
        This QR code rotates every 60 seconds. Once scanned, residents receive a 5-minute session to complete their room registration.
      </p>

      <!-- Bottom Controls: Manual Refresh & Link Copy -->
      <div class="flex items-center gap-2.5">
        <button
          @click="emit('refresh-now')"
          class="px-3.5 py-1.5 rounded-xl border text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95"
          :class="darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          <span>Rotate Now</span>
        </button>

        <button
          @click="handleCopyLink"
          class="px-3.5 py-1.5 rounded-xl border text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95"
          :class="copied ? 'bg-emerald-500 text-white border-emerald-600' : (darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white' : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200')"
        >
          <Check v-if="copied" class="w-3.5 h-3.5" />
          <Copy v-else class="w-3.5 h-3.5" />
          <span>{{ copied ? 'Link Copied!' : 'Copy Direct Link' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
