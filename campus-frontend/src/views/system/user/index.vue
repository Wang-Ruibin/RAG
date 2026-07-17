<template>
  <div class="page-shell">
    <PageHeader title="用户管理" description="管理系统用户账号，支持用户信息维护、角色分配与状态管理">
      <template #actions><el-button v-if="userStore.hasPermission('system:user:add')" type="primary" :icon="Plus" @click="openEditor()">新增用户</el-button></template>
    </PageHeader>

    <FilterCard>
      <label class="filter-field"><span>用户名</span><el-input v-model="filters.userName" placeholder="请输入用户名" clearable style="width:230px" @keyup.enter="applyFilters" /></label>
      <label class="filter-field"><span>昵称</span><el-input v-model="filters.nickName" placeholder="请输入昵称" clearable style="width:230px" @keyup.enter="applyFilters" /></label>
      <label class="filter-field"><span>手机号</span><el-input v-model="filters.phone" placeholder="请输入手机号" clearable style="width:230px" @keyup.enter="applyFilters" /></label>
      <el-button type="primary" :icon="Search" @click="applyFilters">搜索</el-button><el-button :icon="Refresh" @click="resetFilters">重置</el-button>
    </FilterCard>

    <section class="content-card table-card">
      <div class="table-card__body">
        <el-table :data="users" v-loading="loading" row-key="userId" style="width:100%">
          <el-table-column label="用户" min-width="190"><template #default="{row}"><div class="user-cell"><el-avatar :size="36">{{ (row.nickName || row.userName).charAt(0) }}</el-avatar><div><strong>{{ row.userName }}</strong><small>{{ row.nickName }}</small></div></div></template></el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="190" show-overflow-tooltip />
          <el-table-column prop="phone" label="手机号" width="145" />
          <el-table-column label="状态" width="100"><template #default="{row}"><StatusTag :label="row.status==='1'?'正常':'停用'" :tone="row.status==='1'?'success':'info'" /></template></el-table-column>
          <el-table-column label="创建时间" width="180"><template #default="{row}">{{ formatDate(row.createTime) }}</template></el-table-column>
          <el-table-column label="操作" width="260" fixed="right"><template #default="{row}"><div class="row-actions">
            <el-button v-if="userStore.hasPermission('system:user:edit')" link type="primary" @click="openEditor(row)">编辑</el-button>
            <el-button v-if="userStore.hasPermission('system:user:resetPwd')" link type="warning" @click="openPassword(row)">重置密码</el-button>
            <el-button v-if="userStore.hasPermission('system:user:edit')" link type="primary" @click="openRoleDialog(row)">分配角色</el-button>
            <el-popconfirm v-if="userStore.hasPermission('system:user:remove')" :title="`确定删除用户“${row.nickName || row.userName}”？`" @confirm="handleDelete(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </div></template></el-table-column>
          <template #empty><EmptyState title="暂无用户" description="当前筛选条件下没有用户数据" /></template>
        </el-table>
      </div>
      <div class="table-footer"><span class="table-footer__total">共 {{ page.total }} 位用户</span><el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize" :total="page.total" :page-sizes="[10,20,50]" layout="sizes,prev,pager,next" @current-change="loadData" @size-change="handleSizeChange" /></div>
    </section>

    <el-dialog v-model="editorVisible" :title="editingId ? '编辑用户' : '新增用户'" width="600px" @closed="editorRef?.resetFields()">
      <el-form ref="editorRef" :model="editor" :rules="editorRules" label-position="top">
        <div class="form-grid"><el-form-item label="用户名" prop="userName"><el-input v-model="editor.userName" :disabled="!!editingId" /></el-form-item><el-form-item label="昵称" prop="nickName"><el-input v-model="editor.nickName" /></el-form-item><el-form-item label="邮箱" prop="email"><el-input v-model="editor.email" /></el-form-item><el-form-item label="手机号" prop="phone"><el-input v-model="editor.phone" /></el-form-item></div>
        <el-form-item v-if="!editingId" label="初始密码" prop="password"><el-input v-model="editor.password" type="password" show-password /></el-form-item>
        <el-form-item label="状态"><el-radio-group v-model="editor.status"><el-radio-button value="1">正常</el-radio-button><el-radio-button value="0">停用</el-radio-button></el-radio-group></el-form-item>
      </el-form>
      <template #footer><el-button @click="editorVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitEditor">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="roleVisible" title="分配角色" width="520px">
      <div class="role-user"><el-avatar>{{ (roleTarget?.nickName || roleTarget?.userName || 'U').charAt(0) }}</el-avatar><div><strong>{{ roleTarget?.nickName || roleTarget?.userName }}</strong><span>{{ roleTarget?.userName }}</span></div></div>
      <el-form label-position="top"><el-form-item label="选择角色" required><el-select v-model="selectedRoleIds" v-loading="roleLoading" multiple filterable placeholder="至少选择一个角色" style="width:100%"><el-option v-for="role in roles" :key="role.roleId" :label="role.roleName" :value="role.roleId"><span>{{ role.roleName }}</span><small class="role-key">{{ role.roleKey }}</small></el-option></el-select></el-form-item></el-form>
      <el-alert v-if="roleError" :title="roleError" type="error" :closable="false" show-icon />
      <template #footer><el-button @click="roleVisible=false">取消</el-button><el-button type="primary" :loading="roleSubmitting" :disabled="roleLoading || selectedRoleIds.length===0" @click="submitRoles">保存角色</el-button></template>
    </el-dialog>

    <el-dialog v-model="passwordVisible" title="重置密码" width="420px"><el-form label-position="top"><el-form-item label="新密码"><el-input v-model="newPassword" type="password" show-password /></el-form-item></el-form><template #footer><el-button @click="passwordVisible=false">取消</el-button><el-button type="primary" :disabled="!newPassword" @click="submitPassword">确认重置</el-button></template></el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { addUser, assignUserRoles, deleteUsers, getUserRoles, listUser, resetPassword, updateUser } from '@/api/user'
import { listRole } from '@/api/role'
import { useUserStore } from '@/stores/user'
import type { SysRole, SysUser } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore=useUserStore(),users=ref<SysUser[]>([]),loading=ref(false)
const filters=reactive({userName:'',nickName:'',phone:'',status:''}),page=reactive({pageNum:1,pageSize:10,total:0})
function formatDate(value?:string){return value?value.replace('T',' ').slice(0,19):'—'}
async function loadData(){loading.value=true;try{const response=await listUser({pageNum:page.pageNum,pageSize:page.pageSize,userName:filters.userName.trim()||undefined,nickName:filters.nickName.trim()||undefined,phone:filters.phone.trim()||undefined,status:filters.status||undefined});users.value=response.data.rows;page.total=response.data.total}finally{loading.value=false}}
function applyFilters(){page.pageNum=1;loadData()}function resetFilters(){filters.userName='';filters.nickName='';filters.phone='';filters.status='';page.pageNum=1;loadData()}function handleSizeChange(){page.pageNum=1;loadData()}

const editorVisible=ref(false),editingId=ref<number|null>(null),submitting=ref(false),editorRef=ref()
const editor=reactive({userName:'',nickName:'',email:'',phone:'',status:'1',password:''})
const editorRules={userName:[{required:true,message:'请输入用户名',trigger:'blur'}],nickName:[{required:true,message:'请输入昵称',trigger:'blur'}],password:[{validator:(_rule:unknown,value:string,callback:(error?:Error)=>void)=>editingId.value||value?callback():callback(new Error('请输入初始密码')),trigger:'blur'}]}
function openEditor(row?:SysUser){editingId.value=row?.userId??null;Object.assign(editor,{userName:row?.userName||'',nickName:row?.nickName||'',email:row?.email||'',phone:row?.phone||'',status:row?.status||'1',password:''});editorVisible.value=true}
async function submitEditor(){if(!(await editorRef.value?.validate().catch(()=>false)))return;submitting.value=true;try{if(editingId.value){await updateUser({userId:editingId.value,userName:editor.userName,nickName:editor.nickName,email:editor.email,phone:editor.phone,status:editor.status})}else{await addUser({userName:editor.userName,nickName:editor.nickName,email:editor.email,phone:editor.phone,status:editor.status,password:editor.password})}ElMessage.success(editingId.value?'用户信息已更新':'用户已创建');editorVisible.value=false;await loadData()}finally{submitting.value=false}}
async function handleDelete(row:SysUser){await deleteUsers([row.userId]);ElMessage.success('用户已删除');await loadData()}

const roles=ref<SysRole[]>([]),roleVisible=ref(false),roleLoading=ref(false),roleSubmitting=ref(false),roleTarget=ref<SysUser|null>(null),selectedRoleIds=ref<number[]>([]),roleError=ref('')
const roleCache=new Map<number,number[]>()
async function loadRoleOptions(){if(roles.value.length)return;const response=await listRole({pageNum:1,pageSize:100});roles.value=response.data.rows}
async function loadSelectedRoles(userId:number){const cached=roleCache.get(userId);if(cached){selectedRoleIds.value=[...cached];return};const response=await getUserRoles(userId);selectedRoleIds.value=[...response.data];roleCache.set(userId,[...response.data])}
async function openRoleDialog(row:SysUser){roleTarget.value=row;selectedRoleIds.value=[];roleError.value='';roleVisible.value=true;roleLoading.value=true;const [optionsResult,selectedResult]=await Promise.allSettled([loadRoleOptions(),loadSelectedRoles(row.userId)]);const errors=[];if(optionsResult.status==='rejected')errors.push('角色选项');if(selectedResult.status==='rejected')errors.push('当前角色');if(errors.length)roleError.value=`${errors.join('和')}加载失败，请稍后重试`;roleLoading.value=false}
async function submitRoles(){if(!roleTarget.value||selectedRoleIds.value.length===0)return;roleSubmitting.value=true;const userId=roleTarget.value.userId;try{await assignUserRoles({userId,roleIds:[...selectedRoleIds.value]});roleCache.delete(userId);roleVisible.value=false;ElMessage.success('角色分配已更新');await loadData()}finally{roleSubmitting.value=false}}

const passwordVisible=ref(false),passwordUserId=ref(0),newPassword=ref('')
function openPassword(row:SysUser){passwordUserId.value=row.userId;newPassword.value='';passwordVisible.value=true}
async function submitPassword(){await resetPassword(passwordUserId.value,newPassword.value);ElMessage.success('密码已重置');passwordVisible.value=false}

onMounted(loadData)
</script>

<style scoped>
.user-cell{display:flex;align-items:center;gap:11px}.user-cell .el-avatar{color:#fff;background:linear-gradient(135deg,var(--brand),var(--brand-light))}.user-cell>div{display:flex;min-width:0;flex-direction:column}.user-cell strong{color:var(--text)}.user-cell small{margin-top:3px;color:var(--text-muted)}.row-actions{display:flex;align-items:center;white-space:nowrap}.form-grid{display:grid;gap:0 18px;grid-template-columns:1fr 1fr}.role-user{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding:14px;background:var(--surface-soft);border-radius:12px}.role-user .el-avatar{color:#fff;background:var(--brand)}.role-user>div{display:flex;flex-direction:column}.role-user strong{color:var(--text)}.role-user span{color:var(--text-muted);font-size:12px}.role-key{float:right;margin-left:20px;color:var(--text-muted)}
@media(max-width:640px){.form-grid{grid-template-columns:1fr}}
</style>
