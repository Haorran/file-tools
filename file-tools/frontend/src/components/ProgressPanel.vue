<script setup>
defineProps({ data: Object });
</script>

<template>
  <div class="bg-slate-100 dark:bg-[#1f252e] border border-slate-200 dark:border-[#353842] rounded-xl p-4 mb-4 transition-colors duration-300 h-[88px] flex flex-col justify-center">
    <template v-if="data">
      <div class="flex items-center gap-2 mb-2 text-sm">
        <span class="font-semibold text-slate-700 dark:text-slate-200">进度</span>
        <span class="text-slate-500 dark:text-slate-400 tabular-nums">{{ data.current }}/{{ data.total }}</span>
        <span v-if="data.name" class="ml-auto text-slate-400 dark:text-slate-500 truncate max-w-[300px] text-right">{{ data.name }}</span>
      </div>
      <div class="h-1.5 bg-slate-200 dark:bg-[#2a2d35] rounded-full overflow-hidden">
        <div
          class="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-300 ease-out"
          :style="{ width: (data.percent || 0) + '%' }"
        />
      </div>
      <div class="text-xs text-slate-400 dark:text-slate-500 text-right mt-1 tabular-nums">{{ data.percent || 0 }}%</div>
    </template>
    <div v-else class="text-sm text-slate-400 dark:text-slate-500 italic">等待任务开始...</div>
  </div>
</template>
