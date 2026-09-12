<script setup>
import { computed } from 'vue'
import {
  X,
  Disc,
  Clock,
  Sparkles,
  Zap,
  Users,
  ShieldCheck,
  Check,
  Plus,
  ArrowRight,
  LogOut,
  Bell
} from 'lucide-vue-next'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  machine: {
    type: Object,
    default: null
  },
  isMyMachine: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  },
  currentUser: {
    type: Object,
    default: null
  }
})

const emit = defineEmits([
  'close',
  'claim',
  'buzz',
  'release',
  'join-queue',
  'leave-queue'
])

// Virtual queue calculations
const activeQueue = computed(() => {
  return props.machine?.queue?.filter(q => q.status === 'waiting' || q.status === 'notified') || []
})

const waitingCount = computed(() => activeQueue.value.length)

const myQueueEntry = computed(() => {
  if (!props.currentUser?.id || !props.machine?.queue) return null
  return props.machine.queue.find(
    q => q.user_id === props.currentUser.id && (q.status === 'waiting' || q.status === 'notified')
  )
})

const isUserInQueue = computed(() => !!myQueueEntry.value)
const userQueuePosition = computed(() => myQueueEntry.value?.position || 1)

// Progress calculation (based on ~45min standard wash)
const progressPercent = computed(() => {
  if (props.machine?.status === 'available') return 0
  if (props.machine?.status === 'uncollected') return 100
  const running = props.machine?.runningMinutes || 0
  return Math.min(100, Math.round((running / 45) * 100))
})

const { formatTime, getTimezoneAbbr } = useAppTimezone()

const startedAtFormatted = computed(() => {
  if (props.machine?.active_booking?.started_at) {
    return formatTime(props.machine.active_booking.started_at)
  }
  return null
})

const estimatedFinishTime = computed(() => {
  const rem = props.machine?.remainingMinutes || 30
  return formatTime(new Date(Date.now() + rem * 60 * 1000))
})
</script>

<template>
  <div
    v-if="isOpen && machine"
    class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-xs animate-fadeIn"
    @click.self="emit('close')"
  >
    <div
      :class="[
        'w-full max-w-lg rounded-[32px] p-6 sm:p-7 border shadow-2xl transition-all relative overflow-hidden',
        darkMode
          ? 'bg-[#151921] border-slate-800 text-slate-100'
          : 'bg-white border-slate-200 text-slate-900'
      ]"
    >
      <!-- Top Decorative Accent -->
      <div
        :class="[
          'absolute top-0 left-0 right-0 h-1.5',
          isMyMachine
            ? 'bg-sky-500'
            : machine.status === 'available'
            ? 'bg-emerald-500'
            : machine.status === 'uncollected'
            ? 'bg-amber-500'
            : 'bg-sky-400'
        ]"
      />

      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center gap-3">
          <div
            :class="[
              'w-11 h-11 rounded-2xl flex items-center justify-center',
              isMyMachine
                ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
                : machine.status === 'uncollected'
                ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                : machine.status === 'in-use'
                ? 'bg-sky-500/10 text-sky-600 dark:text-sky-400'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            ]"
          >
            <Clock v-if="machine.status === 'uncollected'" class="w-5 h-5 text-amber-500" />
            <Disc v-else :class="['w-5 h-5', machine.status === 'in-use' ? 'animate-spin text-sky-500' : '']" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-base sm:text-lg font-black tracking-tight text-slate-900 dark:text-white">
                {{ machine.name }}
              </h3>
              <span
                v-if="isMyMachine"
                class="text-[9px] px-2 py-0.5 rounded-full bg-sky-500 text-white font-extrabold uppercase tracking-wide"
              >
                Your Load
              </span>
            </div>
            <p class="text-xs text-slate-500 dark:text-slate-400">
              {{ machine.location }} • {{ machine.type === 'washer' ? 'Front-Load Washer' : 'Heat-Pump Dryer' }}
            </p>
          </div>
        </div>

        <button
          @click="emit('close')"
          :class="[
            'p-2 rounded-full transition-all',
            darkMode ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'
          ]"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Main Status Card -->
      <div class="py-5 space-y-5">
        <!-- 1. Live Cycle Stage & Remaining Time Display -->
        <div
          :class="[
            'p-4 rounded-2xl border flex flex-col gap-3',
            darkMode ? 'bg-slate-900/60 border-slate-800' : 'bg-slate-50 border-slate-200/80'
          ]"
        >
          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Current Cycle Stage
            </span>
            <span
              :class="[
                'text-[11px] font-bold px-3 py-0.5 rounded-full border',
                machine.stageBadgeClass || 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20'
              ]"
            >
              {{ machine.cycleStage || (machine.status === 'available' ? '✨ Ready for Wash' : '🌀 Active Washing') }}
            </span>
          </div>

          <!-- Progress Bar & Elapsed/Remaining Metrics -->
          <div v-if="machine.status === 'in-use'" class="space-y-2">
            <div class="w-full bg-slate-200 dark:bg-slate-700 h-2.5 rounded-full overflow-hidden">
              <div
                class="bg-gradient-to-r from-sky-500 to-indigo-500 h-full rounded-full transition-all duration-500"
                :style="{ width: `${progressPercent}%` }"
              />
            </div>
            <div class="flex items-center justify-between text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono tabular-nums flex-wrap gap-1">
              <span>
                {{ machine.runningMinutes }}m elapsed
                <template v-if="startedAtFormatted"> (Started {{ startedAtFormatted }})</template>
              </span>
              <span class="text-emerald-600 dark:text-emerald-400 font-bold">
                ~{{ machine.remainingMinutes || 30 }}m left (Ready ~{{ estimatedFinishTime }})
              </span>
            </div>
          </div>

          <!-- Finished Uncollected State -->
          <div v-else-if="machine.status === 'uncollected'" class="flex items-center gap-2.5 text-xs text-amber-600 dark:text-amber-400 font-medium">
            <Clock class="w-4 h-4 shrink-0" />
            <span>Cycle completed <strong class="font-mono font-bold">{{ machine.finishedAgoMin }} mins ago</strong>. Clean clothes ready for pickup.</span>
          </div>

          <!-- Available State -->
          <div v-else class="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            <Sparkles class="w-4 h-4 shrink-0" />
            <span>Appliance is idle, clean, and ready for an immediate 45-minute cycle.</span>
          </div>
        </div>

        <!-- 2. Virtual Waitlist / Queue Section (When machine is In-Use) -->
        <div
          v-if="machine.status === 'in-use' && !isMyMachine"
          :class="[
            'p-4 rounded-2xl border flex flex-col gap-3',
            darkMode ? 'bg-slate-900/40 border-slate-800' : 'bg-white border-slate-200'
          ]"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Users class="w-4 h-4 text-sky-500" />
              <h4 class="text-xs font-bold text-slate-900 dark:text-white">
                Virtual Waitlist
              </h4>
            </div>
            <span class="text-xs font-bold text-slate-500 dark:text-slate-400 font-mono tabular-nums">
              {{ waitingCount === 0 ? 'No queue' : `${waitingCount} waiting` }}
            </span>
          </div>

          <!-- If current user is already in line -->
          <div v-if="isUserInQueue" class="p-3 rounded-xl bg-sky-50 dark:bg-sky-500/10 border border-sky-200 dark:border-sky-500/20 flex items-center justify-between gap-3">
            <div>
              <p class="text-xs font-bold text-sky-700 dark:text-sky-300 flex items-center gap-1.5">
                <Check class="w-3.5 h-3.5" /> You are in line!
              </p>
              <p class="text-[11px] text-sky-600 dark:text-sky-400">
                Queue position: <strong class="font-mono font-bold">#{{ userQueuePosition }}</strong>. You'll receive an in-app alert when this machine is free.
              </p>
            </div>
            <button
              @click="emit('leave-queue', machine)"
              class="text-xs font-bold px-3 py-1.5 rounded-full border border-sky-300 dark:border-sky-500/40 text-sky-700 dark:text-sky-300 hover:bg-sky-100 dark:hover:bg-sky-500/20 transition-all shrink-0"
            >
              Leave Queue
            </button>
          </div>

          <!-- If user is NOT in line yet -->
          <div v-else class="flex items-center justify-between gap-3">
            <p class="text-xs text-slate-500 dark:text-slate-400">
              Reserve your spot. You will be notified the second this cycle finishes.
            </p>
            <button
              @click="emit('join-queue', machine)"
              class="text-xs font-bold px-3.5 py-1.5 rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 hover:scale-105 transition-all shrink-0 shadow-xs"
            >
              Join Waitlist
            </button>
          </div>
        </div>

        <!-- 3. Primary Action Buttons -->
        <div class="space-y-2.5 pt-1">
          <!-- Available -> Claim -->
          <button
            v-if="machine.status === 'available'"
            @click="emit('claim', machine)"
            class="w-full py-3.5 px-5 rounded-2xl text-xs sm:text-sm font-bold bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-md hover:scale-[1.01] active:scale-95 transition-all flex items-center justify-center gap-2"
          >
            <Plus class="w-4 h-4" /> Claim & Start 45m Wash Cycle
          </button>

          <!-- My Machine -> Release -->
          <button
            v-else-if="isMyMachine"
            @click="emit('release')"
            class="w-full py-3.5 px-5 rounded-2xl text-xs sm:text-sm font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-md hover:scale-[1.01] active:scale-95 transition-all flex items-center justify-center gap-2"
          >
            <LogOut class="w-4 h-4" /> I've Collected My Clothes (Release)
          </button>

          <!-- In Use -> Send Buzz -->
          <button
            v-else-if="machine.status === 'in-use'"
            @click="emit('buzz', machine.id, machine.name, false)"
            :disabled="machine.myBuzzed"
            :class="[
              'w-full py-3 px-5 rounded-2xl text-xs sm:text-sm font-bold transition-all flex items-center justify-center gap-2',
              machine.myBuzzed
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-default'
                : 'border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
            ]"
          >
            <Zap class="w-4 h-4 text-sky-500" />
            {{ machine.myBuzzed ? 'Buzz Sent to Occupant ✓' : 'Send Gentle Reminder Buzz' }}
          </button>

          <!-- Uncollected -> Send Collection Buzz -->
          <button
            v-else-if="machine.status === 'uncollected'"
            @click="emit('buzz', machine.id, machine.name, true)"
            :disabled="machine.myBuzzed"
            :class="[
              'w-full py-3.5 px-5 rounded-2xl text-xs sm:text-sm font-bold shadow-xs transition-all flex items-center justify-center gap-2',
              machine.myBuzzed
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-default'
                : 'bg-amber-500 hover:bg-amber-600 text-white hover:scale-[1.01] active:scale-95'
            ]"
          >
            <Zap class="w-4 h-4" />
            {{ machine.myBuzzed ? 'Collection Reminder Sent ✓' : 'Buzz Occupant to Collect Clothes 🧺' }}
          </button>
        </div>

        <!-- 4. Hostel Privacy Assurance Badge -->
        <div class="flex items-center gap-2 text-[11px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
          <ShieldCheck class="w-4 h-4 text-emerald-500 shrink-0" />
          <span>All peer buzzes and queue positions are completely anonymous to protect resident privacy.</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.98);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.animate-fadeIn {
  animation: fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
