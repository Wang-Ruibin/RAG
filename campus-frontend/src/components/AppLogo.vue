<template>
  <div :class="['app-logo', { compact }]">
    <img src="/assets/hhu-emblem.jpg" alt="河海大学校徽" />
    <div v-if="!compact" class="app-logo__text">
      <strong>河海大学</strong>
      <span>HOHAI UNIVERSITY</span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })
</script>

<style scoped>
.app-logo { display:flex; align-items:center; gap:12px; min-width:0; }
.app-logo img { width:58px; height:58px; object-fit:cover; object-position:50% 3%; border-radius:50%; mix-blend-mode:multiply; }
.app-logo.compact img { width:38px; height:38px; }
.app-logo__text { min-width:0; }
.app-logo__text strong { display:block; color:var(--brand); font-family:"LXGW WenKai Screen","KaiTi",serif; font-size:24px; line-height:1.15; letter-spacing:.08em; white-space:nowrap; }
.app-logo__text span { display:block; margin-top:4px; color:var(--brand); font-size:9px; letter-spacing:.04em; white-space:nowrap; }
:global(html.dark .app-logo img) { mix-blend-mode:screen; filter:brightness(1.2) contrast(.9); }
</style>
