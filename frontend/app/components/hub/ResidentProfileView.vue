<script setup>
import { Info } from 'lucide-vue-next'

const props = defineProps({
  myMachine: {
    type: Object,
    required: true
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})
</script>

<template>
  <div class="space-y-6 animate-fadeIn max-w-2xl">
    <!-- Profile Card -->
    <div
      :class="[
        'p-8 rounded-[28px] border text-center',
        darkMode ? 'bg-[#151921] border-slate-800' : 'bg-white border-slate-200/80 shadow-xs'
      ]"
    >
      <img
        src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=160&h=160&fit=crop&crop=faces"
        class="w-24 h-24 rounded-full mx-auto object-cover ring-4 ring-slate-100 dark:ring-slate-700 mb-3"
        alt="Avatar"
      />
      <h3 class="font-black text-2xl text-slate-900 dark:text-white">Akshat Dhaundiyal</h3>
      <p class="text-xs sm:text-sm text-slate-500 dark:text-slate-400 font-medium mt-0.5">
        Room 214 • Block B Resident
      </p>

      <div class="grid grid-cols-2 gap-3 mt-6">
        <div :class="['p-4 rounded-2xl border', darkMode ? 'bg-slate-800/40 border-slate-700' : 'bg-slate-50 border-slate-200/80']">
          <span class="text-[11px] text-slate-500 dark:text-slate-400 block font-medium">Active Machine Link</span>
          <span class="text-base font-bold font-mono text-slate-900 dark:text-white mt-0.5 block">
            {{ myMachine.claimed ? myMachine.id : 'None' }}
          </span>
        </div>
        <div :class="['p-4 rounded-2xl border', darkMode ? 'bg-slate-800/40 border-slate-700' : 'bg-slate-50 border-slate-200/80']">
          <span class="text-[11px] text-slate-500 dark:text-slate-400 block font-medium">IoT Sensor Status</span>
          <span class="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-0.5 block">Connected ✓</span>
        </div>
      </div>
    </div>

    <!-- Protocol Rules -->
    <div
      :class="[
        'p-6 sm:p-7 rounded-[28px] border space-y-3 text-xs sm:text-sm',
        darkMode ? 'bg-[#151921] border-slate-800 text-slate-300' : 'bg-white border-slate-200/80 text-slate-600 shadow-xs'
      ]"
    >
      <div class="font-bold text-slate-900 dark:text-white flex items-center gap-2 text-base">
        <Info class="w-4 h-4 text-sky-600 dark:text-sky-400" />
        <span>Hostel Laundry Protocol</span>
      </div>
      <p class="leading-relaxed font-normal">
        1. Please unload your clothes within 15 minutes of motor power shutdown (0W draw).
      </p>
      <p class="leading-relaxed font-normal">
        2. If uncollected over 30 minutes, other residents may carefully place laundry into the clean plastic baskets on Shelf #2.
      </p>
      <p class="leading-relaxed font-normal">
        3. Use the inline "Buzz to Empty" button on the Appliances screen before touching unattended clothes.
      </p>
    </div>
  </div>
</template>
