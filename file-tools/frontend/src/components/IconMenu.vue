<script setup>
defineProps({ size: { type: Number, default: 18 } });
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 5h16"/>
    <path d="M4 12h16"/>
    <path d="M4 19h16"/>
  </svg>
</template>
