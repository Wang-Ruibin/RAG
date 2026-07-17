<template>
  <div class="page-shell">
    <PageHeader title="系统日志" description="记录系统内各类操作行为，便于审计、排查与追踪">
      <template #actions><el-button v-if="userStore.hasPermission('system:log:export')" type="primary" :icon="Download" :loading="exporting" :disabled="exporting" @click="handleExport">导出</el-button></template>
    </PageHeader>
    <FilterCard><label class="filter-field"><span>操作模块</span><el-input v-model="filters.title" placeholder="全部" clearable style="width:170px" @keyup.enter="applyFilters" /></label><label class="filter-field"><span>操作人</span><el-input v-model="filters.operName" placeholder="请输入操作人" clearable style="width:190px" @keyup.enter="applyFilters" /></label><label class="filter-field"><span>状态</span><el-select v-model="filters.status" placeholder="全部状态" clearable style="width:170px" @change="applyFilters"><el-option label="成功" :value="1" /><el-option label="失败" :value="0" /></el-select></label><el-button type="primary" :icon="Search" @click="applyFilters">查询</el-button><el-button :icon="Refresh" @click="resetFilters">重置</el-button></FilterCard>

    <section class="content-card table-card">
      <div class="table-toolbar"><div class="table-toolbar__actions"><el-button v-if="userStore.hasPermission('system:log:remove')" type="danger" plain :icon="Delete" @click="handleClean">清空日志</el-button><el-button v-if="userStore.hasPermission('system:log:remove')" type="primary" plain :icon="Delete" :disabled="selectedIds.length===0" @click="handleBatchDelete">批量删除</el-button></div><span class="table-toolbar__meta">已选择 {{ selectedIds.length }} 项</span></div>
      <div class="table-card__body"><el-table ref="tableRef" :data="logs" v-loading="loading" row-key="operId" style="width:100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="46" />
        <el-table-column prop="title" label="操作模块" min-width="130" />
        <el-table-column label="业务类型" width="110"><template #default="{row}"><el-tag type="info">{{ businessLabel(row.businessType) }}</el-tag></template></el-table-column>
        <el-table-column prop="operName" label="操作人" width="120" />
        <el-table-column label="请求" min-width="230"><template #default="{row}"><div class="request-cell"><span>{{ row.requestMethod || '—' }}</span><code>{{ row.operUrl }}</code></div></template></el-table-column>
        <el-table-column prop="operIp" label="IP 地址" width="140" />
        <el-table-column label="状态" width="95"><template #default="{row}"><StatusTag :label="row.status===1?'成功':'失败'" :tone="row.status===1?'success':'danger'" /></template></el-table-column>
        <el-table-column label="耗时" width="90"><template #default="{row}">{{ row.costTime }} ms</template></el-table-column>
        <el-table-column label="操作时间" width="180"><template #default="{row}">{{ formatDate(row.operTime) }}</template></el-table-column>
        <el-table-column label="操作" width="130" fixed="right"><template #default="{row}"><el-button link type="primary" @click="showDetail(row)">查看</el-button><el-popconfirm v-if="userStore.hasPermission('system:log:remove')" title="确定删除此条日志？" @confirm="handleDelete(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm></template></el-table-column>
        <template #empty><EmptyState title="暂无日志" description="当前筛选条件下没有操作记录" /></template>
      </el-table></div>
      <div class="table-footer"><span class="table-footer__total">共 {{ page.total }} 条日志</span><el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize" :total="page.total" :page-sizes="[10,20,50]" layout="sizes,prev,pager,next" @current-change="loadData" @size-change="handleSizeChange" /></div>
    </section>

    <el-drawer v-model="detailVisible" title="日志详情" size="390px">
      <div v-if="detail" class="detail-stack">
        <div class="detail-summary"><div><small>操作模块</small><strong>{{ detail.title }}</strong></div><StatusTag :label="detail.status===1?'成功':'失败'" :tone="detail.status===1?'success':'danger'" /></div>
        <el-descriptions :column="1" border><el-descriptions-item label="操作人">{{ detail.operName }}</el-descriptions-item><el-descriptions-item label="请求方法">{{ detail.requestMethod || '—' }}</el-descriptions-item><el-descriptions-item label="请求地址">{{ detail.operUrl }}</el-descriptions-item><el-descriptions-item label="IP 地址">{{ detail.operIp }}</el-descriptions-item><el-descriptions-item label="耗时">{{ detail.costTime }} ms</el-descriptions-item><el-descriptions-item label="操作时间">{{ formatDate(detail.operTime) }}</el-descriptions-item></el-descriptions>
        <section><h3>请求参数</h3><JsonViewer :value="detail.operParam" /></section><section><h3>返回结果</h3><JsonViewer :value="detail.jsonResult" /></section><el-alert v-if="detail.errorMsg" :title="detail.errorMsg" type="error" :closable="false" show-icon />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download, Refresh, Search } from '@element-plus/icons-vue'
import { cleanLog, deleteLogs, exportLog, listLog } from '@/api/log'
import { useUserStore } from '@/stores/user'
import type { SysOperLog } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'
import JsonViewer from '@/components/JsonViewer.vue'

const userStore=useUserStore(),logs=ref<SysOperLog[]>([]),loading=ref(false),exporting=ref(false),selectedIds=ref<number[]>([]),tableRef=ref()
const filters=reactive<{title:string;operName:string;status:number|null}>({title:'',operName:'',status:null}),page=reactive({pageNum:1,pageSize:10,total:0})
function filterParams(){return{title:filters.title.trim()||undefined,operName:filters.operName.trim()||undefined,status:filters.status??undefined}}
function formatDate(value?:string){return value?value.replace('T',' ').slice(0,19):'—'}
function businessLabel(value:number){return ['其他','新增','修改','删除','查询','导出','导入','授权'][value]||'其他'}
function clearSelection(){selectedIds.value=[];tableRef.value?.clearSelection()}
async function loadData(){clearSelection();loading.value=true;try{const response=await listLog({...filterParams(),pageNum:page.pageNum,pageSize:page.pageSize});logs.value=response.data.rows;page.total=response.data.total;await nextTick();clearSelection()}finally{loading.value=false}}
function handleSelectionChange(rows:SysOperLog[]){selectedIds.value=rows.map(row=>row.operId)}
function applyFilters(){page.pageNum=1;loadData()}function resetFilters(){filters.title='';filters.operName='';filters.status=null;page.pageNum=1;loadData()}function handleSizeChange(){page.pageNum=1;loadData()}

async function handleExport(){if(exporting.value)return;exporting.value=true;let objectUrl='';let link:HTMLAnchorElement|null=null;try{const response=await exportLog(filterParams());const blob=response.data instanceof Blob?response.data:new Blob([response.data]);objectUrl=URL.createObjectURL(blob);link=document.createElement('a');link.href=objectUrl;link.download=`系统日志_${new Date().toISOString().replace(/[-:T]/g,'').slice(0,14)}.xlsx`;document.body.appendChild(link);link.click();ElMessage.success('导出任务已完成')}catch{ElMessage.error('日志导出失败，请稍后重试')}finally{link?.remove();if(objectUrl)window.setTimeout(()=>URL.revokeObjectURL(objectUrl),0);exporting.value=false}}
async function handleDelete(row:SysOperLog){await deleteLogs([row.operId]);ElMessage.success('日志已删除');await loadData()}
async function handleBatchDelete(){if(!selectedIds.value.length)return;await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条日志？`,'批量删除',{type:'warning'});await deleteLogs([...selectedIds.value]);ElMessage.success('选中日志已删除');await loadData()}
async function handleClean(){await ElMessageBox.confirm('确定清空全部系统日志？此操作不可恢复。','清空日志',{type:'error'});await cleanLog();ElMessage.success('系统日志已清空');await loadData()}
const detailVisible=ref(false),detail=ref<SysOperLog|null>(null)
function showDetail(row:SysOperLog){detail.value={...row};detailVisible.value=true}
onMounted(loadData)
</script>

<style scoped>
.request-cell{display:flex;align-items:center;gap:8px}.request-cell span{padding:3px 6px;color:var(--brand);background:var(--brand-soft);border-radius:5px;font-size:10px;font-weight:800}.request-cell code{overflow:hidden;color:var(--text-muted);font-size:11px;text-overflow:ellipsis;white-space:nowrap}.detail-stack{display:flex;flex-direction:column;gap:18px}.detail-summary{display:flex;align-items:center;justify-content:space-between;padding:16px;background:var(--surface-soft);border-radius:12px}.detail-summary>div{display:flex;flex-direction:column}.detail-summary small{color:var(--text-muted)}.detail-summary strong{margin-top:4px;color:var(--text);font-size:17px}.detail-stack section h3{margin:0 0 8px;color:var(--text);font-size:14px}
</style>
