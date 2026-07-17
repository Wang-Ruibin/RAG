<template>
  <div class="page-shell knowledge-page">
    <PageHeader title="知识库管理" description="管理知识库文档，支持文档上传、处理、检索与维护">
      <template #actions><el-button v-if="canUpload" type="primary" :icon="Upload" @click="openUploadDialog">上传文档</el-button></template>
    </PageHeader>

    <FilterCard>
      <label class="filter-field"><span>分类：</span><el-input v-model="filters.category" placeholder="全部分类" clearable style="width:190px" @keyup.enter="applyFilters" /></label>
      <label class="filter-field"><span>状态：</span><el-select v-model="filters.status" placeholder="全部状态" clearable style="width:190px" @change="applyFilters">
        <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
      </el-select></label>
      <label class="filter-field"><span>关键词：</span><el-input v-model="filters.q" placeholder="请输入文件名或关键词" clearable style="width:280px" @keyup.enter="applyFilters" /></label>
      <el-button type="primary" :icon="Search" @click="applyFilters">搜索</el-button>
      <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
    </FilterCard>

    <section class="content-card table-card">
      <div class="table-card__body">
        <el-table :data="documents" v-loading="loading" row-key="id" style="width:100%">
          <el-table-column label="文档" min-width="280">
            <template #default="{row}"><div class="document-cell"><span class="file-icon">{{ fileSuffix(row.original_name) }}</span><div><strong>{{ row.title }}</strong><small>{{ row.original_name }}</small></div></div></template>
          </el-table-column>
          <el-table-column label="分类" width="130"><template #default="{row}"><el-tag type="info">{{ row.category || '未分类' }}</el-tag></template></el-table-column>
          <el-table-column label="状态" width="150"><template #default="{row}"><div class="status-column"><StatusTag :label="statusInfo(row.status).label" :tone="statusInfo(row.status).tone" /><small v-if="row.status==='QUEUED' || row.status==='PROCESSING'">{{ row.stage || '等待处理' }}</small><small v-if="row.error" class="error-text">{{ row.error }}</small></div></template></el-table-column>
          <el-table-column prop="chunk_count" label="知识块" width="90" align="center" />
          <el-table-column label="大小" width="100"><template #default="{row}">{{ formatSize(row.size) }}</template></el-table-column>
          <el-table-column label="更新时间" width="170"><template #default="{row}">{{ formatDate(row.updated_at) }}</template></el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{row}"><div class="row-actions">
              <el-button v-if="canQuery" link type="primary" @click="showDetail(row.id)">详情</el-button>
              <el-button v-if="canEdit" link type="primary" :disabled="isBusy(row.status)" @click="startEdit(row)">编辑</el-button>
              <el-button v-if="canReindex" link type="warning" :disabled="isBusy(row.status)" @click="handleReindex(row)">重新索引</el-button>
              <el-popconfirm v-if="canRemove" title="删除后将同时清理文本块、向量与原文件，确定继续？" width="260" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
            </div></template>
          </el-table-column>
          <template #empty><EmptyState title="暂无知识文档" description="调整筛选条件，或上传第一份校园资料" /></template>
        </el-table>
      </div>
      <div class="table-footer"><span class="table-footer__total">共 {{ total }} 条</span><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50]" layout="sizes,prev,pager,next" @current-change="loadData" @size-change="handleSizeChange" /></div>
    </section>

    <el-dialog v-model="uploadVisible" title="上传校园知识文档" width="520px" @closed="resetUpload">
      <el-form label-position="top">
        <el-form-item label="选择文件" required>
          <el-upload drag action="#" :auto-upload="false" :limit="1" :accept="allowedExtensions" :on-change="handleFileChange" :on-remove="clearSelectedFile">
            <el-icon class="upload-icon"><UploadFilled /></el-icon><div class="el-upload__text">拖拽文件到这里，或<em>点击选择</em></div><template #tip><div class="el-upload__tip">支持 Markdown、TXT、PDF、DOCX，最大 50 MB</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item label="文档标题" required><el-input v-model="uploadForm.title" maxlength="300" /></el-form-item>
        <el-form-item label="分类" required><el-input v-model="uploadForm.category" maxlength="100" placeholder="例如：教学管理" /></el-form-item>
        <el-progress v-if="uploading" :percentage="uploadProgress" :status="uploadProgress===100?'success':undefined" />
      </el-form>
      <template #footer><el-button v-if="uploading" type="danger" plain @click="cancelUpload">取消上传</el-button><el-button v-else @click="uploadVisible=false">取消</el-button><el-button type="primary" :loading="uploading" :disabled="!selectedFile || !uploadForm.title.trim() || !uploadForm.category.trim()" @click="submitUpload">开始上传</el-button></template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑文档元数据" width="520px" @closed="editFormRef?.resetFields()">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="标题" prop="title"><el-input v-model="editForm.title" maxlength="300" /></el-form-item>
        <el-form-item label="分类" prop="category"><el-input v-model="editForm.category" maxlength="100" /></el-form-item>
        <el-form-item label="来源链接"><el-input v-model="editForm.source_url" placeholder="https://…" /></el-form-item>
        <el-form-item label="发布日期"><el-date-picker v-model="editForm.published_at" value-format="YYYY-MM-DD" type="date" placeholder="选择日期" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="文档详情" size="480px">
      <el-descriptions v-if="detail" :column="1" border>
        <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item><el-descriptions-item label="原始文件">{{ detail.original_name }}</el-descriptions-item><el-descriptions-item label="MIME">{{ detail.mime_type }}</el-descriptions-item><el-descriptions-item label="大小">{{ formatSize(detail.size) }}</el-descriptions-item><el-descriptions-item label="分类">{{ detail.category }}</el-descriptions-item><el-descriptions-item label="状态"><StatusTag :label="statusInfo(detail.status).label" :tone="statusInfo(detail.status).tone" /></el-descriptions-item><el-descriptions-item label="阶段">{{ detail.stage || '—' }}</el-descriptions-item><el-descriptions-item label="知识块">{{ detail.chunk_count }}</el-descriptions-item><el-descriptions-item label="来源"><a v-if="detail.source_url" :href="detail.source_url" target="_blank" rel="noopener noreferrer">查看原文</a><span v-else>—</span></el-descriptions-item><el-descriptions-item label="发布日期">{{ detail.published_at || '—' }}</el-descriptions-item><el-descriptions-item label="上传时间">{{ formatDate(detail.created_at) }}</el-descriptions-item><el-descriptions-item v-if="detail.error" label="错误"><span class="error-text">{{ detail.error }}</span></el-descriptions-item>
      </el-descriptions>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Refresh, Search, Upload, UploadFilled } from '@element-plus/icons-vue'
import { deleteDocument, getDocument, listDocuments, reindexDocument, updateDocument, uploadDocument } from '@/api/knowledge'
import { useUserStore } from '@/stores/user'
import type { CampusDocument } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const documents = ref<CampusDocument[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const filters = reactive<{q:string;category:string;status:CampusDocument['status']|''}>({ q:'', category:'', status:'' })
const statusOptions = [
  {label:'排队中',value:'QUEUED'},{label:'处理中',value:'PROCESSING'},{label:'已完成',value:'READY'},{label:'失败',value:'FAILED'},{label:'删除中',value:'DELETING'},
] as const
const canUpload = computed(() => userStore.hasPermission('knowledge:document:upload'))
const canEdit = computed(() => userStore.hasPermission('knowledge:document:edit'))
const canRemove = computed(() => userStore.hasPermission('knowledge:document:remove'))
const canQuery = computed(() => userStore.hasPermission('knowledge:document:query'))
const canReindex = computed(() => userStore.hasPermission('knowledge:document:reindex'))
let pollTimer: ReturnType<typeof setInterval> | null = null

function statusInfo(status: CampusDocument['status']): {label:string;tone:'success'|'warning'|'danger'|'info'|'primary'} {
  return ({QUEUED:{label:'排队中',tone:'warning'},PROCESSING:{label:'处理中',tone:'primary'},READY:{label:'已完成',tone:'success'},FAILED:{label:'失败',tone:'danger'},DELETING:{label:'删除中',tone:'info'}} as const)[status]
}
function isBusy(status: CampusDocument['status']) { return ['QUEUED','PROCESSING','DELETING'].includes(status) }
function formatDate(value?: string) { return value ? value.replace('T',' ').slice(0,19) : '—' }
function formatSize(bytes: number) { if (!bytes) return '0 B'; if (bytes<1024) return `${bytes} B`; if(bytes<1048576)return `${(bytes/1024).toFixed(1)} KB`; return `${(bytes/1048576).toFixed(2)} MB` }
function fileSuffix(name: string) { return (name.split('.').pop() || 'DOC').slice(0,4).toUpperCase() }

async function loadData() {
  loading.value = true
  try {
    const response = await listDocuments({ page:page.value, size:pageSize.value, q:filters.q.trim() || undefined, category:filters.category.trim() || undefined, status_filter:filters.status || undefined })
    documents.value = response.data.items
    total.value = response.data.total
    if (documents.value.some(item => item.status==='QUEUED' || item.status==='PROCESSING')) startPolling(); else stopPolling()
  } finally { loading.value = false }
}
function startPolling(){ if(!pollTimer) pollTimer=setInterval(loadData,3000) }
function stopPolling(){ if(pollTimer){clearInterval(pollTimer);pollTimer=null} }
function applyFilters(){ page.value=1; loadData() }
function resetFilters(){ filters.q='';filters.category='';filters.status='';page.value=1;loadData() }
function handleSizeChange(){ page.value=1;loadData() }

const uploadVisible=ref(false),uploading=ref(false),uploadProgress=ref(0),selectedFile=ref<File|null>(null)
const uploadForm=reactive({title:'',category:''})
const allowedExtensions='.md,.txt,.pdf,.docx'
let uploadController: AbortController|null=null
function openUploadDialog(){ uploadVisible.value=true }
function handleFileChange(file:UploadFile){
  if(!file.raw)return
  const extension=file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if(!['.md','.txt','.pdf','.docx'].includes(extension)){selectedFile.value=null;ElMessage.error('仅支持 Markdown、TXT、PDF、DOCX 文件');return}
  if(file.raw.size>50*1024*1024){selectedFile.value=null;ElMessage.error('文件不能超过 50 MB');return}
  selectedFile.value=file.raw;uploadForm.title=file.name.replace(/\.[^.]+$/,'')
}
function clearSelectedFile(){ selectedFile.value=null; uploadForm.title='' }
function resetUpload(){ if(uploading.value)return; selectedFile.value=null;uploadForm.title='';uploadForm.category='';uploadProgress.value=0 }
function cancelUpload(){ uploadController?.abort() }
async function submitUpload(){
  if(!selectedFile.value)return
  uploading.value=true;uploadProgress.value=0;uploadController=new AbortController()
  const form=new FormData();form.append('file',selectedFile.value);form.append('title',uploadForm.title.trim());form.append('category',uploadForm.category.trim())
  try{const response=await uploadDocument(form,{signal:uploadController.signal,onProgress:value=>uploadProgress.value=value});ElMessage.success(`上传成功，任务 #${response.data.job_id} 已进入处理队列`);uploadVisible.value=false;await loadData()}
  catch(error){if(uploadController.signal.aborted)ElMessage.info('已取消本次上传')}
  finally{uploading.value=false;uploadController=null}
}

const editVisible=ref(false),saving=ref(false),editingId=ref<number|null>(null),editFormRef=ref()
const editForm=reactive({title:'',category:'',source_url:'',published_at:''})
const editRules={title:[{required:true,message:'请输入标题',trigger:'blur'}],category:[{required:true,message:'请输入分类',trigger:'blur'}]}
function startEdit(document:CampusDocument){editingId.value=document.id;Object.assign(editForm,{title:document.title,category:document.category,source_url:document.source_url||'',published_at:document.published_at||''});editVisible.value=true}
async function saveEdit(){if(!(await editFormRef.value?.validate().catch(()=>false))||editingId.value==null)return;saving.value=true;try{await updateDocument(editingId.value,{title:editForm.title.trim(),category:editForm.category.trim(),source_url:editForm.source_url||undefined,published_at:editForm.published_at||undefined});ElMessage.success('文档信息已更新');editVisible.value=false;await loadData()}finally{saving.value=false}}
const detailVisible=ref(false),detail=ref<CampusDocument|null>(null)
async function showDetail(id:number){detail.value=(await getDocument(id)).data;detailVisible.value=true}
async function handleDelete(id:number){await deleteDocument(id);ElMessage.success('文档已删除');await loadData()}
async function handleReindex(document:CampusDocument){const response=await reindexDocument(document.id);ElMessage.success(`重新索引任务 #${response.data.job_id} 已创建`);await loadData()}

onMounted(loadData)
onBeforeUnmount(()=>{stopPolling();uploadController?.abort()})
</script>

<style scoped>
.document-cell{display:flex;align-items:center;gap:12px}.file-icon{display:grid;width:38px;height:42px;place-items:center;color:var(--brand);background:var(--brand-soft);border-radius:8px;font-size:10px;font-weight:800}.document-cell>div{display:flex;min-width:0;flex-direction:column}.document-cell strong{overflow:hidden;color:var(--text);text-overflow:ellipsis;white-space:nowrap}.document-cell small{margin-top:4px;overflow:hidden;color:var(--text-muted);text-overflow:ellipsis;white-space:nowrap}.status-column{display:flex;align-items:flex-start;flex-direction:column;gap:4px}.status-column small{max-width:160px;color:var(--text-muted);font-size:10px}.error-text{color:#e04a4a!important}.row-actions{display:flex;align-items:center;white-space:nowrap}.upload-icon{margin-bottom:10px;color:var(--brand);font-size:42px}.knowledge-page :deep(.el-upload),.knowledge-page :deep(.el-upload-dragger){width:100%}
@media(max-width:640px){.table-footer :deep(.el-pagination__sizes){display:none}}
</style>
