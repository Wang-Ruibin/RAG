<template>
  <header class="page-heading">
    <div>
      <p v-if="eyebrow" class="page-heading__eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-heading__description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-heading__actions"><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string; eyebrow?: string }>()
</script>

<style scoped>
.page-heading { display:flex; min-height:92px; align-items:flex-start; justify-content:space-between; gap:24px; margin-bottom:14px; }
.page-heading__eyebrow { margin:0 0 5px; color:var(--brand); font-size:12px; font-weight:700; letter-spacing:.18em; text-transform:uppercase; }
.page-heading h1 { margin:0; color:var(--text); font-size:32px; line-height:1.3; font-weight:750; }
.page-heading__description { margin:8px 0 0; color:var(--text-muted); font-size:15px; }
.page-heading__actions { display:flex; gap:10px; align-items:center; padding-top:4px; flex-wrap:wrap; }
@media(max-width:640px){.page-heading{flex-direction:column}.page-heading h1{font-size:24px}.page-heading__actions{width:100%}}
</style>
