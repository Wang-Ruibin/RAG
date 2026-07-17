<template>
  <div class="page-shell">
    <PageHeader title="角色管理" description="管理系统角色及其权限，角色用于控制用户对系统功能的访问权限">
      <template #actions><el-button v-if="userStore.hasPermission('system:role:add')" type="primary" :icon="Plus" @click="openDialog()">新增角色</el-button></template>
    </PageHeader>
    <FilterCard><label class="filter-field"><span>角色名称</span><el-input v-model="filters.roleName" placeholder="请输入角色名称" clearable style="width:220px" @keyup.enter="applyFilters" /></label><label class="filter-field"><span>角色标识</span><el-input v-model="filters.roleKey" placeholder="请输入角色标识" clearable style="width:220px" @keyup.enter="applyFilters" /></label><el-button type="primary" :icon="Search" @click="applyFilters">搜索</el-button><el-button :icon="Refresh" @click="resetFilters">重置</el-button></FilterCard>

    <section class="content-card table-card">
      <div class="table-card__body"><el-table :data="roles" v-loading="loading" row-key="roleId" style="width:100%">
        <el-table-column label="角色名称" min-width="180"><template #default="{row}"><div class="role-name"><strong>{{ row.roleName }}</strong><el-tag v-if="row.roleKey==='admin'" size="small" type="primary">受保护</el-tag></div></template></el-table-column>
        <el-table-column prop="roleKey" label="角色标识" min-width="170"><template #default="{row}"><code>{{ row.roleKey }}</code></template></el-table-column>
        <el-table-column prop="roleSort" label="排序" width="90" align="center" />
        <el-table-column label="状态" width="100"><template #default="{row}"><StatusTag :label="row.status==='1'?'正常':'停用'" :tone="row.status==='1'?'success':'info'" /></template></el-table-column>
        <el-table-column label="创建时间" width="180"><template #default="{row}">{{ formatDate(row.createTime) }}</template></el-table-column>
        <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right"><template #default="{row}"><div class="row-actions"><el-button v-if="row.roleKey!=='admin' && userStore.hasPermission('system:role:edit')" link type="primary" @click="openDialog(row)">编辑</el-button><el-popconfirm v-if="row.roleKey!=='admin' && userStore.hasPermission('system:role:remove')" :title="`确定删除角色“${row.roleName}”？`" @confirm="handleDelete(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm><span v-if="row.roleKey==='admin'" class="muted">—</span></div></template></el-table-column>
        <template #empty><EmptyState title="暂无角色" description="当前筛选条件下没有角色数据" /></template>
      </el-table></div>
      <div class="table-footer"><span class="table-footer__total">共 {{ page.total }} 个角色</span><el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize" :total="page.total" :page-sizes="[10,20,50]" layout="sizes,prev,pager,next" @current-change="loadData" @size-change="handleSizeChange" /></div>
    </section>

    <el-drawer v-model="dialogVisible" :title="editingId?'编辑角色':'新增角色'" size="500px" @closed="formRef?.resetFields()">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="right" label-width="90px">
        <div class="form-grid"><el-form-item label="角色名称" prop="roleName"><el-input v-model="form.roleName" /></el-form-item><el-form-item label="角色标识" prop="roleKey"><el-input v-model="form.roleKey" :disabled="!!editingId" placeholder="例如 knowledge_admin" /></el-form-item><el-form-item label="排序"><el-input-number v-model="form.roleSort" :min="0" style="width:100%" /></el-form-item><el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="正常" value="1" /><el-option label="停用" value="0" /></el-select></el-form-item></div>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" show-word-limit /></el-form-item>
        <el-form-item label="菜单权限">
          <div class="tree-panel">
            <div class="tree-toolbar"><span>严格选择模式</span><div><el-button link type="primary" @click="toggleExpand(true)">全部展开</el-button><el-button link type="primary" @click="toggleExpand(false)">全部折叠</el-button><el-button link @click="selectAll">全选</el-button><el-button link @click="clearAll">清空</el-button></div></div>
            <el-tree ref="menuTreeRef" :data="menuTree" node-key="menuId" show-checkbox check-strictly default-expand-all :props="{label:'menuName',children:'children'}" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer><div class="drawer-footer"><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button></div></template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'
import { addRole, deleteRoles, getRoleMenus, listRole, updateRole } from '@/api/role'
import { listMenu } from '@/api/menu'
import { useUserStore } from '@/stores/user'
import type { SysMenu, SysRole } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore=useUserStore(),roles=ref<SysRole[]>([]),menuTree=ref<SysMenu[]>([]),loading=ref(false)
const filters=reactive({roleName:'',roleKey:''}),page=reactive({pageNum:1,pageSize:10,total:0})
function formatDate(value?:string){return value?value.replace('T',' ').slice(0,19):'—'}
async function loadData(){loading.value=true;try{const response=await listRole({pageNum:page.pageNum,pageSize:page.pageSize,roleName:filters.roleName.trim()||undefined,roleKey:filters.roleKey.trim()||undefined});roles.value=response.data.rows;page.total=response.data.total}finally{loading.value=false}}
async function loadMenuTree(){menuTree.value=(await listMenu()).data}
function applyFilters(){page.pageNum=1;loadData()}function resetFilters(){filters.roleName='';filters.roleKey='';page.pageNum=1;loadData()}function handleSizeChange(){page.pageNum=1;loadData()}

const dialogVisible=ref(false),editingId=ref<number|null>(null),submitting=ref(false),formRef=ref(),menuTreeRef=ref()
const form=reactive({roleName:'',roleKey:'',roleSort:0,status:'1',remark:''})
const rules={roleName:[{required:true,message:'请输入角色名称',trigger:'blur'}],roleKey:[{required:true,message:'请输入角色标识',trigger:'blur'}]}
async function openDialog(row?:SysRole){editingId.value=row?.roleId??null;Object.assign(form,{roleName:row?.roleName||'',roleKey:row?.roleKey||'',roleSort:row?.roleSort??0,status:row?.status||'1',remark:row?.remark||''});let checked:number[]=[];if(row?.roleId)checked=(await getRoleMenus(row.roleId)).data;dialogVisible.value=true;await nextTick();menuTreeRef.value?.setCheckedKeys(checked,false)}
function collectIds(nodes:SysMenu[]):number[]{return nodes.flatMap(node=>[node.menuId,...collectIds(node.children||[])])}
function selectAll(){menuTreeRef.value?.setCheckedKeys(collectIds(menuTree.value),false)}function clearAll(){menuTreeRef.value?.setCheckedKeys([],false)}
function toggleExpand(expanded:boolean){const walk=(nodes:any[])=>nodes.forEach(node=>{node.expanded=expanded;walk(node.childNodes||[])});walk(menuTreeRef.value?.store?.root?.childNodes||[])}
async function submitForm(){if(!(await formRef.value?.validate().catch(()=>false)))return;submitting.value=true;try{const menuIds=(menuTreeRef.value?.getCheckedKeys(false)||[]) as number[];if(editingId.value)await updateRole({roleId:editingId.value,...form},menuIds);else await addRole({...form},menuIds);ElMessage.success(editingId.value?'角色已更新':'角色已创建');dialogVisible.value=false;await loadData()}finally{submitting.value=false}}
async function handleDelete(row:SysRole){await deleteRoles([row.roleId]);ElMessage.success('角色已删除');await loadData()}
onMounted(()=>{loadData();loadMenuTree()})
</script>

<style scoped>
.role-name{display:flex;align-items:center;gap:10px}.role-name strong{color:var(--text)}code{padding:4px 8px;color:var(--brand);background:var(--brand-soft);border-radius:6px}.row-actions{display:flex;align-items:center}.form-grid{display:grid;grid-template-columns:1fr}.tree-panel{width:100%;overflow:hidden;border:1px solid var(--border);border-radius:10px}.tree-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;color:var(--text-muted);background:var(--surface-soft);border-bottom:1px solid var(--border);font-size:12px}.tree-toolbar>div{display:flex;flex-wrap:wrap}.tree-panel :deep(.el-tree){max-height:390px;padding:12px;overflow:auto;background:var(--surface)}.tree-panel :deep(.el-tree-node__content){height:34px;border-radius:7px}.drawer-footer{display:flex;justify-content:flex-end;gap:10px;padding:14px 20px;border-top:1px solid var(--border)}
@media(max-width:640px){.form-grid{grid-template-columns:1fr}.tree-toolbar{align-items:flex-start;flex-direction:column}}
</style>
