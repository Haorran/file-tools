import { ref } from 'vue';

const STORAGE_KEY = 'file-tools-crash-log';
const MAX_ENTRIES = 200;

const logs = ref([]);

function loadLogs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    logs.value = raw ? JSON.parse(raw) : [];
  } catch {
    logs.value = [];
  }
}

function saveLogs() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(logs.value.slice(-MAX_ENTRIES)));
  } catch {}
}

function addLog(level, message, detail) {
  const entry = {
    time: new Date().toISOString(),
    level,   // 'error' | 'warn' | 'info'
    message,
    detail: detail ? String(detail).slice(0, 2000) : '',
  };
  logs.value = [...logs.value, entry];
  saveLogs();
}

function setupGlobalHandler() {
  // Vue 错误
  const origErrorHandler = window.onerror;
  window.onerror = (msg, source, line, col, error) => {
    addLog('error', String(msg), `source=${source} line=${line}:${col} stack=${error?.stack || ''}`);
    if (origErrorHandler) origErrorHandler(msg, source, line, col, error);
  };

  // Promise rejection
  window.addEventListener('unhandledrejection', (e) => {
    addLog('error', 'Unhandled Promise', e.reason?.message || String(e.reason));
  });

  // Vue error handler (will be installed in main.js)
  if (window.__vueApp) {
    window.__vueApp.config.errorHandler = (err, instance, info) => {
      addLog('error', `Vue: ${err.message}`, `info=${info} stack=${err.stack?.slice(0, 500)}`);
    };
  }
}

function clearLogs() {
  logs.value = [];
  saveLogs();
}

function exportLogs() {
  const text = logs.value.map(l =>
    `[${l.time}] [${l.level.toUpperCase()}] ${l.message} ${l.detail ? '| ' + l.detail : ''}`
  ).join('\n');
  return text;
}

loadLogs();
setupGlobalHandler();

export function useCrashLog() {
  return { logs, clearLogs, exportLogs, addLog };
}
