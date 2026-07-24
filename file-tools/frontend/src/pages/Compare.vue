<script setup>
import { ref, inject, watch, onMounted } from 'vue';
import { startCompare } from '../api';

const MODES = [
  { value: 0, label: '极速', desc: '仅文件名+大小' },
  { value: 1, label: '推荐', desc: '大小+首位局部哈希' },
  { value: 2, label: '完整', desc: '大小+首位局部哈希+SHA256' },
];

const BLOCK_SIZES = [
  { value: 65536, label: '64KB' },
  { value: 262144, label: '256KB' },
  { value: 1048576, label: '1MB' },
];

const task = inject('task');

const mode = ref(1);
const blockSize = ref(65536);
const dirA = ref('');
const dirB = ref('');
const error = ref('');

onMounted(() => {
  watch(() => task.triggerCompare.value, (v) => {
    if (v) {
      task.triggerCompare.value = false;
      handleSubmit();
    }
  });
});

async function handleSubmit() {
  error.value = '';
  if (!dirA.value.trim() || !dirB.value.trim()) { error.value = '请填写两个目录路径'; return; }
  try {
    const bs = mode.value === 1 ? blockSize.value : undefined;
    const { taskId, sseUrl } = await startCompare({ mode: mode.value, dirA: dirA.value.trim(), dirB: dirB.value.trim(), blockSize: bs });
    task.connect(sseUrl, taskId, "compare");
    task.navigateToRunning('compare');
  } catch (e) { error.value = e.message; }
}
</script>

<template>
  <div class="flex flex-col">
    <h2 class="text-xl font-bold text-slate-800 dark:text-slate-100 mb-4 transition-colors shrink-0">📁 目录比较</h2>

    <div class="flex items-center gap-3 mb-4 shrink-0 flex-wrap">
      <button @click="handleSubmit"
        class="px-6 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition-all duration-200">
        创建任务
      </button>
    </div>

    <div class="flex flex-col gap-4 mb-4 shrink-0">
      <div>
        <label class="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-2 transition-colors">校验模式</label>
        <div class="flex gap-3 flex-wrap">
          <label v-for="m in MODES" :key="m.value"
            class="flex items-center gap-3 px-4 py-3 border-2 rounded-xl cursor-pointer transition-all duration-200"
            :class="mode === m.value
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400'
              : 'border-slate-200 dark:border-[#353842] hover:border-slate-300 dark:hover:border-slate-500'">
            <input type="radio" name="mode" :value="m.value" v-model="mode" class="accent-blue-500" />
            <div>
              <div class="text-sm font-semibold text-slate-800 dark:text-slate-100 transition-colors">{{ m.label }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400 transition-colors">{{ m.desc }}</div>
            </div>
          </label>
        </div>
        <div v-if="mode === 1" class="mt-3">
          <label class="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1.5 transition-colors">首位局部哈希块大小</label>
          <div class="flex gap-2">
            <label v-for="bs in BLOCK_SIZES" :key="bs.value"
              class="px-3 py-1.5 border rounded-lg cursor-pointer text-sm transition-all duration-200"
              :class="blockSize === bs.value
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400 text-blue-700 dark:text-blue-300'
                : 'border-slate-200 dark:border-[#353842] text-slate-600 dark:text-slate-400 hover:border-slate-300'">
              <input type="radio" name="blockSize" :value="bs.value" v-model="blockSize" class="hidden" />
              {{ bs.label }}
            </label>
          </div>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5 transition-colors">目录A</label>
          <input v-model="dirA" type="text" placeholder="/vol1/backup/movies"
            class="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-[#353842] bg-white dark:bg-[#1f252e] text-slate-800 dark:text-slate-100 font-mono text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200" />
        </div>
        <div>
          <label class="block text-sm font-semibold text-slate-700 dark:text-slate-200 mb-1.5 transition-colors">目录B</label>
          <input v-model="dirB" type="text" placeholder="/vol2/backup/movies"
            class="w-full px-3 py-2.5 rounded-lg border border-slate-300 dark:border-[#353842] bg-white dark:bg-[#1f252e] text-slate-800 dark:text-slate-100 font-mono text-sm placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200" />
        </div>
      </div>
      <div v-if="error" class="px-3 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm transition-colors">{{ error }}</div>
    </div>
  </div>
</template>
