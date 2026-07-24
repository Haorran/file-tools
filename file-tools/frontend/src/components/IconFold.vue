<script setup>
defineProps({ size: { type: Number, default: 18 } });
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect width="18" height="18" x="3" y="3" rx="2"/>
    <path d="m9 3-3 3 3 3"/>
  </svg>
</template>
