<template>
  <div>
    <div class="page-header">
      <h3>系统日志</h3>
      <div>
        <el-button type="danger" :icon="Delete" @click="handleClean" v-if="userStore.hasPermission('system:log:remove')">清空日志</el-button>
      </div>
    </div>

    <div class="search-bar">
      <el-input v-model="search.title" placeholder="操作模块" clearable @keyup.enter="loadData" />
      <el-input v-model="search.operName" placeholder="操作人" clearable @keyup.enter="loadData" />
      <el-select v-model="search.status" placeholder="状态" clearable @change="loadData" style="width:120px">
        <el-option label="成功" :value="1" />
        <el-option label="失败" :value="0" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
      <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
    </div>

    <div class="campus-card">
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column type="selection" width="50" />
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="title" label="操作模块" width="140" />
        <el-table-column prop="businessType" label="业务类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ ['其它','新增','修改','删除','查询'][row.businessType] || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operName" label="操作人" width="120" />
        <el-table-column prop="operUrl" label="请求URL" min-width="200" show-overflow-tooltip />
        <el-table-column prop="operIp" label="IP地址" width="140" />
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <span class="cell-status">
              <span :class="['dot', row.status === 1 ? 'dot--green' : 'dot--red']"></span>
              {{ row.status === 1 ? '成功' : '失败' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="costTime" label="耗时(ms)" width="90" align="center" />
        <el-table-column prop="operTime" label="操作时间" width="170">
          <template #default="{ row }">{{ row.operTime?.replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" :icon="View" @click="showDetail(row)">详情</el-button>
            <el-button type="danger" link size="small" :icon="Delete" @click="handleDelete(row)"
              v-if="userStore.hasPermission('system:log:remove')">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:16px;display:flex;justify-content:space-between">
        <el-button type="danger" :disabled="!selectedIds.length" @click="handleBatchDelete"
          v-if="userStore.hasPermission('system:log:remove')">批量删除</el-button>
        <el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize"
          :total="page.total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next"
          @current-change="loadData" @size-change="loadData" />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog title="日志详情" v-model="detailVisible" width="640px" top="8vh">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="操作模块">{{ detail.title }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ detail.operName }}</el-descriptions-item>
        <el-descriptions-item label="请求URL" :span="2">{{ detail.operUrl }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ detail.operIp }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ detail.costTime }} ms</el-descriptions-item>
        <el-descriptions-item label="状态" :span="2">
          <span class="cell-status">
            <span :class="['dot', detail.status === 1 ? 'dot--green' : 'dot--red']"></span>
            {{ detail.status === 1 ? '成功' : '失败' }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="请求参数" :span="2">
          <div class="log-code">{{ detail.operParam || '-' }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="返回结果" :span="2">
          <div class="log-code">{{ detail.jsonResult || '-' }}</div>
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.errorMsg" label="错误信息" :span="2">
          <div class="log-code" style="color:#f56c6c">{{ detail.errorMsg }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { listLog, deleteLogs, cleanLog } from '@/api/log'
import type { SysOperLog } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Search, Refresh, View } from '@element-plus/icons-vue'

const userStore = useUserStore()
const logs = ref<SysOperLog[]>([])
const selectedIds = ref<number[]>([])
const loading = ref(false)
const search = reactive({ title: '', operName: '', status: null as number | null })
const page = reactive({ pageNum: 1, pageSize: 10, total: 0 })

const detailVisible = ref(false)
const detail = reactive<any>({})

function showDetail(row: SysOperLog) {
  Object.assign(detail, row)
  detailVisible.value = true
}

async function loadData() {
  loading.value = true
  try {
    const res = await listLog({ ...search, ...page })
    logs.value = res.data.rows
    page.total = res.data.total
  } finally { loading.value = false }
}

function resetSearch() {
  search.title = ''; search.operName = ''; search.status = null
  page.pageNum = 1; loadData()
}

function handleDelete(row: SysOperLog) {
  ElMessageBox.confirm('确定删除该日志吗？', '警告', { type: 'warning' })
    .then(async () => {
      await deleteLogs([row.operId])
      ElMessage.success('删除成功')
      loadData()
    })
}

function handleBatchDelete() {
  ElMessageBox.confirm('确定删除选中的日志吗？', '警告', { type: 'warning' })
    .then(async () => {
      await deleteLogs(selectedIds.value)
      ElMessage.success('删除成功')
      selectedIds.value = []
      loadData()
    })
}

function handleClean() {
  ElMessageBox.confirm('确定清空所有系统日志吗？此操作不可恢复！', '严重警告', { type: 'error', confirmButtonClass: 'el-button--danger' })
    .then(async () => {
      await cleanLog()
      ElMessage.success('日志已清空')
      loadData()
    })
}

onMounted(loadData)
</script>

<style scoped>
.log-code {
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'SF Mono', Consolas, 'Courier New', monospace;
  font-size: 13px;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 10px 14px;
  border-radius: 8px;
  color: var(--primary-light);
}
</style>
