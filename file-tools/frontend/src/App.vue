<script setup>
import { ref, computed, provide, onMounted } from 'vue';
import { useTheme } from './composables/useTheme';
import { useSSE } from './composables/useSSE';
import { listTasks } from './api';
import SidebarItem from './components/SidebarItem.vue';
import IconCompare from './components/IconCompare.vue';
import IconSearch from './components/IconSearch.vue';
import IconMenu from './components/IconMenu.vue';
import IconSun from './components/IconSun.vue';
import IconMoon from './components/IconMoon.vue';
import IconAuto from './components/IconAuto.vue';
import IconHistory from './components/IconHistory.vue';
import IconSettings from './components/IconSettings.vue';
import Compare from './pages/Compare.vue';
import Duplicate from './pages/Duplicate.vue';
import Runlog from './pages/Runlog.vue';
import Settings from './pages/Settings.vue';

const { theme, isDark, cycleTheme } = useTheme();
const { taskMap, connect, disconnectTask, resetTask, removeTask, onTaskExit, hasRunningTask } = useSSE();

const activeTab = ref('compare');
const collapsed = ref(false);
const triggerCompare = ref(false);
const triggerDuplicate = ref(false);
const runningFilter = ref({ tool: 'all', status: 'all' });

const NAV_ITEMS = [
  { key: 'compare', icon: IconCompare, label: '目录比较' },
  { key: 'duplicate', icon: IconSearch, label: '目录内查重' },
  { key: 'running', icon: IconHistory, label: '运行记录' },
];

function navigateToRunning(tool) {
  runningFilter.value = { tool: tool, status: 'running' };
  activeTab.value = 'running';
}

function switchTab(key) {
  if (key === 'running') {
    runningFilter.value = { tool: 'all', status: 'all' };
  }
  activeTab.value = key;
}

const task = { connect, triggerCompare, triggerDuplicate, taskMap, disconnectTask, resetTask, removeTask, onTaskExit, navigateToRunning };
provide('task', task);

const runningCount = computed(() => {
  return Object.values(taskMap).filter(
    t => t.status === 'running' || t.status === 'connecting' || t.status === 'retrying'
  ).length;
});

const themeTitle = computed(() => ({ light: '浅色模式', dark: '深色模式', auto: '跟随系统' })[theme.value]);

onMounted(async () => {
  try {
    const data = await listTasks();
    for (const t of data.tasks || []) {
      if (t.status === 'running' && !taskMap[t.taskId]) {
        const sseUrl = `/app/file-tools/api/events?taskId=${t.taskId}`;
        connect(sseUrl, t.taskId, t.tool);
      }
    }
  } catch {}
});
</script>

<template>
  <div class="flex h-screen transition-colors duration-300">
    <aside
      class="hidden md:flex flex-col bg-white dark:bg-[#14171A] border-r border-slate-200 dark:border-[#353842] transition-all duration-300 ease-in-out"
      :class="collapsed ? 'w-16' : 'w-48'"
    >
      <nav class="flex-1 flex flex-col px-2 pt-[14px] space-y-2">
        <div class="h-[42px] mb-2">
          <button @click="collapsed = !collapsed"
            class="w-full relative rounded-lg transition-all duration-200 font-medium group overflow-hidden h-[42px] text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            title="折叠/展开侧边栏">
            <IconMenu :size="18" class="absolute top-1/2 -translate-y-1/2 transition-all duration-300"
              :class="collapsed ? 'left-1/2 -translate-x-1/2' : 'left-3'" />
            <span class="absolute left-[42px] top-1/2 -translate-y-1/2 text-sm font-bold whitespace-nowrap transition-all duration-300"
              :class="collapsed ? 'opacity-0' : 'opacity-100'">文件工具箱</span>
          </button>
        </div>
        <div class="border-t border-slate-100 dark:border-[#353842]" />
        <SidebarItem v-for="item in NAV_ITEMS" :key="item.key" :icon="item.icon" :label="item.label"
          :isActive="activeTab === item.key" :collapsed="collapsed"
          :badge="item.key === 'running' ? runningCount : undefined"
          @click="switchTab(item.key)" />
      </nav>
      <div
        class="p-2 mb-2 border-t border-slate-100 dark:border-[#353842] pt-3 flex transition-all duration-300 ease-in-out"
        :class="collapsed ? 'flex-col items-center space-y-1' : 'flex-row justify-center items-center gap-1'"
      >
        <button @click="cycleTheme"
          class="shrink-0 w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300 text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
          :title="themeTitle">
          <IconSun v-if="theme === 'light'" :size="18" /><IconMoon v-else-if="theme === 'dark'" :size="18" /><IconAuto v-else :size="18" />
        </button>
        <button @click="activeTab = 'settings'"
          class="shrink-0 w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-200 relative group"
          :class="activeTab === 'settings' ? 'bg-blue-50 dark:bg-[#2a2d35] text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
          title="设置">
          <IconSettings :size="18" />
          <span v-if="collapsed" class="absolute left-12 bg-slate-900 dark:bg-[#353842] text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 whitespace-nowrap">设置</span>
        </button>
      </div>
    </aside>

    <div class="flex-1 flex flex-col h-full relative overflow-hidden">
      <div class="flex-1 overflow-y-auto bg-slate-50 dark:bg-[#1a1d24] transition-colors duration-300">
        <div class="p-6">
          <transition name="fade" mode="out-in">
            <Compare v-if="activeTab === 'compare'" key="compare" />
            <Duplicate v-else-if="activeTab === 'duplicate'" key="duplicate" />
            <Runlog v-else-if="activeTab === 'running'" :key="'running'" :initialFilter="runningFilter" />
            <Settings v-else key="settings" />
          </transition>
        </div>
      </div>
    </div>

    <nav class="md:hidden shrink-0 bg-white dark:bg-[#14171A] border-t border-slate-200 dark:border-[#353842] flex justify-around py-3 z-30 safe-area-pb shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
      <button v-for="item in NAV_ITEMS" :key="item.key" @click="switchTab(item.key)"
        class="flex flex-col items-center gap-1 relative"
        :class="activeTab === item.key ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500'">
        <component :is="item.icon" :size="20" />
        <span class="text-[10px] font-medium">{{ item.label }}</span>
        <span v-if="item.key === 'running' && runningCount > 0"
          class="absolute -top-1 -right-1 min-w-[16px] h-[16px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-0.5">{{ runningCount > 99 ? '99+' : runningCount }}</span>
      </button>
      <button @click="activeTab = 'settings'" class="flex flex-col items-center gap-1"
        :class="activeTab === 'settings' ? 'text-blue-600 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500'">
        <IconSettings :size="20" /><span class="text-[10px] font-medium">设置</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.safe-area-pb { padding-bottom: env(safe-area-inset-bottom, 12px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
