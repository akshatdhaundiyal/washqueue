<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  editingPlugId: {
    type: String,
    default: null
  },
  initialForm: {
    type: Object,
    default: () => ({
      machine_id: '',
      provider: 'tuya_local',
      device_id: '',
      local_key: '',
      ip_address: '',
      protocol_version: '3.3',
      power_threshold_running: 10.0,
      power_threshold_idle: 5.0,
      debounce_seconds: 120
    })
  },
  machinesList: {
    type: Array,
    default: () => []
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'save'])

const form = ref({ ...props.initialForm })

watch(() => props.initialForm, (newVal) => {
  form.value = { ...newVal }
}, { deep: true, immediate: true })

const onSubmit = () => {
  emit('save', { ...form.value })
}
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
    <div 
      class="rounded-[32px] p-6 max-w-lg w-full space-y-4 border shadow-2xl transition-all animate-fadeIn"
      :class="darkMode ? 'bg-[#121824] border-white/10 text-white' : 'bg-white border-slate-200 text-slate-900'"
    >
      <div class="flex items-center justify-between border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <h3 class="text-sm font-mono font-bold uppercase">
          {{ editingPlugId ? 'EDIT_SMART_PLUG_CONFIG' : 'REGISTER_WIPRO_SMART_PLUG' }}
        </h3>
        <button 
          @click="emit('close')" 
          class="font-mono transition p-1.5 rounded-lg"
          :class="darkMode ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'"
        >✕</button>
      </div>

      <form @submit.prevent="onSubmit" class="space-y-3 font-mono text-xs">
        <div>
          <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Assign to Machine</label>
          <select 
            v-model="form.machine_id" 
            class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
            :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
          >
            <option value="">-- Select Machine --</option>
            <option v-for="m in machinesList" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">IP Address (Local LAN)</label>
            <input 
              v-model="form.ip_address" 
              required 
              placeholder="192.168.1.50" 
              class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
              :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
            />
          </div>
          <div>
            <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Protocol Version</label>
            <select 
              v-model="form.protocol_version" 
              class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
              :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
            >
              <option value="3.3">3.3 (Standard Wipro)</option>
              <option value="3.1">3.1 (Older)</option>
              <option value="3.4">3.4 (Newer Tuya)</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Tuya Device ID</label>
          <input 
            v-model="form.device_id" 
            required 
            placeholder="bf1234567890abcdef" 
            class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
            :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
          />
        </div>

        <div>
          <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Tuya Local Key</label>
          <input 
            v-model="form.local_key" 
            required 
            type="text" 
            placeholder="16-character local key" 
            class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
            :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
          />
        </div>

        <div class="grid grid-cols-3 gap-2">
          <div>
            <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Run (W)</label>
            <input 
              v-model.number="form.power_threshold_running" 
              type="number" 
              step="0.1" 
              class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
              :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
            />
          </div>
          <div>
            <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Idle (W)</label>
            <input 
              v-model.number="form.power_threshold_idle" 
              type="number" 
              step="0.1" 
              class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
              :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
            />
          </div>
          <div>
            <label class="block font-medium mb-1" :class="darkMode ? 'text-slate-300' : 'text-slate-700'">Soak (s)</label>
            <input 
              v-model.number="form.debounce_seconds" 
              type="number" 
              class="w-full rounded-xl p-2.5 border focus:outline-none focus:border-[#10b981]"
              :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
          <button 
            type="button" 
            @click="emit('close')" 
            class="px-4 py-2 rounded-xl font-bold border transition"
            :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'"
          >
            Cancel
          </button>
          <button 
            type="submit" 
            class="px-4 py-2 bg-[#10b981] hover:bg-[#4edea3] text-[#003824] rounded-xl font-bold uppercase transition active:scale-95 shadow-sm"
          >
            Save Plug
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
