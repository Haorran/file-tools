<script setup>
import { ref, watch, nextTick } from 'vue';

const props = defineProps({
  lines: { type: Array, default: () => [] },
  exitCode: { type: Number, default: null },
  status: { type: String, default: 'idle' },
});

const bottomRef = ref(null);
watch(() => props.lines.length, () => {
  nextTick(() => bottomRef.value?.scrollIntoView({ behavior: 'smooth' }));
});

function lineClass(line) {
  if (line.type === 'error') return 'text-red-600 dark:text-red-400';
  if (line.type === 'stderr') return 'text-slate-400 dark:text-slate-500';
  if (line.text.includes('✅')) return 'text-green-600 dark:text-green-400 font-semibold';
  if (line.text.includes('❌')) return 'text-red-600 dark:text-red-400 font-semibold';
  if (line.text.startsWith('【')) return 'text-amber-600 dark:text-amber-400 font-semibold';
  return 'text-slate-800 dark:text-slate-200';
}
</script>

<template>
  <div class="border border-slate-200 dark:border-[#353842] rounded-xl overflow-hidden mt-4 transition-colors duration-300 flex flex-col flex-1 min-h-[200px]">
    <!-- header -->
    <div class="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-[#1f252e] border-b border-slate-200 dark:border-[#353842] shrink-0">
      <span class="font-semibold text-sm text-slate-700 dark:text-slate-200">日志</span>
      <span v-if="status === 'done' && exitCode === 0" class="text-xs px-3 py-0.5 rounded-full font-semibold bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">✅ 通过</span>
      <span v-else-if="status === 'done'" class="text-xs px-3 py-0.5 rounded-full font-semibold bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400">❌ 退出码 {{ exitCode }}</span>
      <span v-else-if="status === 'running'" class="text-xs px-3 py-0.5 rounded-full font-semibold bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">⏳ 运行中</span>
      <span v-else-if="status === 'error'" class="text-xs px-3 py-0.5 rounded-full font-semibold bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400">❌ 错误</span>
    </div>
    <!-- body -->
    <div class="p-4 flex-1 min-h-0 overflow-y-auto bg-white dark:bg-[#14171A] font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-all">
      <div v-if="status === 'idle'" class="text-slate-400 dark:text-slate-500 italic">日志将在任务运行时显示...</div>
      <div v-else-if="lines.length === 0 && status === 'running'" class="text-slate-400 dark:text-slate-500 italic">等待输出...</div>
      <div v-for="(line, i) in lines" :key="i" :class="lineClass(line)">{{ line.text }}</div>
      <div ref="bottomRef" />
    </div>
  </div>
</template>
