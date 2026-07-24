<script setup>
defineProps({ size: { type: Number, default: 18 } });
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M12 7 L8 17 M12 7 L16 17 M9.5 14 L14.5 14"/>
  </svg>
</template>
