<template>
  <div>
    <div class="page-header">
      <h3>角色管理</h3>
    </div>

    <div class="search-bar">
      <div class="search-left">
        <el-input v-model="search.roleName" placeholder="角色名称" clearable @keyup.enter="loadData" />
        <el-input v-model="search.roleKey" placeholder="角色标识" clearable @keyup.enter="loadData" />
        <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
        <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
      </div>
      <div class="search-right">
        <el-button type="primary" :icon="Plus" @click="openDialog()" v-if="userStore.hasPermission('system:role:add')">新增角色</el-button>
      </div>
    </div>

    <div class="campus-card">
      <el-table :data="roles" v-loading="loading" stripe style="width:100%">
        <el-table-column prop="roleName" label="角色名称" min-width="160" />
        <el-table-column prop="roleKey" label="权限标识" min-width="160" />
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <span class="cell-status">
              <span :class="['dot', row.status === '1' ? 'dot--green dot--pulse' : 'dot--gray']"></span>
              {{ row.status === '1' ? '正常' : '停用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="createTime" label="创建时间" width="170">
          <template #default="{ row }">{{ row.createTime?.replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="Edit" @click="openDialog(row)"
              v-if="userStore.hasPermission('system:role:edit') && row.roleKey !== 'admin'">编辑</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)"
              v-if="userStore.hasPermission('system:role:remove') && row.roleKey !== 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:16px;display:flex;justify-content:flex-end">
        <el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize"
          :total="page.total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next"
          @current-change="loadData" @size-change="loadData" />
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog :title="editId ? '编辑角色' : '新增角色'" v-model="dialogVisible" width="640px" top="8vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="角色名称" prop="roleName">
              <el-input v-model="form.roleName" placeholder="请输入" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="权限标识" prop="roleKey">
              <el-input v-model="form.roleKey" placeholder="如 admin / user" :disabled="!!editId" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="排序">
              <el-input-number v-model="form.roleSort" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch v-model="form.status" active-value="1" inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="菜单权限">
          <div class="menu-tree-box">
            <el-tree
              ref="menuTreeRef"
              :data="menuTree"
              show-checkbox
              node-key="menuId"
              :default-checked-keys="form.menuIds"
              :props="{ label: 'menuName', children: 'children' }"
              default-expand-all
              check-strictly
            />
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" />
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
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { listRole, addRole, updateRole, deleteRoles, getRoleMenus } from '@/api/role'
import { listMenu } from '@/api/menu'
import type { SysRole, SysMenu } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, Refresh } from '@element-plus/icons-vue'

const userStore = useUserStore()
const roles = ref<SysRole[]>([])
const menuTree = ref<SysMenu[]>([])
const loading = ref(false)
const search = reactive({ roleName: '', roleKey: '' })
const page = reactive({ pageNum: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref()
const menuTreeRef = ref()
const form = reactive<any>({ roleName: '', roleKey: '', roleSort: 0, status: '1', remark: '', menuIds: [] })
const rules = {
  roleName: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  roleKey: [{ required: true, message: '请输入权限标识', trigger: 'blur' }]
}

async function loadData() {
  loading.value = true
  try {
    const res = await listRole({ ...search, ...page })
    roles.value = res.data.rows
    page.total = res.data.total
  } finally { loading.value = false }
}

async function loadMenuTree() {
  const res = await listMenu()
  menuTree.value = res.data
}

function resetSearch() { search.roleName = ''; search.roleKey = ''; page.pageNum = 1; loadData() }

async function openDialog(row?: SysRole) {
  editId.value = row?.roleId || null
  form.roleName = row?.roleName || ''
  form.roleKey = row?.roleKey || ''
  form.roleSort = row?.roleSort || 0
  form.status = row?.status || '1'
  form.remark = row?.remark || ''
  form.menuIds = row?.roleId ? [] : []
  if (row?.roleId) {
    const res = await getRoleMenus(row.roleId)
    form.menuIds = res.data
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const checkedKeys = menuTreeRef.value?.getCheckedKeys() || []
    const data = { ...form, menuIds: checkedKeys }
    if (editId.value) {
      data.roleId = editId.value
      await updateRole(data, checkedKeys)
      ElMessage.success('修改成功')
    } else {
      await addRole(data, checkedKeys)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

function handleDelete(row: SysRole) {
  ElMessageBox.confirm(`确定删除角色「${row.roleName}」吗？`, '警告', { type: 'warning' })
    .then(async () => {
      await deleteRoles([row.roleId])
      ElMessage.success('删除成功')
      loadData()
    })
}

onMounted(() => { loadData(); loadMenuTree() })
</script>

<style scoped>
.search-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex: 1;
}
.search-right {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

.menu-tree-box {
  max-height: 320px;
  overflow-y: auto;
  padding: 14px 20px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  width: 100%;
}

.menu-tree-box :deep(.el-tree-node__content) {
  height: 32px;
  padding-left: 6px;
}

.menu-tree-box :deep(.el-tree-node__label) {
  font-size: 14px;
}

/* 滚动条美化 */
.menu-tree-box::-webkit-scrollbar {
  width: 6px;
}
.menu-tree-box::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}
.menu-tree-box::-webkit-scrollbar-track {
  background: transparent;
}
</style>
