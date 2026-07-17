<template>
  <div>
    <div class="page-header">
      <h3>纠错审核</h3>
    </div>

    <div class="search-bar">
      <el-select v-model="search.status" placeholder="状态" clearable @change="loadData" style="width:140px">
        <el-option label="待审核" value="PENDING" />
        <el-option label="处理中" value="PROCESSING" />
        <el-option label="已采纳" value="APPROVED" />
        <el-option label="已拒绝" value="REJECTED" />
        <el-option label="失败" value="FAILED" />
      </el-select>
      <el-button type="primary" :icon="Search" @click="loadData">搜索</el-button>
      <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
    </div>

    <div class="campus-card">
      <el-table :data="corrections" v-loading="loading" stripe>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="original_question" label="原问题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.original_question || '-' }}</template>
        </el-table-column>
        <el-table-column prop="proposed_answer" label="用户建议答案" min-width="240" show-overflow-tooltip />
        <el-table-column prop="contributor_name" label="提交人" width="120">
          <template #default="{ row }">{{ row.contributor_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)" effect="light">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0, 19) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'PENDING'" type="primary" link size="small" :icon="View" @click="openReview(row)">审核</el-button>
            <el-button v-else type="info" link size="small" :icon="View" @click="openReview(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:16px;display:flex;justify-content:flex-end">
        <el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize"
          :total="page.total" :page-sizes="[10,20,50]" layout="total,sizes,prev,pager,next"
          @current-change="loadData" @size-change="loadData" />
      </div>
    </div>

    <!-- 审核弹窗 -->
    <el-dialog v-model="dialogVisible" :title="current?.status === 'PENDING' ? '审核纠错' : '纠错详情'" width="680px" destroy-on-close>
      <template v-if="current">
        <el-descriptions :column="1" border size="small" class="review-info">
          <el-descriptions-item label="原问题">{{ current.original_question || '-' }}</el-descriptions-item>
          <el-descriptions-item label="AI 原回答">
            <div class="pre-wrap">{{ current.original_answer || '-' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="用户建议答案">
            <div class="pre-wrap">{{ current.proposed_answer }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="提交人">
            {{ current.contributor_name || '-' }}<span v-if="current.contributor_email">（{{ current.contributor_email }}）</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="current.review_note" label="审核备注">{{ current.review_note }}</el-descriptions-item>
          <el-descriptions-item v-if="current.error" label="错误信息">{{ current.error }}</el-descriptions-item>
        </el-descriptions>

        <!-- 待审核：可编辑后入库 -->
        <el-form v-if="current.status === 'PENDING'" label-position="top" class="review-form">
          <el-form-item label="入库问题（可修改）">
            <el-input v-model="reviewForm.question" maxlength="1000" show-word-limit />
          </el-form-item>
          <el-form-item label="入库答案（可修改）">
            <el-input v-model="reviewForm.answer" type="textarea" :autosize="{ minRows: 4, maxRows: 10 }" maxlength="6000" show-word-limit />
          </el-form-item>
        </el-form>
      </template>
      <template #footer v-if="current?.status === 'PENDING'">
        <el-button type="danger" plain :loading="rejecting" @click="handleReject">拒绝</el-button>
        <el-button type="primary" :loading="approving" :disabled="!canApprove" @click="handleApprove">通过并入库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, View } from '@element-plus/icons-vue'
import { listCorrections, approveCorrection, rejectCorrection } from '@/api/qa'
import type { AdminAnswerCorrection } from '@/types'

const loading = ref(false)
const corrections = ref<AdminAnswerCorrection[]>([])
const search = reactive({ status: '' })
const page = reactive({ pageNum: 1, pageSize: 10, total: 0 })

const dialogVisible = ref(false)
const current = ref<AdminAnswerCorrection | null>(null)
const reviewForm = reactive({ question: '', answer: '' })
const approving = ref(false)
const rejecting = ref(false)

const canApprove = computed(() =>
  reviewForm.question.trim().length >= 2 && reviewForm.answer.trim().length >= 2
)

function statusText(status: string) {
  return { PENDING: '待审核', PROCESSING: '处理中', APPROVED: '已采纳', REJECTED: '已拒绝', FAILED: '失败' }[status as never] || status
}
function statusTagType(status: string) {
  return ({ PENDING: 'info', PROCESSING: 'warning', APPROVED: 'success', REJECTED: 'danger', FAILED: 'danger' } as const)[status as never] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const res = await listCorrections({
      page: page.pageNum,
      size: page.pageSize,
      status_filter: search.status || undefined,
    })
    corrections.value = res.data.items
    page.total = res.data.total
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  search.status = ''
  page.pageNum = 1
  loadData()
}

function openReview(row: AdminAnswerCorrection) {
  current.value = row
  reviewForm.question = row.original_question || ''
  reviewForm.answer = row.proposed_answer
  dialogVisible.value = true
}

async function handleApprove() {
  if (!current.value || approving.value) return
  approving.value = true
  try {
    await approveCorrection(current.value.id, {
      question: reviewForm.question.trim(),
      answer: reviewForm.answer.trim(),
      source_document_ids: current.value.source_document_ids || [],
    })
    ElMessage.success('已批准，正在生成知识文档')
    dialogVisible.value = false
    loadData()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '操作失败')
  } finally {
    approving.value = false
  }
}

async function handleReject() {
  if (!current.value || rejecting.value) return
  try {
    const { value: reason } = await ElMessageBox.prompt('请输入拒绝理由（2-1000字）', '拒绝纠错', {
      confirmButtonText: '确认拒绝',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputValidator: v => (v && v.trim().length >= 2) || '理由至少 2 个字',
    })
    rejecting.value = true
    await rejectCorrection(current.value.id, reason.trim())
    ElMessage.success('已拒绝')
    dialogVisible.value = false
    loadData()
  } catch (err: any) {
    if (err !== 'cancel' && err?.message !== 'cancel') {
      ElMessage.error(err?.response?.data?.message || '操作失败')
    }
  } finally {
    rejecting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.review-info {
  margin-bottom: 16px;
}
.pre-wrap {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}
.review-form {
  :deep(.el-form-item__label) {
    font-weight: 600;
  }
}
</style>
