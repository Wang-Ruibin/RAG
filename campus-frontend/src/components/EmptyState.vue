<template>
  <div class="empty-state">
    <div class="empty-state__icon"><el-icon><slot name="icon"><Document /></slot></el-icon></div>
    <strong>{{ title }}</strong><p>{{ description }}</p><slot />
  </div>
</template>
<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
withDefaults(defineProps<{ title?: string; description?: string }>(), { title: '暂无数据', description: '当前条件下没有可展示的内容' })
</script>
<style scoped>
.empty-state { display:flex; min-height:220px; flex-direction:column; align-items:center; justify-content:center; color:var(--text-muted); text-align:center; }
.empty-state__icon { display:grid; place-items:center; width:58px; height:58px; margin-bottom:14px; border-radius:18px; color:var(--brand); background:var(--brand-soft); font-size:26px; }
.empty-state strong{color:var(--text);font-size:15px}.empty-state p{margin:6px 0 14px;font-size:13px}
</style>
