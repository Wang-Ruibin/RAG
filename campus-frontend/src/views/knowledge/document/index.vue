<template>
  <div>
    <div class="page-header">
      <h3>知识库管理</h3>
      <span class="header-meta">共 {{ total }} 篇文档，处理完成后参与问答</span>
    </div>

    <!-- 搜索 -->
    <div class="search-bar">
      <el-input v-model="query" placeholder="搜索文档标题" clearable @keyup.enter="loadData" @clear="loadData" style="width:260px">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
      <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
    </div>

    <!-- 上传区域 -->
    <div class="upload-card">
      <el-upload
        class="upload-dragger"
        drag
        action="#"
        :auto-upload="true"
        :http-request="handleUpload"
        :accept="'.md,.txt,.pdf,.docx'"
        :show-file-list="false"
        :disabled="uploading"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">点击或拖拽校园资料到这里</div>
        <div class="upload-hint">支持 Markdown、TXT、PDF、DOCX，单文件最大 50MB</div>
        <div v-if="uploading" class="upload-progress">
          <el-icon class="is-loading"><Loading /></el-icon> 上传中...
        </div>
      </el-upload>
    </div>

    <!-- 文档表格 -->
    <div class="campus-card">
      <el-table :data="documents" v-loading="loading" row-key="id" stripe>
        <el-table-column label="文档" min-width="240">
          <template #default="{ row }">
            <div class="doc-title-cell">
              <strong>{{ row.title }}</strong>
              <span class="doc-filename">{{ row.original_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="200">
          <template #default="{ row }">
            <div class="status-cell">
              <span :class="['status-tag', statusStyle(row.status).cls]">{{ statusStyle(row.status).label }}</span>
              <el-progress
                v-if="row.status === 'QUEUED' || row.status === 'PROCESSING'"
                :percentage="stagePercent(row.stage)"
                :show-text="false"
                :stroke-width="5"
                style="margin-top:4px"
              />
              <span v-if="row.error" class="status-error-text">{{ row.error }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="切块" width="70" align="center" />
        <el-table-column label="大小" width="90" align="center">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ row.updated_at?.replace('T', ' ').substring(0, 19) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="View" @click="showDetail(row.id)">查看</el-button>
            <el-button type="primary" link size="small" :icon="Edit" @click="startEdit(row)"
              :disabled="row.status === 'QUEUED' || row.status === 'PROCESSING' || row.status === 'DELETING'">编辑</el-button>
            <el-button type="warning" link size="small" :icon="RefreshRight" @click="handleReindex(row)"
              :disabled="row.status === 'QUEUED' || row.status === 'PROCESSING' || row.status === 'DELETING'">索引</el-button>
            <el-popconfirm title="确定删除此文档？将同时清除知识库中的文本块和向量数据" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link size="small" :icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top:16px;display:flex;justify-content:flex-end">
        <el-pagination
          v-model:current-page="page" v-model:page-size="pageSize"
          :total="total" :page-sizes="[10,20,50]"
          layout="total,sizes,prev,pager,next"
          @current-change="loadData" @size-change="loadData" />
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog title="编辑知识库资料" v-model="editVisible" width="500px" top="8vh" @closed="editFormRef?.resetFields()">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="80px" @submit.prevent="saveEdit">
        <el-form-item label="标题" prop="title">
          <el-input v-model="editForm.title" maxlength="300" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-input v-model="editForm.category" maxlength="100" placeholder="如：校园制度、学术科研" />
        </el-form-item>
        <el-form-item label="来源链接">
          <el-input v-model="editForm.source_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-input v-model="editForm.published_at" type="date" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer title="文档详情" v-model="detailVisible" size="480px">
      <template v-if="detail">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="原始文件">{{ detail.original_name }}</el-descriptions-item>
          <el-descriptions-item label="MIME 类型">{{ detail.mime_type }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatSize(detail.size) }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ detail.category }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <span :class="['status-tag', statusStyle(detail.status).cls]">{{ statusStyle(detail.status).label }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="处理阶段">{{ detail.stage }}</el-descriptions-item>
          <el-descriptions-item label="知识块数">{{ detail.chunk_count }}</el-descriptions-item>
          <el-descriptions-item label="来源链接">
            <a v-if="detail.source_url" :href="detail.source_url" target="_blank">打开原文</a>
            <span v-else>无</span>
          </el-descriptions-item>
          <el-descriptions-item label="发布日期">{{ detail.published_at || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ detail.created_at?.replace('T', ' ').substring(0, 19) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail.updated_at?.replace('T', ' ').substring(0, 19) }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.error" label="错误信息">
            <span style="color:var(--dot-red)">{{ detail.error }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useUserStore } from '@/stores/user'
import { listDocuments, getDocument, uploadDocument, updateDocument, deleteDocument, reindexDocument } from '@/api/knowledge'
import type { CampusDocument } from '@/types'
import { ElMessage } from 'element-plus'
import { Search, Refresh, View, Edit, Delete, UploadFilled, Loading, RefreshRight } from '@element-plus/icons-vue'

const userStore = useUserStore()
const documents = ref<CampusDocument[]>([])
const total = ref(0)
const loading = ref(false)
const query = ref('')
const page = ref(1)
const pageSize = ref(10)
const uploading = ref(false)

// 自动轮询
let pollTimer: ReturnType<typeof setInterval> | null = null
const hasProcessing = computed(() => documents.value.some(d => d.status === 'QUEUED' || d.status === 'PROCESSING'))

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (hasProcessing.value) loadData()
    else stopPolling()
  }, 2500)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// 状态映射
const statusMap: Record<string, { label: string; cls: string }> = {
  QUEUED: { label: '排队中', cls: 'status-queued' },
  PROCESSING: { label: '处理中', cls: 'status-processing' },
  READY: { label: '已完成', cls: 'status-ready' },
  FAILED: { label: '失败', cls: 'status-failed' },
  DELETING: { label: '删除中', cls: 'status-deleting' },
}
function statusStyle(s: string) { return statusMap[s] || { label: s, cls: '' } }

// 处理阶段百分比
const stageMap: Record<string, number> = {
  SAVED: 10, EXTRACTING: 25, CLEANING: 40, CHUNKING: 55, EMBEDDING: 75, INDEXING: 90, COMPLETE: 100,
}
function stagePercent(s: string) { return stageMap[s] || 5 }

function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// 数据加载
async function loadData() {
  loading.value = true
  try {
    const res = await listDocuments({ page: page.value, size: pageSize.value, q: query.value || undefined })
    documents.value = res.data.items
    total.value = res.data.total
    if (hasProcessing.value) startPolling()
  } finally {
    loading.value = false
  }
}
function resetSearch() { query.value = ''; page.value = 1; loadData() }

// 上传
async function handleUpload({ file }: { file: File }) {
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('文件不能超过 50MB')
    return
  }
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('title', file.name.replace(/\.[^.]+$/, ''))
    form.append('category', '其他')
    await uploadDocument(form)
    ElMessage.success('上传成功，正在后台处理')
    await loadData()
  } catch {
    // 具体错误信息（如"相同内容已存在"）由 request.ts 拦截器统一弹出
  } finally {
    uploading.value = false
  }
}

// 编辑
const editVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const editFormRef = ref()
const editForm = ref({ title: '', category: '', source_url: '', published_at: '' })
const editRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  category: [{ required: true, message: '请输入分类', trigger: 'blur' }],
}

function startEdit(doc: CampusDocument) {
  editingId.value = doc.id
  editForm.value = {
    title: doc.title,
    category: doc.category,
    source_url: doc.source_url || '',
    published_at: doc.published_at || '',
  }
  editVisible.value = true
}

async function saveEdit() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid || editingId.value == null) return
  saving.value = true
  try {
    await updateDocument(editingId.value, {
      title: editForm.value.title,
      category: editForm.value.category,
      source_url: editForm.value.source_url || undefined,
      published_at: editForm.value.published_at || undefined,
    })
    ElMessage.success('保存成功')
    editVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

// 详情
const detailVisible = ref(false)
const detail = ref<CampusDocument | null>(null)
async function showDetail(id: number) {
  try {
    const res = await getDocument(id)
    detail.value = res.data
    detailVisible.value = true
  } catch { /* ignore */ }
}

// 操作
async function handleDelete(id: number) {
  try {
    await deleteDocument(id)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* ignore */ }
}

async function handleReindex(doc: CampusDocument) {
  try {
    await reindexDocument(doc.id)
    ElMessage.success('已加入重新处理队列')
    await loadData()
  } catch { /* ignore */ }
}

onMounted(loadData)
onUnmounted(stopPolling)
</script>

<style scoped lang="scss">
.header-meta {
  font-size: 13px;
  color: var(--text-secondary);
  margin-left: auto;
}

// 上传卡片
.upload-card {
  margin-bottom: 20px;
  animation: rise-in 0.45s cubic-bezier(0.22, 1, 0.36, 1) 0.06s both;
}
.upload-dragger {
  :deep(.el-upload-dragger) {
    background: var(--bg-card);
    border: 2px dashed var(--border);
    border-radius: 16px;
    padding: 32px;
    transition: all 0.22s ease;
    &:hover { border-color: var(--accent); background: var(--accent-subtle); }
  }
  .upload-icon {
    font-size: 40px;
    color: var(--accent);
    margin-bottom: 8px;
  }
  .upload-text {
    font-size: 15px;
    font-weight: 600;
    color: var(--primary);
    margin-bottom: 4px;
  }
  .upload-hint {
    font-size: 12px;
    color: var(--text-secondary);
  }
  .upload-progress {
    margin-top: 8px;
    font-size: 13px;
    color: var(--accent);
  }
}

// 文档标题列
.doc-title-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  strong { font-size: 14px; color: var(--primary); }
  .doc-filename {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

// 状态标签
.status-cell {
  display: flex;
  flex-direction: column;
}
.status-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  width: fit-content;

  &.status-queued { background: #FEF3C7; color: #B45309; }
  &.status-processing { background: #DBEAFE; color: #1D4ED8; }
  &.status-ready { background: #D1FAE5; color: #047857; }
  &.status-failed { background: #FEE2E2; color: #B91C1C; }
  &.status-deleting { background: #F1F5F9; color: #64748B; }
}
.status-error-text {
  font-size: 11px;
  color: var(--dot-red);
  margin-top: 2px;
}
</style>
