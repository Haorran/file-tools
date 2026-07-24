import { reactive, shallowRef } from 'vue';
import { checkTaskStatus } from '../api';

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

export function useSSE() {
  const taskMap = reactive({});

  function ensureTask(taskId) {
    if (!taskMap[taskId]) {
      taskMap[taskId] = {
        status: 'connecting',
        progress: null,
        lines: [],
        exitCode: null,
        source: null,
        onExitCallbacks: [],
        retryCount: 0,
        retryTimer: null,
        sseUrl: null,
        tool: null,
      };
    }
    return taskMap[taskId];
  }

  function connect(sseUrl, taskId, tool, keepState) {
    const t = ensureTask(taskId);
    cleanup(t);
    t.sseUrl = sseUrl;
    t.tool = tool || t.tool || null;
    t.retryCount = 0;
    if (!keepState) {
      t.lines = [];
      t.progress = null;
      t.exitCode = null;
    }
    t.status = 'connecting';
    _openConnection(sseUrl, taskId);
  }

  function _openConnection(sseUrl, taskId) {
    const es = new EventSource(sseUrl);
    const t = ensureTask(taskId);
    t.source = es;

    es.addEventListener('connected', () => { t.status = 'running'; });

    es.addEventListener('progress', (e) => {
      try { t.progress = JSON.parse(e.data); } catch {}
    });

    es.addEventListener('stdout', (e) => {
      try {
        const d = JSON.parse(e.data);
        t.lines = [...t.lines, { type: 'stdout', text: d.line }];
      } catch {}
    });

    es.addEventListener('stderr', (e) => {
      try {
        const d = JSON.parse(e.data);
        if (!d.line.includes('进度')) {
          t.lines = [...t.lines, { type: 'stderr', text: d.line }];
        }
      } catch {}
    });

    es.addEventListener('exit', (e) => {
      try { t.exitCode = JSON.parse(e.data).code; } catch {}
      t.status = 'done';
      es.close();
      t.onExitCallbacks.forEach(cb => cb(t.exitCode));
    });

    es.addEventListener('error', (e) => {
      try {
        t.lines = [...t.lines, { type: 'error', text: JSON.parse(e.data).message }];
      } catch {}
      t.status = 'error';
      es.close();
      t.onExitCallbacks.forEach(cb => cb(null));
    });

    es.onerror = async () => {
      es.close();
      if (t.status === 'running' || t.status === 'connecting' || t.status === 'retrying') {
        const taskStatus = await checkTaskStatus(taskId);
        if (taskStatus === 'done') { t.status = 'done'; return; }
        else if (taskStatus !== 'running') {
          t.status = 'error';
          t.lines = [...t.lines, { type: 'error', text: '连接中断' }];
          return;
        }
        if (t.retryCount < MAX_RETRIES) {
          t.retryCount++;
          t.status = 'retrying';
          t.lines = [...t.lines, { type: 'error', text: `连接中断，第 ${t.retryCount}/${MAX_RETRIES} 次重试中...` }];
          t.retryTimer = setTimeout(() => {
            if (t.status === 'retrying') _openConnection(sseUrl, taskId);
          }, RETRY_DELAY_MS * t.retryCount);
        } else {
          t.status = 'error';
          t.lines = [...t.lines, { type: 'error', text: '连接中断，已达最大重试次数' }];
        }
      }
    };
  }

  function cleanup(t) {
    if (t.retryTimer) { clearTimeout(t.retryTimer); t.retryTimer = null; }
    if (t.source) { t.source.close(); t.source = null; }
  }

  function disconnectTask(taskId) {
    const t = taskMap[taskId];
    if (t) cleanup(t);
  }

  function resetTask(taskId) {
    disconnectTask(taskId);
    if (taskMap[taskId]) {
      taskMap[taskId].status = 'idle';
      taskMap[taskId].progress = null;
      taskMap[taskId].lines = [];
      taskMap[taskId].exitCode = null;
    }
  }

  function onTaskExit(taskId, callback) {
    const t = ensureTask(taskId);
    if (!t.onExitCallbacks) t.onExitCallbacks = [];
    t.onExitCallbacks.push(callback);
  }

  function removeTask(taskId) {
    disconnectTask(taskId);
    delete taskMap[taskId];
  }

  function getTaskIds() {
    return Object.keys(taskMap);
  }

  function hasRunningTask() {
    return Object.values(taskMap).some(t => t.status === 'running' || t.status === 'connecting' || t.status === 'retrying');
  }

  return { taskMap, connect, disconnectTask, resetTask, removeTask, onTaskExit, getTaskIds, hasRunningTask, ensureTask };
}
