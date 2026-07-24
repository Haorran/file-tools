<script setup>
import { ref, onMounted } from 'vue';

const appVersion = __APP_VERSION__;

const crashLogs = ref([]);
const showLogs = ref(false);

function loadCrashLogs() {
  try {
    const raw = localStorage.getItem('file-tools-crash-log');
    crashLogs.value = raw ? JSON.parse(raw) : [];
  } catch {
    crashLogs.value = [];
  }
}

function clearCrashLogs() {
  localStorage.removeItem('file-tools-crash-log');
  crashLogs.value = [];
}

async function exportCrashLogs() {
  const content = crashLogs.value.map(l =>
    `[${l.time}] [${(l.level || 'error').toUpperCase()}] ${l.message} ${l.detail || ''}`
  ).join('\n');
  if (!content) { alert('没有日志可导出'); return; }
  const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `crash_log_${ts}.txt`;
  try {
    const res = await fetch('/app/file-tools/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, filename }),
    });
    const data = await res.json();
    if (data.path) {
      alert('已导出到: ' + data.path);
    } else {
      alert(data.error || '导出失败');
    }
  } catch (e) { alert('导出失败: ' + e.message); }
}

onMounted(loadCrashLogs);
</script>

<template>
  <div class="flex flex-col h-full">
    <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100 mb-6 transition-colors">⚙️ 设置</h2>

    <div class="border border-slate-200 dark:border-[#353842] rounded-xl bg-white dark:bg-[#1a1d24] p-6 transition-colors mb-4">
      <h3 class="text-base font-semibold text-slate-800 dark:text-slate-100 mb-4 pb-3 border-b border-slate-100 dark:border-[#353842]">关于</h3>
      <div class="space-y-3 text-sm">
        <div class="flex items-center">
          <span class="w-28 text-slate-500 dark:text-slate-400 shrink-0">应用名称</span>
          <span class="text-slate-800 dark:text-slate-100 font-medium">文件工具箱</span>
        </div>
        <div class="flex items-center">
          <span class="w-28 text-slate-500 dark:text-slate-400 shrink-0">作者</span>
          <span class="text-slate-800 dark:text-slate-100">灏然</span>
        </div>
        <div class="flex items-center">
          <span class="w-28 text-slate-500 dark:text-slate-400 shrink-0">应用反馈&建议</span>
          <div class="flex items-center gap-4">
            <a href="https://s26.fnnas.net/s/01e4988bc5b4460d94" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline transition-colors">飞牛文件收集</a>
            <a href="https://club.fnnas.com/home.php?username=kiko_" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline transition-colors">论坛名片</a>
          </div>
        </div>
        <div class="flex items-center">
          <span class="w-28 text-slate-500 dark:text-slate-400 shrink-0">当前版本</span>
          <span class="text-slate-800 dark:text-slate-100 font-mono">v{{ appVersion }}</span>
        </div>
      </div>
    </div>

    <!-- 应用日志 -->
    <div class="border border-slate-200 dark:border-[#353842] rounded-xl bg-white dark:bg-[#1a1d24] p-6 transition-colors">
      <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-100 dark:border-[#353842]">
        <h3 class="text-base font-semibold text-slate-800 dark:text-slate-100">应用日志</h3>
        <div class="flex items-center gap-2">
          <button @click="loadCrashLogs" class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-[#353842] text-slate-600 dark:text-slate-400 text-sm hover:bg-slate-100 dark:hover:bg-[#1f252e] transition-all">刷新</button>
          <button v-if="crashLogs.length > 0" @click="exportCrashLogs" class="px-3 py-1.5 rounded-lg border border-green-300 dark:border-green-700 text-green-700 dark:text-green-400 text-sm hover:bg-green-50 dark:hover:bg-green-900/20 transition-all">导出日志</button>
          <button v-if="crashLogs.length > 0" @click="clearCrashLogs" class="px-3 py-1.5 rounded-lg border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 text-sm hover:bg-red-50 dark:hover:bg-red-900/20 transition-all">清空</button>
        </div>
      </div>

      <div v-if="crashLogs.length === 0" class="text-sm text-slate-400 dark:text-slate-500 italic py-4 text-center">
        暂无日志记录
      </div>
      <div v-else class="max-h-80 overflow-y-auto font-mono text-xs space-y-1">
        <div v-for="(log, i) in crashLogs" :key="i"
          class="px-3 py-1.5 rounded"
          :class="log.level === 'error'
            ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'
            : log.level === 'warn'
            ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
            : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400'">
          <div class="text-slate-400 dark:text-slate-500">{{ log.time }}</div>
          <div class="break-all whitespace-pre-wrap">{{ log.message }}</div>
          <div v-if="log.detail" class="text-slate-400 dark:text-slate-500 break-all">{{ log.detail }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
