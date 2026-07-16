<template>
  <div>
    <div class="page-header">
      <h3>知识文档管理</h3>
      <el-button type="primary" :icon="Plus" @click="openDialog()" v-if="userStore.hasPermission('knowledge:document:add')">新增文档</el-button>
      <el-button :icon="Download" @click="handleExport" v-if="userStore.hasPermission('knowledge:document:export')">导出</el-button>
      <el-button :icon="Upload" @click="handleImport" v-if="userStore.hasPermission('knowledge:document:import')">导入</el-button>
    </div>

    <!-- 搜索 -->
    <div class="search-bar">
      <el-input v-model="search.title" placeholder="文档标题" clearable @clear="loadData" @keyup.enter="loadData" />
      <el-select v-model="search.categoryId" placeholder="分类" clearable @change="loadData" style="width:180px">
        <el-option v-for="c in categories" :key="c.categoryId" :label="c.categoryName" :value="c.categoryId" />
      </el-select>
      <el-select v-model="search.status" placeholder="状态" clearable @change="loadData" style="width:120px">
        <el-option label="已发布" value="1" />
        <el-option label="草稿" value="0" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
      <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
    </div>

    <!-- 表格 -->
    <div class="campus-card">
      <el-table :data="documents" v-loading="loading" stripe>
        <el-table-column prop="docId" label="ID" width="80" align="center" />
        <el-table-column prop="title" label="文档标题" min-width="240" show-overflow-tooltip />
        <el-table-column label="分类" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ getCategoryName(row.categoryId) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="keywords" label="关键词" width="160" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="cell-status">
              <span :class="['dot', row.status === '1' ? 'dot--green' : 'dot--gray']"></span>
              {{ row.status === '1' ? '已发布' : '草稿' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="viewCount" label="浏览" width="80" align="center" />
        <el-table-column prop="updateTime" label="更新时间" width="170">
          <template #default="{ row }">{{ row.updateTime?.replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="View" @click="showDetail(row)"
              v-if="userStore.hasPermission('knowledge:document:query')">查看</el-button>
            <el-button type="primary" link size="small" :icon="Edit" @click="openDialog(row)"
              v-if="userStore.hasPermission('knowledge:document:edit')">编辑</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)"
              v-if="userStore.hasPermission('knowledge:document:remove')">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:16px;display:flex;justify-content:flex-end">
        <el-pagination
          v-model:current-page="page.pageNum" v-model:page-size="page.pageSize"
          :total="page.total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next"
          @current-change="loadData" @size-change="loadData" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog :title="editId ? '编辑文档' : '新增文档'" v-model="dialogVisible" width="780px" top="5vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分类" prop="categoryId">
              <el-select v-model="form.categoryId" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categories" :key="c.categoryId" :label="c.categoryName" :value="c.categoryId" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关键词">
              <el-input v-model="form.keywords" placeholder="多个关键词用逗号分隔" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="来源URL">
          <el-input v-model="form.sourceUrl" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="文档内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="14" placeholder="支持 Markdown 格式" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看详情弹窗 -->
    <el-dialog title="文档详情" v-model="detailVisible" width="760px" top="5vh">
      <div v-if="detail" class="detail-content">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="分类">{{ getCategoryName(detail.categoryId) }}</el-descriptions-item>
          <el-descriptions-item label="关键词">{{ detail.keywords || '-' }}</el-descriptions-item>
          <el-descriptions-item label="浏览">{{ detail.viewCount }}</el-descriptions-item>
          <el-descriptions-item label="来源" :span="2">{{ detail.sourceUrl || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="content-preview" v-html="renderMarkdown(detail.content || '')" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { listDocument, getDocument, addDocument, updateDocument, deleteDocuments } from '@/api/knowledge'
import { categoryTree } from '@/api/knowledge'
import type { KnowledgeDocument, KnowledgeCategory } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, Refresh, View, Download, Upload } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const userStore = useUserStore()
const documents = ref<KnowledgeDocument[]>([])
const categories = ref<KnowledgeCategory[]>([])
const loading = ref(false)

const search = reactive({ title: '', categoryId: null as number | null, status: null as string | null })
const page = reactive({ pageNum: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref()
const form = ref<KnowledgeDocument>({ docId: 0, title: '', categoryId: 0, content: '', sourceUrl: '', keywords: '', status: '1', viewCount: 0, createTime: '', updateTime: '' })
const rules = {
  title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }],
  categoryId: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入文档内容', trigger: 'blur' }]
}

const detailVisible = ref(false)
const detail = ref<KnowledgeDocument | null>(null)

function getCategoryName(id: number) {
  return categories.value.find(c => c.categoryId === id)?.categoryName || '-'
}

function renderMarkdown(text: string) {
  return DOMPurify.sanitize(marked.parse(text) as string)
}

function handleExport() {
  ElMessage.info('导出功能开发中')
}

function handleImport() {
  ElMessage.info('导入功能开发中')
}

async function loadCategories() {
  const res = await categoryTree()
  categories.value = res.data
}

async function loadData() {
  loading.value = true
  try {
    const res = await listDocument({ ...search, ...page })
    documents.value = res.data.rows
    page.total = res.data.total
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  search.title = ''; search.categoryId = null; search.status = null
  page.pageNum = 1
  loadData()
}

function openDialog(row?: KnowledgeDocument) {
  editId.value = row?.docId || null
  form.value = row ? { ...row } : { docId: 0, title: '', categoryId: categories.value[0]?.categoryId || 0, content: '', sourceUrl: '', keywords: '', status: '1', viewCount: 0, createTime: '', updateTime: '' }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editId.value) {
      await updateDocument(form.value)
      ElMessage.success('修改成功')
    } else {
      await addDocument(form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

async function showDetail(row: KnowledgeDocument) {
  const res = await getDocument(row.docId)
  detail.value = res.data
  detailVisible.value = true
}

function handleDelete(row: KnowledgeDocument) {
  ElMessageBox.confirm(`确定删除文档「${row.title}」吗？`, '警告', { type: 'warning' })
    .then(async () => {
      await deleteDocuments([row.docId])
      ElMessage.success('删除成功')
      loadData()
    })
}

onMounted(() => { loadCategories(); loadData() })
</script>

<style scoped>
.detail-content { max-height: 65vh; overflow-y: auto; }
.content-preview { margin-top: 16px; padding: 20px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; line-height: 1.8; font-size: 14px; }
</style>
