import { createApp } from 'vue';
import App from './App.vue';
import './style.css';

const app = createApp(App);

// Vue 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  try {
    const raw = localStorage.getItem('file-tools-crash-log');
    const logs = raw ? JSON.parse(raw) : [];
    logs.push({
      time: new Date().toISOString(),
      level: 'error',
      message: `Vue: ${err.message}`,
      detail: `info=${info} stack=${(err.stack || '').slice(0, 500)}`,
    });
    localStorage.setItem('file-tools-crash-log', JSON.stringify(logs.slice(-200)));
  } catch {}
  console.error('[crash-log]', err, info);
};

// 全局 JS 错误
window.onerror = (msg, source, line, col, error) => {
  try {
    const raw = localStorage.getItem('file-tools-crash-log');
    const logs = raw ? JSON.parse(raw) : [];
    logs.push({
      time: new Date().toISOString(),
      level: 'error',
      message: String(msg),
      detail: `source=${source} line=${line}:${col}`,
    });
    localStorage.setItem('file-tools-crash-log', JSON.stringify(logs.slice(-200)));
  } catch {}
};

// Promise rejection
window.addEventListener('unhandledrejection', (e) => {
  try {
    const raw = localStorage.getItem('file-tools-crash-log');
    const logs = raw ? JSON.parse(raw) : [];
    logs.push({
      time: new Date().toISOString(),
      level: 'error',
      message: 'Promise: ' + (e.reason?.message || String(e.reason)),
      detail: '',
    });
    localStorage.setItem('file-tools-crash-log', JSON.stringify(logs.slice(-200)));
  } catch {}
});

window.__vueApp = app;
app.mount('#app');
