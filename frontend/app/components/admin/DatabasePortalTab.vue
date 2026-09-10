<script setup>
import { ref } from 'vue'
import { RefreshCw, Download } from 'lucide-vue-next'

const props = defineProps({
  dbTarget: {
    type: String,
    default: 'local'
  },
  dbStatus: {
    type: Object,
    default: () => ({ connected: true, dialect: 'sqlite', tables: [], error: null })
  },
  selectedTable: {
    type: String,
    default: 'machines'
  },
  tableData: {
    type: Object,
    default: () => ({ total: 0, limit: 25, offset: 0, columns: [], rows: [] })
  },
  tableLoading: {
    type: Boolean,
    default: false
  },
  queryResult: {
    type: Object,
    default: null
  },
  queryLoading: {
    type: Boolean,
    default: false
  },
  queryError: {
    type: String,
    default: ''
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'switch-target',
  'refresh-status',
  'select-table',
  'run-query',
  'export-json'
])

const localSqlQuery = ref('SELECT * FROM machines LIMIT 10;')

const setQueryTemplate = (sql) => {
  localSqlQuery.value = sql
  emit('run-query', sql)
}

const onRunQueryClick = () => {
  emit('run-query', localSqlQuery.value)
}
</script>

<template>
  <section class="space-y-6 animate-fadeIn">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">
            DATABASE_PORTAL // DUAL_STORAGE_EXPLORER
          </h2>
          <span 
            class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border flex items-center gap-1.5"
            :class="dbStatus.connected ? 'bg-emerald-500/20 text-emerald-500 border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="dbStatus.connected ? 'bg-emerald-500' : 'bg-amber-400'"></span>
            {{ dbStatus.connected ? `${dbTarget.toUpperCase()} ONLINE (${dbStatus.dialect})` : 'UNCONFIGURED' }}
          </span>
        </div>
        <p class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Direct read-only inspection and SQL query console for Local Edge (SQLite) and Cloud Database (Supabase PostgreSQL).
        </p>
      </div>

      <!-- Target Database Switcher & Controls -->
      <div class="flex items-center gap-2">
        <div class="inline-flex p-1 rounded-xl border" :class="darkMode ? 'bg-[#0a0e17] border-white/10' : 'bg-slate-100 border-slate-200'">
          <button
            @click="emit('switch-target', 'local')"
            class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95"
            :class="dbTarget === 'local' ? 'bg-[#10b981] text-[#003824] shadow-sm' : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')"
          >
            🖥️ Local (SQLite)
          </button>
          <button
            @click="emit('switch-target', 'cloud')"
            class="px-3.5 py-1.5 rounded-lg text-xs font-mono font-bold transition flex items-center gap-1.5 active:scale-95"
            :class="dbTarget === 'cloud' ? 'bg-indigo-500 text-white shadow-sm' : (darkMode ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900')"
          >
            ☁️ Cloud (Supabase)
          </button>
        </div>

        <button
          @click="emit('refresh-status', dbTarget)"
          class="p-2 rounded-xl border text-xs font-mono transition active:scale-95"
          :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'"
          title="Refresh Tables"
        >
          <RefreshCw class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Connection Error Warning (if Cloud is not configured) -->
    <div v-if="!dbStatus.connected && dbStatus.error" class="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-600 dark:text-amber-200 text-xs font-mono space-y-1">
      <div class="font-bold flex items-center gap-2">
        <span>⚠️ Database Target Offline / Not Configured</span>
      </div>
      <p class="text-[11px] opacity-90">{{ dbStatus.error }}</p>
      <p class="text-[10px] pt-1" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
        Tip: Set <code class="font-bold">CLOUD_DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres</code> in <code class="font-bold">backend/.env</code> to query your cloud database.
      </p>
    </div>

    <!-- Table Navigation Pills & Row Counts -->
    <div class="rounded-3xl p-5 border space-y-3" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
      <div class="flex items-center justify-between">
        <span class="text-xs font-mono font-bold uppercase tracking-wider" :class="darkMode ? 'text-white' : 'text-slate-900'">
          Discovered Tables ({{ dbStatus.tables?.length || 0 }})
        </span>
        <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Click a table to inspect records</span>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-for="tbl in dbStatus.tables"
          :key="tbl.name"
          @click="emit('select-table', tbl.name, 0)"
          class="px-3 py-1.5 rounded-xl text-xs font-mono font-bold border transition flex items-center gap-2 active:scale-95"
          :class="selectedTable === tbl.name ? (darkMode ? 'bg-white/10 text-white border-[#10b981]' : 'bg-slate-900 text-white border-slate-900') : (darkMode ? 'bg-[#0a0e17] text-slate-400 border-white/5 hover:border-white/20' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200')"
        >
          <span>📄 {{ tbl.name }}</span>
          <span 
            class="px-1.5 py-0.2 rounded-full text-[10px] font-mono"
            :class="selectedTable === tbl.name ? 'bg-[#10b981] text-[#003824] font-bold' : 'bg-emerald-500/15 text-emerald-500'"
          >
            {{ tbl.row_count }}
          </span>
        </button>
      </div>
    </div>

    <!-- Table Data Viewer Grid -->
    <div class="rounded-3xl p-5 border space-y-4" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center gap-2">
          <span class="text-sm font-mono font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">Table: {{ selectedTable }}</span>
          <span class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">({{ tableData.total }} total rows)</span>
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="tableData.offset <= 0 || tableLoading"
            @click="emit('select-table', selectedTable, Math.max(0, tableData.offset - tableData.limit))"
            class="px-2.5 py-1 rounded-lg text-xs font-mono border disabled:opacity-30 transition"
            :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'"
          >
            ◀ Prev
          </button>
          <span class="text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            {{ tableData.offset + 1 }} - {{ Math.min(tableData.total, tableData.offset + tableData.limit) }}
          </span>
          <button
            :disabled="tableData.offset + tableData.limit >= tableData.total || tableLoading"
            @click="emit('select-table', selectedTable, tableData.offset + tableData.limit)"
            class="px-2.5 py-1 rounded-lg text-xs font-mono border disabled:opacity-30 transition"
            :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'"
          >
            Next ▶
          </button>
        </div>
      </div>

      <!-- Table Container with horizontal scroll -->
      <div 
        class="overflow-x-auto max-h-[380px] rounded-2xl border transition-colors"
        :class="darkMode ? 'bg-[#0a0e17] border-white/10 text-white' : 'bg-white border-slate-200 text-slate-900 shadow-2xs'"
      >
        <table v-if="tableData.rows && tableData.rows.length > 0" class="w-full text-left font-mono text-xs">
          <thead 
            class="uppercase text-[10px] sticky top-0 border-b"
            :class="darkMode ? 'bg-[#121824] text-slate-400 border-white/10' : 'bg-slate-100 text-slate-600 border-slate-200'"
          >
            <tr>
              <th v-for="col in tableData.columns" :key="col" class="px-3.5 py-2.5 whitespace-nowrap font-bold">
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y" :class="darkMode ? 'divide-white/5' : 'divide-slate-100'">
            <tr v-for="(row, rIdx) in tableData.rows" :key="rIdx" :class="darkMode ? 'hover:bg-white/[0.03]' : 'hover:bg-slate-50'" class="transition">
              <td v-for="col in tableData.columns" :key="col" class="px-3.5 py-2 whitespace-nowrap max-w-xs truncate" :class="darkMode ? 'text-zinc-300' : 'text-slate-700'">
                <span v-if="row[col] === null" :class="darkMode ? 'text-zinc-600' : 'text-slate-400'" class="italic">NULL</span>
                <span v-else-if="typeof row[col] === 'boolean'" class="px-1.5 py-0.2 rounded text-[10px]" :class="row[col] ? 'bg-emerald-500/20 text-emerald-500' : 'bg-rose-500/20 text-rose-500'">
                  {{ row[col] ? 'TRUE' : 'FALSE' }}
                </span>
                <span v-else>{{ row[col] }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else-if="tableLoading" class="p-8 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          Loading table data...
        </div>
        <div v-else class="p-8 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          No records found in table '{{ selectedTable }}'.
        </div>
      </div>
    </div>

    <!-- Interactive SQL Console -->
    <div class="rounded-3xl p-5 border space-y-4" :class="darkMode ? 'bg-[#121824] border-white/10' : 'bg-white border-slate-200 shadow-xs'">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div>
          <h3 class="text-sm font-mono font-bold uppercase flex items-center gap-2" :class="darkMode ? 'text-white' : 'text-slate-900'">
            <span>⚡ Interactive SQL Query Console</span>
            <span class="text-[10px] font-normal px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-500 border border-emerald-500/30">
              Read-Only Safe
            </span>
          </h3>
          <p class="text-[11px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Execute custom queries directly against {{ dbTarget === 'local' ? 'Local SQLite (washqueue.db)' : 'Cloud PostgreSQL' }}.
          </p>
        </div>

        <!-- Quick Template Chips -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">Presets:</span>
          <button 
            @click="setQueryTemplate('SELECT * FROM smart_plugs;')"
            class="text-[10px] font-mono px-2 py-1 rounded border transition"
            :class="darkMode ? 'bg-[#0a0e17] text-slate-400 hover:text-white border-white/10' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200'"
          >
            smart_plugs
          </button>
          <button 
            @click="setQueryTemplate('SELECT * FROM telemetry_readings ORDER BY recorded_at DESC LIMIT 20;')"
            class="text-[10px] font-mono px-2 py-1 rounded border transition"
            :class="darkMode ? 'bg-[#0a0e17] text-slate-400 hover:text-white border-white/10' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200'"
          >
            telemetry (20)
          </button>
          <button 
            @click="setQueryTemplate('SELECT * FROM machines;')"
            class="text-[10px] font-mono px-2 py-1 rounded border transition"
            :class="darkMode ? 'bg-[#0a0e17] text-slate-400 hover:text-white border-white/10' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200'"
          >
            machines
          </button>
          <button 
            @click="setQueryTemplate('SELECT * FROM users;')"
            class="text-[10px] font-mono px-2 py-1 rounded border transition"
            :class="darkMode ? 'bg-[#0a0e17] text-slate-400 hover:text-white border-white/10' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200'"
          >
            users
          </button>
        </div>
      </div>

      <!-- Query Input Area -->
      <div class="relative">
        <textarea
          v-model="localSqlQuery"
          rows="3"
          placeholder="SELECT * FROM machines WHERE status = 'available';"
          class="w-full bg-[#070a10] border border-white/15 rounded-2xl p-3 text-emerald-400 font-mono text-xs focus:outline-none focus:border-[#10b981] placeholder-zinc-600 shadow-inner"
        ></textarea>
        <div class="flex items-center justify-between mt-2">
          <span class="text-[10px] font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Allowed: <code class="text-emerald-500">SELECT</code>, <code class="text-emerald-500">WITH</code>, <code class="text-emerald-500">PRAGMA</code>, <code class="text-emerald-500">EXPLAIN</code>
          </span>
          <div class="flex items-center gap-2">
            <button
              v-if="queryResult?.rows?.length"
              @click="emit('export-json')"
              class="px-3 py-1.5 rounded-xl text-xs font-mono font-bold border transition flex items-center gap-1.5"
              :class="darkMode ? 'bg-[#181b25] text-white border-white/10 hover:bg-[#262a34]' : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
            <button
              @click="onRunQueryClick"
              :disabled="queryLoading"
              class="px-4 py-1.5 bg-[#10b981] hover:bg-[#4edea3] text-[#003824] rounded-xl text-xs font-mono font-bold transition uppercase flex items-center gap-1.5 active:scale-95 shadow-sm"
            >
              <span v-if="queryLoading">Executing...</span>
              <span v-else>▶ Run Query</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Query Error Message -->
      <div v-if="queryError" class="p-3.5 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-500 text-xs font-mono">
        <strong>Query Error:</strong> {{ queryError }}
      </div>

      <!-- Query Results Grid -->
      <div v-if="queryResult" class="space-y-2 pt-2 border-t" :class="darkMode ? 'border-white/10' : 'border-slate-100'">
        <div class="flex items-center justify-between text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
          <span class="font-bold" :class="darkMode ? 'text-white' : 'text-slate-900'">Query Results ({{ queryResult.row_count }} rows)</span>
          <span class="px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-500">
            ⏱️ {{ queryResult.execution_time_ms }} ms
          </span>
        </div>

        <div 
          class="overflow-x-auto max-h-[300px] rounded-2xl border transition-colors"
          :class="darkMode ? 'border-white/10 bg-[#070a10] text-white' : 'border-slate-200 bg-white text-slate-900 shadow-2xs'"
        >
          <table v-if="queryResult.rows && queryResult.rows.length > 0" class="w-full text-left font-mono text-xs">
            <thead 
              class="uppercase text-[10px] sticky top-0 border-b"
              :class="darkMode ? 'bg-[#10141d] text-slate-400 border-white/10' : 'bg-slate-100 text-slate-600 border-slate-200'"
            >
              <tr>
                <th v-for="col in queryResult.columns" :key="col" class="px-3.5 py-2 whitespace-nowrap font-bold">
                  {{ col }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y" :class="darkMode ? 'divide-white/5' : 'divide-slate-100'">
              <tr v-for="(row, rIdx) in queryResult.rows" :key="rIdx" :class="darkMode ? 'hover:bg-white/[0.03]' : 'hover:bg-slate-50'" class="transition">
                <td v-for="col in queryResult.columns" :key="col" class="px-3.5 py-1.5 whitespace-nowrap max-w-xs truncate" :class="darkMode ? 'text-zinc-300' : 'text-slate-700'">
                  <span v-if="row[col] === null" :class="darkMode ? 'text-zinc-600' : 'text-slate-400'" class="italic">NULL</span>
                  <span v-else-if="typeof row[col] === 'boolean'" class="px-1.5 py-0.2 rounded text-[10px]" :class="row[col] ? 'bg-emerald-500/20 text-emerald-500' : 'bg-rose-500/20 text-rose-500'">
                    {{ row[col] ? 'TRUE' : 'FALSE' }}
                  </span>
                  <span v-else>{{ row[col] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="p-6 text-center text-xs font-mono" :class="darkMode ? 'text-slate-400' : 'text-slate-500'">
            Query executed successfully. 0 rows returned.
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
