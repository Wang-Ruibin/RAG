<template>
  <div class="page-shell knowledge-page">
    <PageHeader title="知识库管理" description="管理知识库文档，支持文档上传、处理、检索与维护">
      <template #actions><el-button v-if="canUpload" type="primary" :icon="Upload" @click="openUploadDialog">上传文档</el-button></template>
    </PageHeader>

    <FilterCard>
      <label class="filter-field"><span>分类：</span><el-select v-model="filters.category" placeholder="全部分类" clearable style="width:190px" @change="applyFilters">
        <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
      </el-select></label>
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
          <el-table-column label="状态 / 进度" width="200"><template #default="{row}"><div class="status-column">
            <StatusTag :label="statusInfo(row.status).label" :tone="statusInfo(row.status).tone" />
            <el-progress v-if="isProcessing(row) || deletingId===row.id"
              :percentage="deletingId===row.id ? deletePercent : (smoothPercent[row.id] ?? 0)"
              :stroke-width="6" :show-text="false"
              style="width:100%;margin-top:4px" />
            <small v-if="isProcessing(row)">{{ stageText(row.stage) }}</small>
            <small v-if="deletingId===row.id">删除中 {{ Math.round(deletePercent) }}%</small>
            <small v-if="row.error" class="error-text">{{ row.error }}</small>
          </div></template></el-table-column>
          <el-table-column prop="chunk_count" label="知识块" width="90" align="center" />
          <el-table-column label="大小" width="100"><template #default="{row}">{{ formatSize(row.size) }}</template></el-table-column>
          <el-table-column label="更新时间" width="170"><template #default="{row}">{{ formatDate(row.updated_at) }}</template></el-table-column>
          <el-table-column label="操作" width="250" fixed="right">
            <template #default="{row}"><div class="row-actions">
              <el-button v-if="canQuery" link type="primary" @click="showDetail(row.id)">详情</el-button>
              <el-button v-if="canEdit" link type="primary" :disabled="isBusy(row.status)" @click="startEdit(row)">编辑</el-button>
              <el-button v-if="canReindex" link type="warning" :disabled="isBusy(row.status)" @click="handleReindex(row)">重新索引</el-button>
              <el-popconfirm v-if="canRemove" title="删除后将同时清理文本块、向量与原文件，确定继续？" width="260" @confirm="handleDelete(row.id)"><template #reference><el-button link type="danger" :loading="deletingId===row.id" :disabled="deletingId!==null">删除</el-button></template></el-popconfirm>
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
        <el-form-item label="分类" required><el-select v-model="uploadForm.category" placeholder="选择分类" style="width:100%">
        <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
      </el-select></el-form-item>
        <div v-if="uploading" class="upload-progress-bar"><el-progress :percentage="uploadProgress" :stroke-width="8" :status="uploadProgress===100?'success':undefined" :striped="uploadProgress<100" :striped-flow="uploadProgress<100" /><span class="upload-progress-text">{{ uploadProgress < 100 ? `上传中 ${uploadProgress}%` : '上传完成，等待处理…' }}</span></div>
      </el-form>
      <template #footer><el-button v-if="uploading" type="danger" plain @click="cancelUpload">取消上传</el-button><el-button v-else @click="uploadVisible=false">取消</el-button><el-button type="primary" :loading="uploading" :disabled="!selectedFile || !uploadForm.title.trim() || !uploadForm.category.trim()" @click="submitUpload">开始上传</el-button></template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑文档元数据" width="520px" @closed="editFormRef?.resetFields()">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="标题" prop="title"><el-input v-model="editForm.title" maxlength="300" /></el-form-item>
        <el-form-item label="分类" prop="category"><el-select v-model="editForm.category" placeholder="选择分类" style="width:100%">
        <el-option v-for="c in CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
      </el-select></el-form-item>
        <el-form-item label="来源链接"><el-input v-model="editForm.source_url" placeholder="https://…" /></el-form-item>
        <el-form-item label="发布日期"><el-date-picker v-model="editForm.published_at" value-format="YYYY-MM-DD" type="date" placeholder="选择日期" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="文档详情" size="640px">
      <template v-if="detail">
        <el-tabs v-model="detailTab" class="detail-tabs">
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item><el-descriptions-item label="原始文件">{{ detail.original_name }}</el-descriptions-item><el-descriptions-item label="MIME">{{ detail.mime_type }}</el-descriptions-item><el-descriptions-item label="大小">{{ formatSize(detail.size) }}</el-descriptions-item><el-descriptions-item label="分类">{{ detail.category }}</el-descriptions-item><el-descriptions-item label="状态"><StatusTag :label="statusInfo(detail.status).label" :tone="statusInfo(detail.status).tone" /></el-descriptions-item><el-descriptions-item label="阶段">{{ detail.stage || '—' }}</el-descriptions-item><el-descriptions-item label="知识块">{{ detail.chunk_count }}</el-descriptions-item><el-descriptions-item label="来源"><a v-if="detail.source_url" :href="detail.source_url" target="_blank" rel="noopener noreferrer">查看原文</a><span v-else>—</span></el-descriptions-item><el-descriptions-item label="发布日期">{{ detail.published_at || '—' }}</el-descriptions-item><el-descriptions-item label="上传时间">{{ formatDate(detail.created_at) }}</el-descriptions-item><el-descriptions-item v-if="detail.error" label="错误"><span class="error-text">{{ detail.error }}</span></el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
          <el-tab-pane label="内容预览" name="preview" :disabled="detail.status !== 'READY'">
            <div v-if="previewLoading" v-loading="previewLoading" style="min-height:200px" />
            <template v-else-if="preview">
              <div class="preview-meta">
                <span class="preview-format"><el-tag size="small">{{ preview.format }}</el-tag></span>
                <span class="preview-chars">已显示 {{ preview.offset + preview.content.length }} / {{ preview.total_chars }} 字符</span>
              </div>
              <div v-if="preview.format === 'md'" class="markdown-body preview-content" v-html="renderPreviewMarkdown(preview.content)" />
              <pre v-else class="preview-plaintext">{{ preview.content }}</pre>
              <div v-if="preview.has_more" class="preview-more">
                <el-button :loading="previewLoadingMore" :icon="Download" @click="loadMorePreview">加载更多内容</el-button>
              </div>
            </template>
            <div v-else-if="!previewLoading && detail.status === 'READY'" class="preview-placeholder">
              <el-button type="primary" :icon="View" @click="loadPreview">查看文档内容</el-button>
            </div>
            <div v-else class="preview-placeholder">
              <el-icon><WarningFilled /></el-icon>
              <p>文档处理完成后即可预览内容</p>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { UploadFile } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Download, Refresh, Search, Upload, UploadFilled, View, WarningFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { deleteDocument, getDocument, listDocuments, previewDocument, reindexDocument, updateDocument, uploadDocument } from '@/api/knowledge'
import { useUserStore } from '@/stores/user'
import type { CampusDocument, DocumentPreview } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const CATEGORIES = [
  { label: '校园信息', value: 'campus_info' },
  { label: '政策制度', value: 'policy' },
  { label: '办事流程', value: 'flow' },
  { label: '新闻动态', value: 'news' },
  { label: '综合', value: 'general' },
] as const

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
const deletingId = ref<number | null>(null)
const deletePercent = ref(0)
let deleteTimer: ReturnType<typeof setInterval> | null = null
let pollTimer: ReturnType<typeof setInterval> | null = null

// 平滑进度：基于时间的减速曲线，decouple 后端 stage 跳变
const smoothPercent = reactive<Record<number, number>>({})
const docSeenAt = reactive<Record<number, number>>({})
let smoothTimer: ReturnType<typeof setInterval> | null = null

function isProcessing(row: CampusDocument) { return row.status === 'QUEUED' || row.status === 'PROCESSING' }

function stageText(stage: string): string {
  const map: Record<string, string> = { SAVED: '已保存，等待处理', EXTRACTING: '解析文档…', CLEANING: '清洗文本…', CHUNKING: '切片中…', EMBEDDING: '生成向量…', INDEXING: '写入向量库…', COMPLETE: '处理完成' }
  return map[stage] || stage
}

/** 时间驱动目标值：14s 到 ~90%，之后减速逼近 95%，COMPLETE 跳到 100% */
function timeTarget(docId: number, stage: string): number {
  if (stage === 'COMPLETE') return 100
  const elapsed = (Date.now() - (docSeenAt[docId] ?? Date.now())) / 1000
  // 95 * (1 - e^(-t/5))：5s→60%, 10s→82%, 14s→89%, 20s→93%
  return Math.round(95 * (1 - Math.exp(-elapsed / 5)))
}

function seedProgress(docs: CampusDocument[]) {
  const now = Date.now()
  for (const doc of docs) {
    if (!isProcessing(doc)) continue
    if (!(doc.id in docSeenAt)) docSeenAt[doc.id] = now
    const target = timeTarget(doc.id, doc.stage)
    if (!(doc.id in smoothPercent)) smoothPercent[doc.id] = 2
    smoothPercent[doc.id] = Math.max(smoothPercent[doc.id], target - 4) // 允许小步追赶
  }
  // 清理已完成的
  for (const id of Object.keys(smoothPercent)) {
    if (!docs.some(d => d.id === Number(id) && isProcessing(d))) {
      delete smoothPercent[Number(id)]
      delete docSeenAt[Number(id)]
    }
  }
  // 平滑动画
  if (!smoothTimer && Object.keys(smoothPercent).length) {
    smoothTimer = setInterval(() => {
      let active = false
      for (const id of Object.keys(smoothPercent)) {
        const cur = smoothPercent[Number(id)] ?? 0
        const doc = documents.value.find(d => d.id === Number(id))
        const tgt = doc ? timeTarget(Number(id), doc.stage) : 100
        if (cur < tgt) {
          // ease-out: 越接近目标越慢
          smoothPercent[Number(id)] = cur + Math.max(0.15, (tgt - cur) * 0.06)
          active = true
        } else if (tgt === 100 && cur < 100) {
          smoothPercent[Number(id)] = 100
        }
      }
      if (!active) { clearInterval(smoothTimer!); smoothTimer = null }
    }, 120)
  }
}

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
    seedProgress(documents.value)
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
const editRules={title:[{required:true,message:'请输入标题',trigger:'blur'}],category:[{required:true,message:'请选择分类',trigger:'change'}]}
function startEdit(document:CampusDocument){editingId.value=document.id;Object.assign(editForm,{title:document.title,category:document.category,source_url:document.source_url||'',published_at:document.published_at||''});editVisible.value=true}
async function saveEdit(){if(!(await editFormRef.value?.validate().catch(()=>false))||editingId.value==null)return;saving.value=true;try{await updateDocument(editingId.value,{title:editForm.title.trim(),category:editForm.category.trim(),source_url:editForm.source_url||undefined,published_at:editForm.published_at||undefined});ElMessage.success('文档信息已更新');editVisible.value=false;await loadData()}finally{saving.value=false}}
const detailVisible=ref(false),detail=ref<CampusDocument|null>(null)
const detailTab=ref('info')
const preview=ref<DocumentPreview|null>(null)
const previewLoading=ref(false),previewLoadingMore=ref(false)

function renderPreviewMarkdown(value: string) { return DOMPurify.sanitize(marked.parse(value || '') as string) }

async function loadPreview() {
  if (!detail.value) return
  previewLoading.value = true
  try {
    const res = await previewDocument(detail.value.id)
    preview.value = res.data
  } catch { preview.value = null; ElMessage.error('加载预览失败') }
  finally { previewLoading.value = false }
}

async function loadMorePreview() {
  if (!detail.value || !preview.value) return
  previewLoadingMore.value = true
  try {
    const res = await previewDocument(detail.value.id, preview.value.offset + preview.value.limit)
    preview.value = { ...res.data, content: preview.value.content + res.data.content }
  } catch { ElMessage.error('加载更多内容失败') }
  finally { previewLoadingMore.value = false }
}

watch(detailVisible, v => { if (!v) { detailTab.value = 'info'; preview.value = null } })
async function showDetail(id:number){detail.value=(await getDocument(id)).data;detailVisible.value=true}
async function handleDelete(id:number){
  if(deletingId.value!==null) return
  deletingId.value=id
  deletePercent.value=0
  const delStart=Date.now()
  deleteTimer=setInterval(()=>{
    const elapsed=(Date.now()-delStart)/1000
    deletePercent.value=Math.round(95*(1-Math.exp(-elapsed/5)))
    if(deletePercent.value>=94){clearInterval(deleteTimer!);deleteTimer=null}
  },100)
  try{await deleteDocument(id);deletePercent.value=100;await new Promise(r=>setTimeout(r,400));ElMessage.success('文档已删除');await loadData()}
  catch{ElMessage.error('删除失败')}
  finally{deletingId.value=null;if(deleteTimer){clearInterval(deleteTimer);deleteTimer=null};deletePercent.value=0}
}
async function handleReindex(document:CampusDocument){const response=await reindexDocument(document.id);ElMessage.success(`重新索引任务 #${response.data.job_id} 已创建`);await loadData()}

onMounted(loadData)
onBeforeUnmount(()=>{stopPolling();uploadController?.abort();if(smoothTimer){clearInterval(smoothTimer);smoothTimer=null}})
</script>

<style scoped>
.document-cell{display:flex;align-items:center;gap:12px}.file-icon{display:grid;width:38px;height:42px;place-items:center;color:var(--brand);background:var(--brand-soft);border-radius:8px;font-size:10px;font-weight:800}.document-cell>div{display:flex;min-width:0;flex-direction:column}.document-cell strong{overflow:hidden;color:var(--text);text-overflow:ellipsis;white-space:nowrap}.document-cell small{margin-top:4px;overflow:hidden;color:var(--text-muted);text-overflow:ellipsis;white-space:nowrap}.status-column{display:flex;align-items:flex-start;flex-direction:column;gap:4px}.status-column small{max-width:160px;color:var(--text-muted);font-size:10px}.error-text{color:#e04a4a!important}.row-actions{display:flex;align-items:center;white-space:nowrap}.upload-icon{margin-bottom:10px;color:var(--brand);font-size:42px}.upload-progress-bar{margin-top:6px;padding:12px 0}.upload-progress-text{display:block;margin-top:6px;color:var(--text-muted);font-size:12px;text-align:center}.knowledge-page :deep(.el-upload),.knowledge-page :deep(.el-upload-dragger){width:100%}
.detail-tabs{margin-top:-8px}.detail-tabs :deep(.el-tabs__header){margin-bottom:16px}
.preview-meta{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.preview-chars{color:var(--text-muted);font-size:12px}
.preview-plaintext{max-height:420px;overflow:auto;padding:16px;color:var(--text);background:var(--surface-soft);border:1px solid var(--border);border-radius:var(--radius);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px;line-height:1.7;white-space:pre-wrap;word-break:break-word}
.preview-content{max-height:420px;overflow:auto;padding:2px 0}
.preview-more{display:flex;justify-content:center;padding:12px 0 0}
.preview-placeholder{display:flex;min-height:200px;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:var(--text-muted)}
@media(max-width:640px){.table-footer :deep(.el-pagination__sizes){display:none}}
</style>
