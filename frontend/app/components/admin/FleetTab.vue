<script setup>
const props = defineProps({
  machines: {
    type: Array,
    default: () => []
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['check-overdue', 'force-clear'])
</script>

<template>
  <section class="space-y-6 animate-fadeIn">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-lg font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
          FLEET_MANAGEMENT // AUDIT_AND_CONTROLS
        </h2>
        <p class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Unmasked student bookings, live waitlist queues, and manual hardware overrides.
        </p>
      </div>

      <button 
        @click="emit('check-overdue')"
        class="px-4 py-2 bg-amber-500/15 border border-amber-500/40 text-amber-500 hover:bg-amber-500/25 font-mono font-bold text-xs rounded-xl transition flex items-center gap-2 active:scale-95"
        title="Scan all active machines and shift overdue cycles to idle_full"
      >
        <span>⚡ Check Overdue Cycles</span>
      </button>
    </div>

    <!-- Machines Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
      <div 
        v-for="machine in machines" 
        :key="machine.id"
        class="rounded-3xl p-5 border flex flex-col justify-between transition-all"
        :class="darkMode ? 'bg-[#121824] border-white/10 shadow-lg' : 'bg-white border-slate-200 shadow-xs'"
      >
        <div>
          <div class="flex items-center justify-between mb-3">
            <span class="font-mono font-extrabold text-sm" :class="darkMode ? 'text-white' : 'text-slate-900'">
              {{ machine.name }}
            </span>
            <span 
              class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border"
              :class="{
                'bg-emerald-500/20 text-emerald-500 border-emerald-500/30': machine.status === 'available',
                'bg-rose-500/20 text-rose-400 border-rose-500/30': machine.status === 'in_use',
                'bg-amber-500/20 text-amber-300 border-amber-500/30': machine.status === 'idle_full'
              }"
            >
              {{ machine.status }}
            </span>
          </div>

          <!-- Active Student Booking Details (Unmasked for Hostel Admin) -->
          <div class="p-3.5 rounded-2xl border mb-3 text-xs font-mono" :class="darkMode ? 'bg-[#0a0e17] border-white/5' : 'bg-slate-50 border-slate-200'">
            <div v-if="machine.active_booking" class="space-y-1">
              <div class="flex items-center justify-between">
                <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Resident:</span>
                <span class="font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">{{ machine.active_booking.user_name }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Room:</span>
                <span class="font-bold text-sky-500">{{ machine.active_booking.room_number || 'B-214' }}</span>
              </div>
              <div class="flex items-center justify-between text-[11px]">
                <span :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Started:</span>
                <span :class="darkMode ? 'text-zinc-300' : 'text-slate-600'">{{ new Date(machine.active_booking.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
              </div>
            </div>
            <div v-else class="text-center py-2 italic text-[11px]" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              No active booking
            </div>
          </div>

          <!-- Associated Smart Plug -->
          <div class="mb-3 text-xs font-mono">
            <span class="text-[10px] uppercase block" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Smart Plug Node:</span>
            <span v-if="machine.smart_plug" class="font-bold text-emerald-500 flex items-center gap-1 mt-0.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {{ machine.smart_plug.device_id.slice(0, 10) }}... ({{ machine.smart_plug.ip_address }})
            </span>
            <span v-else class="italic text-[11px]" :class="darkMode ? 'text-zinc-500' : 'text-slate-400'">No smart plug linked</span>
          </div>

          <!-- Queue Waitlist -->
          <div class="border-t pt-3 text-xs font-mono" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
            <span class="text-[10px] uppercase block mb-1" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
              Waitlist Queue ({{ machine.queue?.length || 0 }})
            </span>
            <div v-if="machine.queue && machine.queue.length > 0" class="space-y-1">
              <div v-for="q in machine.queue" :key="q.user_id" class="flex justify-between text-[11px]">
                <span :class="darkMode ? 'text-zinc-300' : 'text-slate-700'">#{{ q.position }} {{ q.user_name }}</span>
                <span class="text-[10px] uppercase" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">{{ q.status }}</span>
              </div>
            </div>
            <p v-else class="text-[11px] italic" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Queue is empty</p>
          </div>
        </div>

        <!-- Force Clear Action Button -->
        <div class="pt-4 border-t mt-4" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
          <button 
            v-if="machine.status !== 'available'"
            @click="emit('force-clear', machine.id)"
            class="w-full py-2 bg-rose-500/15 border border-rose-500/30 text-rose-400 hover:bg-rose-500/25 text-xs font-mono font-bold rounded-xl transition active:scale-95"
          >
            Force Clear Machine
          </button>
          <div v-else class="text-center text-[11px] font-mono text-emerald-500 py-1 font-bold">
            ✓ Ready for Use
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
