<script setup>
import { ref } from 'vue'
import { Lock, KeyRound, Sparkles, ArrowRight, ShieldCheck } from 'lucide-vue-next'

const props = defineProps({
  darkMode: {
    type: Boolean,
    default: false
  },
  pinError: {
    type: String,
    default: ''
  },
  isAuthenticating: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['verify-pin'])
const inputPin = ref('')

const onSubmit = () => {
  emit('verify-pin', inputPin.value)
}

const fillDemoPin = () => {
  inputPin.value = '1234'
}
</script>

<template>
  <div class="min-h-[70vh] flex items-center justify-center p-4 sm:p-6 animate-fadeIn">
    <div 
      class="w-full max-w-md rounded-[32px] border p-6 sm:p-8 transition-all shadow-xl text-center"
      :class="darkMode ? 'bg-[#151921] border-slate-800 shadow-black/40' : 'bg-white border-slate-200/80 shadow-[0_4px_25px_rgba(0,0,0,0.04)]'"
    >
      <div 
        class="w-12 h-12 rounded-2xl mx-auto flex items-center justify-center mb-4 border transition-colors"
        :class="darkMode ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-emerald-50 border-emerald-200/80 text-emerald-600'"
      >
        <Lock class="w-6 h-6" />
      </div>

      <h2 class="text-xl font-black tracking-tight mb-1" :class="darkMode ? 'text-white' : 'text-slate-900'">
        Operator PIN Required
      </h2>
      <p class="text-xs font-normal mb-6" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        Enter the administrative security PIN to unlock real-time IoT calibration, smart plug controls, and database portal.
      </p>

      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <input 
            v-model="inputPin"
            type="password" 
            maxlength="8" 
            placeholder="••••" 
            required
            autofocus
            class="w-full text-center tracking-[0.6em] text-xl font-mono py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-emerald-500/20 transition"
            :class="darkMode ? 'bg-[#0c0e14] border-slate-700/80 text-white placeholder-slate-600 focus:border-emerald-500' : 'bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400 focus:border-emerald-500'"
          />
        </div>

        <p v-if="pinError" class="text-xs text-rose-500 font-medium">{{ pinError }}</p>

        <button 
          type="submit" 
          :disabled="isAuthenticating || !inputPin"
          class="w-full py-3 rounded-xl text-xs font-bold transition-all bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 shadow-md flex items-center justify-center gap-2"
        >
          <ShieldCheck class="w-4 h-4" />
          <span>{{ isAuthenticating ? 'Verifying...' : 'Unlock Operator Console' }}</span>
        </button>
      </form>

      <!-- Demo PIN Button -->
      <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
        <button
          type="button"
          @click="fillDemoPin"
          class="font-semibold text-emerald-600 dark:text-emerald-400 hover:underline inline-flex items-center gap-1"
        >
          <Sparkles class="w-3.5 h-3.5 text-amber-500" />
          <span>Fill Demo PIN (1234)</span>
        </button>

        <NuxtLink
          to="/login"
          class="font-medium text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 inline-flex items-center gap-1"
        >
          <span>Common Login</span>
          <ArrowRight class="w-3 h-3" />
        </NuxtLink>
      </div>
    </div>
  </div>
</template>
