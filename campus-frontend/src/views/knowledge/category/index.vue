<template>
  <div>
    <div class="page-header">
      <h3>知识分类管理</h3>
      <el-button type="primary" :icon="Plus" @click="openDialog()" v-if="userStore.hasPermission('knowledge:category:add')">新增分类</el-button>
      <el-button :icon="Download" @click="handleExport" v-if="userStore.hasPermission('knowledge:category:export')">导出</el-button>
    </div>

    <div class="campus-card">
      <el-table :data="categories" v-loading="loading" row-key="categoryId" default-expand-all>
        <el-table-column prop="categoryName" label="分类名称" min-width="180">
          <template #default="{ row }">
            <el-icon v-if="row.icon" style="margin-right:6px"><component :is="row.icon" /></el-icon>
            {{ row.categoryName }}
          </template>
        </el-table-column>
        <el-table-column prop="categoryKey" label="标识" width="140" />
        <el-table-column prop="sortOrder" label="排序" width="80" align="center" />
        <el-table-column prop="docCount" label="文档数" width="100" align="center">
          <template #default="{ row }">
            <span class="tnum">{{ row.docCount || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="180">
          <template #default="{ row }">{{ row.createTime?.replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="Edit" @click="openDialog(row)"
              v-if="userStore.hasPermission('knowledge:category:edit')">编辑</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)"
              v-if="userStore.hasPermission('knowledge:category:remove')">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog :title="editId ? '编辑分类' : '新增分类'" v-model="dialogVisible" width="500px" top="10vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="分类名称" prop="categoryName">
          <el-input v-model="form.categoryName" placeholder="请输入分类名称" />
        </el-form-item>
        <el-form-item label="分类标识" prop="categoryKey">
          <el-input v-model="form.categoryKey" placeholder="如 academic / news" :disabled="!!editId" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sortOrder" :min="0" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="Element Plus 图标名" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { listCategory, addCategory, updateCategory, deleteCategories } from '@/api/knowledge'
import type { KnowledgeCategory } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Download } from '@element-plus/icons-vue'

const userStore = useUserStore()
const categories = ref<KnowledgeCategory[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref()

const form = ref<KnowledgeCategory>({ categoryId: 0, parentId: 0, categoryName: '', categoryKey: '', sortOrder: 0, icon: '' })
const rules = {
  categoryName: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  categoryKey: [{ required: true, message: '请输入分类标识', trigger: 'blur' }]
}

function handleExport() {
  ElMessage.info('导出功能开发中')
}

async function loadData() {
  loading.value = true
  try {
    const res = await listCategory()
    categories.value = res.data
  } finally {
    loading.value = false
  }
}

function openDialog(row?: KnowledgeCategory) {
  editId.value = row?.categoryId || null
  form.value = row ? { ...row } : { categoryId: 0, parentId: 0, categoryName: '', categoryKey: '', sortOrder: 0, icon: '' }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editId.value) {
      await updateCategory(form.value)
      ElMessage.success('修改成功')
    } else {
      await addCategory(form.value)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function handleDelete(row: KnowledgeCategory) {
  ElMessageBox.confirm(`确定删除分类「${row.categoryName}」吗？`, '警告', { type: 'warning' })
    .then(async () => {
      await deleteCategories([row.categoryId])
      ElMessage.success('删除成功')
      loadData()
    })
}

onMounted(loadData)
</script>
