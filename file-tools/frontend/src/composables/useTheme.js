import { ref, watch, onMounted, onUnmounted } from 'vue';

const THEME_KEY = 'file-tools-theme';
const theme = ref('auto');
const isDark = ref(false);

function getTimeDark() {
  const h = new Date(Date.now() + 28800000).getUTCHours();
  return h < 8 || h >= 18;
}

function applyDark(v) {
  isDark.value = v;
  document.documentElement.classList.toggle('dark', v);
}

function resolve(mode) {
  let dark;
  if (mode === 'auto') {
    let fnosMode = null;
    try {
      fnosMode = new URLSearchParams(window.location.search).get('fnos-theme-mode');
      if (!fnosMode && window.parent !== window) {
        fnosMode = new URLSearchParams(window.parent.location.search).get('fnos-theme-mode');
      }
    } catch {}
    if (!fnosMode) {
      try { fnosMode = localStorage.getItem('fnos-theme-mode'); } catch {}
    }
    if (fnosMode === '20') dark = true;
    else if (fnosMode === '10') dark = false;
    else if (fnosMode === '30') dark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches;
    else dark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches || getTimeDark();
  } else {
    dark = mode === 'dark';
  }
  applyDark(dark);
}

let mqlHandler = null;
let storageHandler = null;

export function useTheme() {
  onMounted(() => {
    try {
      const v = localStorage.getItem(THEME_KEY);
      if (['light', 'dark', 'auto'].includes(v)) theme.value = v;
    } catch {}
    resolve(theme.value);

    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    mqlHandler = () => { if (theme.value === 'auto') resolve('auto'); };
    mql.addEventListener('change', mqlHandler);

    // 监听 NAS 桌面主题变更
    storageHandler = (e) => {
      if (e.key === 'fnos-theme-mode' && theme.value === 'auto') resolve('auto');
    };
    window.addEventListener('storage', storageHandler);
  });

  onUnmounted(() => {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    if (mqlHandler) mql.removeEventListener('change', mqlHandler);
    if (storageHandler) window.removeEventListener('storage', storageHandler);
  });

  watch(theme, (v) => {
    try { localStorage.setItem(THEME_KEY, v); } catch {}
    resolve(v);
  });

  function cycleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : theme.value === 'dark' ? 'auto' : 'light';
  }

  function setTheme(v) {
    theme.value = v;
  }

  const label = {
    light: '浅色模式',
    dark: '深色模式',
    auto: '自动模式',
  };

  return { theme, isDark, cycleTheme, setTheme, label };
}
