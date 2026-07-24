<script setup>
import { ref, inject, computed, onMounted, onUnmounted } from 'vue';
import { listLogs, getLog, deleteLog, stopTask, listTasks } from '../api';

const props = defineProps({ initialFilter: { type: Object, default: () => ({ tool: 'all', status: 'all' }) } });
const task = inject('task');

const logs = ref([]);
const loading = ref(true);
const selectedLogId = ref(null);
const logContent = ref(null);
const deleting = ref(new Set());
const stopping = ref(new Set());
const clearingLogs = ref(false);
const exportPath = ref('');
const copied = ref(false);
const copyFailed = ref(false);
const confirmDeleteTarget = ref(null);
const confirmClearAll = ref(false);
const exportDialog = ref(false);
const exportNote = ref('');
const exportNoteError = ref('');
const exportingActive = ref(null);
const exportingLog = ref(null);

const toolOptions = [{ value: 'all', label: '全部类型' },{ value: 'compare', label: '目录比较' },{ value: 'duplicate', label: '目录内查重' }];
const statusOptions = [{ value: 'all', label: '全部状态' },{ value: 'running', label: '运行中' },{ value: 'done', label: '已完成' },{ value: 'stopped', label: '已终止' }];
const toolFilter = ref('all');
const toolOpen = ref(false);
const statusOpen = ref(false);
const statusFilter = ref('all');

const TOOL_LABEL = { compare: '目录比较', duplicate: '目录内查重' };
const TOOL_KEY = { compare: 'compare', duplicate: 'duplicate' };
const RESULT_LABEL = { has_diff: '有差异', ok: '一致', has_dup: '有重复', no_dup: '无重复' };
const MODE_LABEL = { 0: '极速', 1: '推荐', 2: '完整' };



onMounted(() => {
  const f = props.initialFilter || {};
  if (f.tool && f.tool !== 'all') {
    toolFilter.value = f.tool;
  }
  if (f.status) {
    statusFilter.value = f.status;
  }
});

const activeTasks = computed(() => {
  const result = [];
  for (const [tid, t] of Object.entries(task.taskMap || {})) {
    const s = t.status;
    if (s === 'running' || s === 'connecting' || s === 'retrying') {
      result.push({ taskId: tid, ...t });
    }
  }
  return result;
});

const filteredActiveTasks = computed(() => {
  if (toolFilter.value === 'all') return activeTasks.value;
  return activeTasks.value.filter(t => {
    // 从任务参数推断类型
    const url = t.sseUrl || '';
    return t.tool === toolFilter.value;
  });
});

const filteredLogs = computed(() => {
  let list = logs.value;
  if (toolFilter.value !== 'all') {
    list = list.filter(l => l.tool === toolFilter.value);
  }
  if (statusFilter.value === 'running') {
    list = [];
  } else if (statusFilter.value === 'stopped') {
    list = list.filter(l => l.status === 'stopped' || l.exitCode === 143);
  } else if (statusFilter.value === 'done') {
    list = list.filter(l => l.status !== 'stopped' && l.exitCode !== 143);
  }
  return list;
});

function formatTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatArgs(log) {
  const a = log.args || {};
  if (log.tool === 'compare') return `${MODE_LABEL[a.mode] || a.mode} | ${a.dirA} ↔ ${a.dirB}`;
  const parts = [MODE_LABEL[a.mode] || a.mode, a.scanDir];
  if (a.filterKB) parts.push(`≥${a.filterKB}KB`);
  return parts.join(' | ');
}

async function loadLogs() {
  loading.value = true;
  try {
    const data = await listLogs();
    logs.value = data.logs || [];
  } finally {
    loading.value = false;
  }
}

function viewActive(taskId) {
  selectedLogId.value = selectedLogId.value === taskId ? null : taskId;
  logContent.value = null;
}

async function viewLog(log) {
  selectedLogId.value = selectedLogId.value === log.id ? null : log.id;
  logContent.value = null;
  if (selectedLogId.value) {
    const data = await getLog(log.tool, log.filename);
    if (data) logContent.value = data.lines || [];
  }
}

async function handleStop(taskId) {
  stopping.value.add(taskId);
  task.onTaskExit(taskId, () => loadLogs());
  try {
    await stopTask(taskId);
  } catch (e) {
    alert('终止失败: ' + e.message);
  } finally {
    stopping.value.delete(taskId);
  }
}

function showDeleteConfirm(log) {
  confirmDeleteTarget.value = log;
}
async function doDelete() {
  const log = confirmDeleteTarget.value;
  if (!log) return;
  confirmDeleteTarget.value = null;
  deleting.value.add(log.filename);
  try {
    await deleteLog(log.tool, log.filename);
    if (selectedLogId.value === log.id) { selectedLogId.value = null; logContent.value = null; }
    await loadLogs();
  } catch (e) { alert(e.message); }
  finally { deleting.value.delete(log.filename); }
}

function openExportDialog(log) {
  exportDialog.value = true;
  exportNote.value = '';
  exportNoteError.value = '';
  exportingLog.value = log;
}

function formatTimestamp(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function sanitizeNote(note) {
  return note.replace(/[\/.:*?"<>| ]/g, '_').replace(/^_+|_+$/g, '').slice(0, 60);
}

async function doExport() {
  const log = exportingLog.value;
  if (!log) return;
  const content = logContent.value ? logContent.value.map(l => l.text || l).join('\n') : (log.lines || []).map(l => l.text || l).join('\n');
  if (!content) return;

  const tool = TOOL_KEY[log.tool] || log.tool;
  const result = RESULT_LABEL[log.result] || (log.status === 'running' ? '运行中' : '');
  const ts = formatTimestamp(log.timestamp || Date.now());
  let name = `${tool}_${result}_${ts}`;
  const note = exportNote.value.trim();
  if (note) {
    const sn = sanitizeNote(note);
    if (!sn) { exportNoteError.value = '备注包含无效字符'; return; }
    name += '_' + sn;
  }

  exportDialog.value = false;
  exportPath.value = '';
  exportNote.value = '';
  exportNoteError.value = '';
  exportingLog.value = null;

  try {
    const res = await fetch('/app/file-tools/api/export', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, filename: name + '.txt' }),
    });
    const data = await res.json();
    if (data.path) exportPath.value = data.path;
    else alert(data.error || '导出失败');
  } catch (e) { alert('导出失败: ' + e.message); }
}

function cancelExport() {
  exportDialog.value = false;
  exportNote.value = '';
  exportNoteError.value = '';
  exportingLog.value = null;
}

async function copyPath() {
  try {
    await navigator.clipboard.writeText(exportPath.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 1500);
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = exportPath.value;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copied.value = true;
      setTimeout(() => { copied.value = false; }, 1500);
    } catch {
      copyFailed.value = true;
      setTimeout(() => { copyFailed.value = false; }, 1500);
    }
  }
}

function lineClass(line) {
  if (line.type === 'error') return 'text-red-600 dark:text-red-400';
  if (line.type === 'stderr') return 'text-slate-400 dark:text-slate-500';
  if (line.text?.includes('✅')) return 'text-green-600 dark:text-green-400 font-semibold';
  if (line.text?.includes('❌')) return 'text-red-600 dark:text-red-400 font-semibold';
  if (line.text?.startsWith('【')) return 'text-green-600 dark:text-green-400 font-semibold';
  return 'text-slate-800 dark:text-slate-200';
}

async function clearAllLogs() {
  clearingLogs.value = true;
  try {
    for (const log of logs.value) {
      try { await deleteLog(log.tool, log.filename); } catch {}
    }
    logs.value = [];
    selectedLogId.value = null;
    logContent.value = null;
  } finally {
    clearingLogs.value = false;
    confirmClearAll.value = false;
  }
}

onMounted(() => {
  loadLogs();
  recoverActiveTasks();
  // 已有运行中任务完成时自动刷新日志列表
  for (const [tid, t] of Object.entries(task.taskMap || {})) {
    if (t.status === 'running' || t.status === 'connecting' || t.status === 'retrying') {
      task.onTaskExit(tid, () => loadLogs());
    }
  }
});


async function recoverActiveTasks() {
  try {
    const data = await listTasks();
    for (const t of data.tasks || []) {
      if (t.status === 'running' && !task.taskMap[t.taskId]) {
        const sseUrl = `/app/file-tools/api/events?taskId=${t.taskId}`;
        task.connect(sseUrl, t.taskId, t.tool);
      }
    }
  } catch {}
}
</script>

<template>
  <div class="flex flex-col h-full">
    <div v-if="exportPath" class="flex items-center gap-2 px-3 py-2 rounded-lg bg-green-50 dark:bg-green-900/20 text-sm mb-4 shrink-0">
      <span class="text-green-700 dark:text-green-400">已导出：</span>
      <code class="text-green-800 dark:text-green-300 font-mono text-xs break-all">{{ exportPath }}</code>
      <button @click="copyPath" class="shrink-0 px-2 py-1 rounded text-xs transition-colors"
          :class="copyFailed ? 'bg-red-200 dark:bg-red-800 text-red-700 dark:text-red-300' : copied ? 'bg-green-200 dark:bg-green-800 text-green-700 dark:text-green-300' : 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200 hover:bg-green-300 dark:hover:bg-green-700'">
          {{ copyFailed ? '❌ 复制失败' : copied ? '✅ 已复制' : '复制路径' }}
        </button>
      <button @click="exportPath = ''" class="shrink-0 ml-auto w-6 h-6 flex items-center justify-center rounded text-green-600 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-800 transition-colors" title="关闭">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>

    <!-- header + filters -->
    <div class="flex items-center justify-between mb-4 shrink-0 flex-wrap gap-3">
      <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100 transition-colors">📋 运行记录</h2>
      <div class="flex items-center gap-2">
        <!-- 类型筛选 - 胶囊圆点 -->
        <div class="relative">
          <button @click="toolOpen = !toolOpen; statusOpen = false"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm font-medium transition-all duration-200"
            :class="toolFilter === 'compare'
              ? 'border-blue-400 dark:border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : toolFilter === 'duplicate'
              ? 'border-purple-400 dark:border-purple-500 text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20'
              : 'border-slate-300 dark:border-[#535862] text-slate-600 dark:text-slate-400 bg-white dark:bg-[#1f252e] hover:border-slate-400'">
            <span v-if="toolFilter === 'compare'" class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></span>
            <span v-else-if="toolFilter === 'duplicate'" class="w-1.5 h-1.5 rounded-full bg-purple-500 shrink-0"></span>
            {{ toolOptions.find(o => o.value === toolFilter)?.label }}
            <svg class="w-3 h-3 transition-transform" :class="toolOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div v-if="toolOpen" class="absolute top-full left-0 mt-1 w-36 rounded-xl border border-slate-200 dark:border-[#353842] bg-white dark:bg-[#1f252e] shadow-xl z-20 py-1.5">
            <button v-for="o in toolOptions" :key="o.value" @click="toolFilter = o.value; toolOpen = false"
              class="flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-[#2a2d35] transition-colors rounded-lg mx-1"
              :class="toolFilter === o.value
                ? o.value === 'compare' ? 'text-blue-600 dark:text-blue-400 font-semibold' : o.value === 'duplicate' ? 'text-purple-600 dark:text-purple-400 font-semibold' : 'text-slate-700 dark:text-slate-300'
                : 'text-slate-700 dark:text-slate-300'">
              <span v-if="toolFilter === o.value" class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="o.value === 'compare' ? 'bg-blue-500' : o.value === 'duplicate' ? 'bg-purple-500' : 'bg-slate-400'"></span>
              <span v-else class="w-1.5 h-1.5 shrink-0"></span>
              {{ o.label }}
            </button>
          </div>
        </div>
        <!-- 状态筛选 - 胶囊圆点 -->
        <div class="relative">
          <button @click="statusOpen = !statusOpen; toolOpen = false"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm font-medium transition-all duration-200"
            :class="statusFilter === 'running'
              ? 'border-blue-400 dark:border-blue-500 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : statusFilter === 'done'
              ? 'border-green-400 dark:border-green-500 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
              : statusFilter === 'stopped'
              ? 'border-orange-400 dark:border-orange-500 text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20'
              : 'border-slate-300 dark:border-[#535862] text-slate-600 dark:text-slate-400 bg-white dark:bg-[#1f252e] hover:border-slate-400'">
            <span v-if="statusFilter === 'running'" class="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></span>
            <span v-else-if="statusFilter === 'done'" class="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0"></span>
            <span v-else-if="statusFilter === 'stopped'" class="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0"></span>
            {{ statusOptions.find(o => o.value === statusFilter)?.label }}
            <svg class="w-3 h-3 transition-transform" :class="statusOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path d="m6 9 6 6 6-6"/></svg>
          </button>
          <div v-if="statusOpen" class="absolute top-full right-0 mt-1 w-32 rounded-xl border border-slate-200 dark:border-[#353842] bg-white dark:bg-[#1f252e] shadow-xl z-20 py-1.5">
            <button v-for="o in statusOptions" :key="o.value" @click="statusFilter = o.value; statusOpen = false"
              class="flex items-center gap-2 w-full px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-[#2a2d35] transition-colors rounded-lg mx-1"
              :class="statusFilter === o.value
                ? o.value === 'running' ? 'text-blue-600 dark:text-blue-400 font-semibold' : o.value === 'done' ? 'text-green-600 dark:text-green-400 font-semibold' : o.value === 'stopped' ? 'text-orange-600 dark:text-orange-400 font-semibold' : 'text-slate-700 dark:text-slate-300'
                : 'text-slate-700 dark:text-slate-300'">
              <span v-if="statusFilter === o.value" class="w-1.5 h-1.5 rounded-full shrink-0"
                :class="o.value === 'running' ? 'bg-blue-500' : o.value === 'done' ? 'bg-green-500' : o.value === 'stopped' ? 'bg-orange-500' : 'bg-slate-400'"></span>
              <span v-else class="w-1.5 h-1.5 shrink-0"></span>
              {{ o.label }}
            </button>
          </div>
        </div>
        <button @click="loadLogs" :disabled="loading" title="刷新"
          class="p-1.5 rounded-lg text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-[#1f252e] disabled:opacity-50 transition-all">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" :class="loading ? 'animate-spin' : ''" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
        <button @click="confirmClearAll = true" :disabled="loading || clearingLogs || logs.length === 0" title="清空记录"
          class="p-1.5 rounded-lg text-slate-400 dark:text-slate-500 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-30 transition-all">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>

    <div class="flex-1 min-h-0 overflow-y-auto space-y-3">
      <!-- 活跃任务 (仅状态筛选为 running 时显示) -->
      <template v-if="statusFilter === 'running' || statusFilter === 'all'">
        <template v-for="at in filteredActiveTasks" :key="'active-' + at.taskId">
          <div class="border rounded-xl border-blue-400 dark:border-blue-500 bg-blue-50/30 dark:bg-blue-900/10">
            <div class="flex items-center gap-3 px-4 py-3 cursor-pointer" @click="viewActive(at.taskId)">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">运行中</span>
              <span class="text-xs text-slate-500 dark:text-slate-400 truncate flex-1">任务 {{ at.taskId.slice(0, 8) }}...</span>
              <div class="h-1.5 w-24 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden shrink-0">
                <div class="h-full bg-blue-500 rounded-full transition-all duration-300" :style="{ width: (at.progress?.percent || 0) + '%' }" />
              </div>
              <span class="text-xs text-blue-600 dark:text-blue-400 tabular-nums shrink-0">{{ at.progress?.percent || 0 }}%</span>
              <button @click.stop="handleStop(at.taskId)" :disabled="stopping.has(at.taskId)"
                class="px-3 py-1 rounded-lg bg-red-600 text-white text-xs font-semibold hover:bg-red-700 disabled:opacity-50 transition-all shrink-0">
                {{ stopping.has(at.taskId) ? '终止中...' : '终止' }}
              </button>
            </div>
            <div v-if="selectedLogId === at.taskId" class="border-t border-blue-200 dark:border-blue-800">
              <div class="flex items-center justify-between px-4 py-2 bg-blue-50 dark:bg-blue-900/10">
                <span class="text-xs text-slate-500 dark:text-slate-400">{{ at.lines.length }} 行输出</span>
                <button @click="openExportDialog(at)" class="px-3 py-1 rounded-lg border border-green-300 dark:border-green-700 text-green-700 dark:text-green-400 text-xs hover:bg-green-50 dark:hover:bg-green-900/20 transition-all">导出 TXT</button>
              </div>
              <div class="max-h-80 overflow-y-auto px-4 py-2 font-mono text-xs bg-white dark:bg-[#14171A]">
                <div v-if="at.lines.length === 0" class="text-slate-400 dark:text-slate-500 py-4 text-center">等待输出...</div>
                <div v-for="(line, i) in at.lines" :key="i" :class="lineClass(line)" class="py-0.5 break-all whitespace-pre-wrap">{{ line.text }}</div>
              </div>
            </div>
          </div>
        </template>
      </template>

      <!-- 历史记录 -->
      <template v-if="loading">
        <div class="text-center text-slate-400 dark:text-slate-500 text-sm py-8">加载中...</div>
      </template>
      <template v-else-if="filteredLogs.length === 0">
        <div class="flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 py-12">
          <p class="text-lg mb-1">📭</p>
          <p class="text-sm">暂无运行记录</p>
        </div>
      </template>

      <template v-for="log in filteredLogs" :key="'log-' + log.id">
        <div class="border rounded-xl transition-all duration-200"
          :class="selectedLogId === log.id
            ? 'border-blue-400 dark:border-blue-500 bg-blue-50/50 dark:bg-blue-900/10'
            : 'border-slate-200 dark:border-[#353842] bg-white dark:bg-[#1a1d24] hover:border-slate-300 dark:hover:border-slate-600'">
          <div class="flex items-center gap-3 px-4 py-3 cursor-pointer" @click="viewLog(log)">
            <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
              :class="log.tool === 'compare' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400' : 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'">
              {{ TOOL_LABEL[log.tool] || log.tool }}
            </span>
            <span class="text-xs text-slate-400 dark:text-slate-500 shrink-0 tabular-nums">{{ formatTime(log.timestamp) }}</span>
            <span class="text-xs text-slate-500 dark:text-slate-400 truncate flex-1">{{ formatArgs(log) }}</span>
            <span v-if="log.result" class="text-xs px-1.5 py-0.5 rounded font-medium shrink-0"
              :class="log.result === 'has_diff' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' : log.result === 'ok' ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' : log.result === 'has_dup' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400' : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'">
              {{ log.result === 'has_diff' ? '有差异' : log.result === 'ok' ? '一致' : log.result === 'has_dup' ? '有重复' : log.result === 'no_dup' ? '无重复' : '' }}
            </span>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
              :class="log.status === 'stopped' || log.exitCode === 143
                ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400'
                : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'">
              {{ log.status === 'stopped' || log.exitCode === 143 ? '已终止' : '已完成' }}
            </span>
            <button @click.stop="showDeleteConfirm(log)" :disabled="deleting.has(log.filename)"
              class="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 transition-all" title="删除">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
          <div v-if="selectedLogId === log.id" class="border-t border-slate-200 dark:border-[#353842]">
            <div class="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-[#14171A]">
              <span class="text-xs text-slate-500 dark:text-slate-400">{{ log.lineCount }} 行输出</span>
              <button @click="openExportDialog(log)" class="px-3 py-1 rounded-lg border border-green-300 dark:border-green-700 text-green-700 dark:text-green-400 text-xs hover:bg-green-50 dark:hover:bg-green-900/20 transition-all">导出 TXT</button>
            </div>
            <div class="max-h-80 overflow-y-auto px-4 py-2 font-mono text-xs">
              <div v-if="!logContent" class="text-slate-400 dark:text-slate-500 py-4 text-center">加载中...</div>
              <div v-else-if="logContent.length === 0" class="text-slate-400 dark:text-slate-500 py-4 text-center">无输出</div>
              <div v-else>
                <div v-for="(line, i) in logContent" :key="i" class="py-0.5 text-slate-700 dark:text-slate-300 break-all whitespace-pre-wrap">{{ line.text || line }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>


    <!-- 导出备注弹窗 -->
    <div v-if="exportDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="cancelExport">
      <div class="bg-white dark:bg-[#1f252e] rounded-2xl shadow-2xl p-6 w-80 mx-4 border border-slate-200 dark:border-[#353842]">
        <p class="text-sm text-slate-700 dark:text-slate-200 mb-1 font-semibold">导出 TXT</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">可选填写备注，将追加到文件名末尾</p>
        <input v-model="exportNote" @input="exportNoteError = ''" @keyup.enter="doExport"
          class="w-full px-3 py-2 rounded-lg text-sm border border-slate-300 dark:border-[#535862] bg-white dark:bg-[#14171A] text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-green-400 dark:focus:border-green-500 transition-colors mb-1"
          placeholder="例：备份校验结果" maxlength="60" autofocus />
        <p v-if="exportNoteError" class="text-xs text-red-500 mb-2">{{ exportNoteError }}</p>
        <p v-else class="text-xs text-slate-400 dark:text-slate-500 mb-4">不能包含 \ / : . * ? " &lt; &gt; | 空格</p>
        <div class="flex justify-end gap-2">
          <button @click="cancelExport"
            class="px-4 py-2 rounded-lg text-sm border border-slate-300 dark:border-[#535862] text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-[#2a2d35] transition-colors">取消</button>
          <button @click="doExport"
            class="px-4 py-2 rounded-lg text-sm bg-green-600 text-white hover:bg-green-700 transition-colors">导出</button>
        </div>
      </div>
    </div>

    <!-- 清空全部确认弹窗 -->
    <div v-if="confirmClearAll" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="confirmClearAll = false">
      <div class="bg-white dark:bg-[#1f252e] rounded-2xl shadow-2xl p-6 w-80 mx-4 border border-slate-200 dark:border-[#353842]">
        <p class="text-sm text-slate-700 dark:text-slate-200 mb-1 font-semibold">确认清空</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-5">此操作不可恢复，确定要清空所有运行记录？</p>
        <div class="flex justify-end gap-2">
          <button @click="confirmClearAll = false"
            class="px-4 py-2 rounded-lg text-sm border border-slate-300 dark:border-[#535862] text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-[#2a2d35] transition-colors">取消</button>
          <button @click="clearAllLogs"
            class="px-4 py-2 rounded-lg text-sm bg-red-600 text-white hover:bg-red-700 transition-colors">清空</button>
        </div>
      </div>
    </div>

    <div v-if="confirmDeleteTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="confirmDeleteTarget = null">
      <div class="bg-white dark:bg-[#1f252e] rounded-2xl shadow-2xl p-6 w-80 mx-4 border border-slate-200 dark:border-[#353842]">
        <p class="text-sm text-slate-700 dark:text-slate-200 mb-1 font-semibold">确认删除</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-5">此操作不可恢复，确定要删除这条运行记录？</p>
        <div class="flex justify-end gap-2">
          <button @click="confirmDeleteTarget = null"
            class="px-4 py-2 rounded-lg text-sm border border-slate-300 dark:border-[#535862] text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-[#2a2d35] transition-colors">取消</button>
          <button @click="doDelete()"
            class="px-4 py-2 rounded-lg text-sm bg-red-600 text-white hover:bg-red-700 transition-colors">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>
