<template><span :class="['status-tag', `is-${tone}`]"><i />{{ label }}</span></template>
<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'success' | 'warning' | 'danger' | 'info' | 'primary' }>(), { tone: 'info' })
</script>
<style scoped>
.status-tag { display:inline-flex; align-items:center; gap:7px; min-height:26px; padding:3px 9px; border-radius:999px; color:var(--text-secondary); background:var(--surface-soft); font-size:12px; font-weight:600; }
.status-tag i { width:7px; height:7px; border-radius:50%; background:var(--text-light); }
.status-tag.is-success{color:#087a47;background:rgba(16,185,129,.1)} .status-tag.is-success i{background:#10b981}
.status-tag.is-warning{color:#a76100;background:rgba(245,158,11,.12)} .status-tag.is-warning i{background:#f59e0b}
.status-tag.is-danger{color:#c03636;background:rgba(239,68,68,.1)} .status-tag.is-danger i{background:#ef4444}
.status-tag.is-primary{color:var(--brand);background:var(--brand-soft)} .status-tag.is-primary i{background:var(--brand)}
html.dark .status-tag.is-success{color:#6ee7b7} html.dark .status-tag.is-warning{color:#fcd34d} html.dark .status-tag.is-danger{color:#fca5a5}
</style>
