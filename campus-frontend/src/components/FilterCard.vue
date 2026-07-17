<template><section class="filter-card"><slot /></section></template>
<style scoped>
.filter-card { display:flex; min-height:88px; align-items:center; gap:14px; flex-wrap:wrap; padding:20px 24px; margin-bottom:16px; background:var(--surface); border:1px solid var(--border); border-radius:13px; box-shadow:var(--shadow-sm); }
.filter-card :deep(.el-input__wrapper),.filter-card :deep(.el-select__wrapper){min-height:44px}
.filter-card :deep(.el-button){height:44px;padding:8px 24px}
.filter-card :deep(.filter-field){display:flex;align-items:center;gap:10px}
.filter-card :deep(.filter-field>span){color:var(--text-secondary);font-size:14px;font-weight:600;white-space:nowrap}
</style>
