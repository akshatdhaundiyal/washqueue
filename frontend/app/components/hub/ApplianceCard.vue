<script setup>
import { Disc, Clock, Check, Plus, Zap, Waves, Sparkles } from 'lucide-vue-next'

const props = defineProps({
  machine: {
    type: Object,
    required: true
  },
  isMyMachine: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['claim', 'buzz', 'select'])
</script>

<template>
  <div
    @click="emit('select', machine)"
    :class="[
      'p-5 rounded-[26px] border transition-all flex flex-col justify-between group hover:scale-[1.01] cursor-pointer',
      isMyMachine
        ? darkMode
          ? 'bg-[#151921] border-sky-500/50 ring-1 ring-sky-500/20 shadow-lg'
          : 'bg-white border-sky-300 shadow-xs ring-1 ring-sky-100'
        : machine.status === 'uncollected'
        ? darkMode
          ? 'bg-[#151921] border-amber-500/50 shadow-sm'
          : 'bg-white border-amber-300 shadow-xs'
        : darkMode
        ? 'bg-[#151921] border-slate-800 hover:border-slate-700'
        : 'bg-white border-slate-200/80 shadow-xs hover:border-slate-300'
    ]"
  >
    <div>
      <!-- Top Row -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-3">
          <div
            :class="[
              'w-11 h-11 rounded-2xl flex items-center justify-center',
              isMyMachine
                ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
                : machine.status === 'uncollected'
                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                : machine.status === 'in-use'
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
            ]"
          >
            <Clock v-if="machine.status === 'uncollected'" class="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <Disc v-else :class="['w-5 h-5', machine.status === 'in-use' ? 'animate-spin text-sky-600 dark:text-sky-400' : '']" />
          </div>
          <div>
            <h4 class="text-xs sm:text-sm font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              {{ machine.name }}
              <span
                v-if="isMyMachine"
                class="text-[9px] px-1.5 py-0.5 rounded-md bg-sky-500 text-white font-extrabold"
              >
                YOUR LOAD
              </span>
            </h4>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">{{ machine.location }}</p>
          </div>
        </div>

        <div class="flex items-center gap-1.5">
          <!-- Status Badge (JetBrains Mono tabular numbers) -->
          <span
            :class="[
              'text-[10px] font-bold uppercase px-2.5 py-1 rounded-full tracking-wider font-mono tabular-nums',
              isMyMachine
                ? 'bg-sky-50 text-sky-700 border border-sky-200/60 dark:bg-sky-500/15 dark:text-sky-400 dark:border-sky-500/20'
                : machine.status === 'uncollected'
                ? 'bg-amber-50 text-amber-700 border border-amber-200/60 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/20'
                : machine.status === 'in-use'
                ? 'bg-slate-100 text-slate-600 border border-slate-200/80 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700'
                : 'bg-emerald-50 text-emerald-700 border border-emerald-200/60 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/20'
            ]"
          >
            <template v-if="isMyMachine">
              {{ machine.runningMinutes }}m ON
            </template>
            <template v-else-if="machine.status === 'uncollected'">
              DONE ({{ machine.finishedAgoMin }}m)
            </template>
            <template v-else-if="machine.status === 'in-use'">
              IN USE
            </template>
            <template v-else>
              AVAILABLE
            </template>
          </span>
        </div>
      </div>

      <!-- Details & Humanized Cycle Stage Display -->
      <div class="my-2.5 text-xs">
        <div v-if="machine.status === 'available'" class="flex items-center justify-between">
          <p class="text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1.5">
            <Sparkles class="w-3.5 h-3.5" /> Ready for immediate wash load
          </p>
        </div>
        <div v-else-if="machine.status === 'in-use'" class="flex flex-col gap-1.5">
          <div class="flex items-center justify-between">
            <span
              class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border"
              :class="machine.stageBadgeClass || 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20'"
            >
              {{ machine.cycleStage || '🌀 Active Washing' }}
            </span>
            <span class="text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono tabular-nums">
              ~{{ machine.remainingMinutes || 30 }}m remaining
            </span>
          </div>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">
            Running for <span class="font-bold text-slate-800 dark:text-slate-200 font-mono tabular-nums">{{ machine.runningMinutes }} mins</span> (standard cycle ~45m)
          </p>
        </div>
        <div v-else-if="machine.status === 'uncollected'" class="flex flex-col gap-1">
          <p class="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1.5">
            <Clock class="w-3.5 h-3.5 shrink-0" />
            <span>Cycle finished <strong class="font-mono font-bold tabular-nums">{{ machine.finishedAgoMin }}m</strong> ago • Clean clothes in drum</span>
          </p>
          <p class="text-[11px] text-slate-500 dark:text-slate-400">
            Send a friendly buzz below to ask the occupant to collect their clothes.
          </p>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
      <span class="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
        <template v-if="machine.status === 'uncollected' && machine.nudgesSent > 0">
          <span class="font-mono font-bold tabular-nums">{{ machine.nudgesSent }}</span> buzzes sent
        </template>
        <template v-else>
          {{ machine.type === 'washer' ? 'Front-Load Washer' : 'Heat-Pump Dryer' }}
        </template>
      </span>

      <!-- Action Buttons (with stop propagation so card tap doesn't fire) -->
      <span
        v-if="isMyMachine"
        class="text-xs font-bold text-sky-600 dark:text-sky-400 flex items-center gap-1"
      >
        <Check class="w-3.5 h-3.5" /> Active on Home
      </span>

      <button
        v-else-if="machine.status === 'available'"
        @click.stop="emit('claim', machine)"
        class="py-2 px-4 rounded-full text-xs font-bold bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xs hover:scale-105 transition-all flex items-center gap-1.5 active:scale-95"
      >
        <Plus class="w-3.5 h-3.5" /> Claim & Book
      </button>

      <button
        v-else-if="machine.status === 'uncollected'"
        @click.stop="emit('buzz', machine.id, machine.name, true)"
        :disabled="machine.myBuzzed"
        :class="[
          'py-1.5 px-3.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95',
          machine.myBuzzed
            ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-default border border-slate-200 dark:border-slate-700'
            : 'bg-amber-50 text-amber-700 border border-amber-300 hover:bg-amber-100 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/30 hover:scale-105'
        ]"
      >
        <Zap class="w-3.5 h-3.5 text-amber-500" />
        {{ machine.myBuzzed ? 'Buzzed ✓' : 'Buzz to Empty' }}
      </button>

      <button
        v-else
        @click.stop="emit('buzz', machine.id, machine.name, false)"
        :disabled="machine.myBuzzed"
        :class="[
          'py-1.5 px-3.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95',
          machine.myBuzzed
            ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-default border border-slate-200 dark:border-slate-700'
            : 'border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
        ]"
      >
        <Zap class="w-3 h-3 text-sky-500" />
        {{ machine.myBuzzed ? 'Buzzed ✓' : 'Send Buzz' }}
      </button>
    </div>
  </div>
</template>
