<template><pre class="json-viewer">{{ formatted }}</pre></template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ value?: unknown }>()
const formatted = computed(() => {
  if (props.value == null || props.value === '') return '—'
  if (typeof props.value !== 'string') return JSON.stringify(props.value, null, 2)
  try { return JSON.stringify(JSON.parse(props.value), null, 2) } catch { return props.value }
})
</script>
<style scoped>
.json-viewer { max-height:280px; margin:0; padding:14px 16px; overflow:auto; white-space:pre-wrap; word-break:break-word; color:var(--code-text); background:var(--code-bg); border:1px solid var(--border); border-radius:12px; font:12px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace; }
</style>
