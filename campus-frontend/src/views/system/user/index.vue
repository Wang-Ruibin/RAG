<template>
  <div>
    <div class="page-header">
      <h3>用户管理</h3>
    </div>

    <div class="search-bar">
      <el-input v-model="search.userName" placeholder="用户名" clearable @keyup.enter="loadData" />
      <el-input v-model="search.nickName" placeholder="昵称" clearable @keyup.enter="loadData" />
      <el-input v-model="search.phone" placeholder="手机号" clearable @keyup.enter="loadData" />
      <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
      <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
      <el-button type="primary" :icon="Plus" @click="openDialog()" v-if="userStore.hasPermission('system:user:add')">新增用户</el-button>
    </div>

    <div class="campus-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="userName" label="用户名" width="130" />
        <el-table-column prop="nickName" label="昵称" width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="140" />
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
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="Edit" @click="openDialog(row)"
              v-if="userStore.hasPermission('system:user:edit') && row.userId !== 1">编辑</el-button>
            <el-button type="warning" link size="small" :icon="Key" @click="handleResetPwd(row)"
              v-if="userStore.hasPermission('system:user:resetPwd') && row.userId !== 1">重置密码</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)"
              v-if="userStore.hasPermission('system:user:remove') && row.userId !== 1">删除</el-button>
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
    <el-dialog :title="editId ? '编辑用户' : '新增用户'" v-model="dialogVisible" width="520px" top="8vh">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="userName">
          <el-input v-model="form.userName" placeholder="学号/工号" :disabled="!!editId" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickName">
          <el-input v-model="form.nickName" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item v-if="!editId" label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="状态" v-if="userStore.hasPermission('system:user:status')">
          <el-switch v-model="form.status" active-value="1" inactive-value="0" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.roleIds" placeholder="请选择角色" clearable>
            <el-option v-for="r in roles" :key="r.roleId" :label="r.roleName" :value="r.roleId" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog title="重置密码" v-model="pwdVisible" width="400px">
      <el-form label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" @click="doResetPwd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { listUser, addUser, updateUser, deleteUsers, resetPassword, getUserRoles } from '@/api/user'
import { listRole } from '@/api/role'
import type { SysUser, SysRole } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Search, Refresh, Key } from '@element-plus/icons-vue'

const userStore = useUserStore()
const users = ref<SysUser[]>([])
const roles = ref<SysRole[]>([])
const loading = ref(false)
const search = reactive({ userName: '', nickName: '', phone: '' })
const page = reactive({ pageNum: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref()
const form = reactive<any>({ userName: '', nickName: '', password: '', email: '', phone: '', status: '1', roleIds: null })
const rules = {
  userName: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  nickName: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const pwdVisible = ref(false)
const resetUserId = ref<number>(0)
const newPassword = ref('123456')

async function loadData() {
  loading.value = true
  try {
    const res = await listUser({ ...search, ...page })
    users.value = res.data.rows
    page.total = res.data.total
  } finally { loading.value = false }
}

async function loadRoles() {
  const res = await listRole({ pageSize: 100 })
  roles.value = res.data.rows
}

function resetSearch() {
  search.userName = ''; search.nickName = ''; search.phone = ''
  page.pageNum = 1
  loadData()
}

async function openDialog(row?: any) {
  editId.value = row?.userId || null
  form.userName = row?.userName || ''
  form.nickName = row?.nickName || ''
  form.password = ''
  form.email = row?.email || ''
  form.phone = row?.phone || ''
  form.status = row?.status || '1'
  form.roleIds = null
  if (editId.value) {
    rules.password[0].required = false
    try {
      const res = await getUserRoles(row.userId)
      form.roleIds = (res.data?.length) ? res.data[0] : null
    } catch { /* 角色加载失败不影响编辑 */ }
  } else {
    rules.password[0].required = true
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const roleIds = form.roleIds ? [form.roleIds] : []
    const data = { ...form }
    delete data.roleIds
    if (editId.value) {
      data.userId = editId.value
      await updateUser(data, roleIds)
      ElMessage.success('修改成功')
    } else {
      await addUser(data, roleIds)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

function handleResetPwd(row: SysUser) {
  resetUserId.value = row.userId
  newPassword.value = '123456'
  pwdVisible.value = true
}

async function doResetPwd() {
  await resetPassword(resetUserId.value, newPassword.value)
  ElMessage.success('密码已重置')
  pwdVisible.value = false
}

function handleDelete(row: SysUser) {
  ElMessageBox.confirm(`确定删除用户「${row.nickName}」吗？`, '警告', { type: 'warning' })
    .then(async () => {
      await deleteUsers([row.userId])
      ElMessage.success('删除成功')
      loadData()
    })
}

onMounted(() => { loadData(); loadRoles() })
</script>
