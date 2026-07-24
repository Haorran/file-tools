<script setup>
defineProps({
  icon: { type: Object, required: true },
  label: { type: String, required: true },
  isActive: { type: Boolean, default: false },
  collapsed: { type: Boolean, default: false },
  badge: { type: Number, default: undefined },
});
defineEmits(['click']);
</script>

<template>
  <button
    @click="$emit('click')"
    class="w-full relative rounded-lg transition-all duration-200 font-medium group overflow-hidden h-[42px]"
    :class="isActive
      ? 'bg-blue-50 dark:bg-[#2a2d35] text-blue-600 dark:text-blue-400'
      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'"
    :title="label"
  >
    <component
      :is="icon"
      class="absolute top-1/2 -translate-y-1/2 transition-all duration-300"
      :class="collapsed ? 'left-1/2 -translate-x-1/2' : 'left-3'"
      :size="18"
    />
    <span
      class="absolute left-[42px] top-1/2 -translate-y-1/2 text-sm whitespace-nowrap transition-all duration-300"
      :class="collapsed ? 'opacity-0' : 'opacity-100'"
    >{{ label }}</span>

    <!-- badge -->
    <span
      v-if="badge !== undefined && badge > 0"
      class="absolute top-2 transition-all duration-300 flex items-center justify-center min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full px-1"
      :class="collapsed ? 'right-2' : 'right-3'"
    >{{ badge > 99 ? '99+' : badge }}</span>

    <!-- collapsed tooltip -->
    <span
      v-if="collapsed"
      class="absolute left-12 bg-slate-900 dark:bg-[#353842] text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition pointer-events-none z-50 whitespace-nowrap"
    >{{ label }}</span>

    <!-- active indicator -->
    <span
      v-if="isActive"
      class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-blue-500 dark:bg-blue-400 rounded-r transition-all duration-300"
    />
  </button>
</template>
