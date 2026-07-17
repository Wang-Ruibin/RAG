<template>
  <div class="page-shell">
    <PageHeader title="纠错审核" description="审核用户对 AI 回答提交的纠错，通过后生成知识文档并沉淀进问答库" />
    <FilterCard>
      <label class="filter-field"><span>状态</span>
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:170px" @change="applyFilters">
          <el-option label="待审核" value="PENDING" />
          <el-option label="处理中" value="PROCESSING" />
          <el-option label="已采纳" value="APPROVED" />
          <el-option label="已拒绝" value="REJECTED" />
          <el-option label="失败" value="FAILED" />
        </el-select>
      </label>
      <el-button type="primary" :icon="Search" @click="applyFilters">查询</el-button>
      <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
    </FilterCard>

    <section class="content-card table-card">
      <div class="table-card__body">
        <el-table :data="corrections" v-loading="loading" row-key="id" style="width:100%">
          <el-table-column label="原问题" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.original_question || '—' }}</template>
          </el-table-column>
          <el-table-column prop="proposed_answer" label="用户建议答案" min-width="260" show-overflow-tooltip />
          <el-table-column label="提交人" width="130">
            <template #default="{ row }">{{ row.contributor_name || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }"><StatusTag :label="statusText(row.status)" :tone="statusTone(row.status)" /></template>
          </el-table-column>
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openReview(row)">{{ row.status === 'PENDING' ? '审核' : '查看' }}</el-button>
            </template>
          </el-table-column>
          <template #empty><EmptyState title="暂无纠错" description="用户在问答页点踩并提交纠错后会出现在这里" /></template>
        </el-table>
      </div>
      <div class="table-footer">
        <span class="table-footer__total">共 {{ page.total }} 条纠错</span>
        <el-pagination v-model:current-page="page.pageNum" v-model:page-size="page.pageSize"
          :total="page.total" :page-sizes="[10,20,50]" layout="sizes,prev,pager,next"
          @current-change="loadData" @size-change="handleSizeChange" />
      </div>
    </section>

    <!-- 审核弹窗 -->
    <el-dialog v-model="dialogVisible" :title="current?.status === 'PENDING' ? '审核纠错' : '纠错详情'" width="680px" destroy-on-close>
      <template v-if="current">
        <el-descriptions :column="1" border size="small" class="review-info">
          <el-descriptions-item label="原问题">{{ current.original_question || '—' }}</el-descriptions-item>
          <el-descriptions-item label="AI 原回答">
            <div class="pre-wrap">{{ current.original_answer || '—' }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="用户建议答案">
            <div class="pre-wrap">{{ current.proposed_answer }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="提交人">
            {{ current.contributor_name || '—' }}<span v-if="current.contributor_email">（{{ current.contributor_email }}）</span>
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
import { Search, Refresh } from '@element-plus/icons-vue'
import { listCorrections, approveCorrection, rejectCorrection } from '@/api/qa'
import type { AdminAnswerCorrection } from '@/types'
import PageHeader from '@/components/PageHeader.vue'
import FilterCard from '@/components/FilterCard.vue'
import StatusTag from '@/components/StatusTag.vue'
import EmptyState from '@/components/EmptyState.vue'

const loading = ref(false)
const corrections = ref<AdminAnswerCorrection[]>([])
const filters = reactive({ status: '' })
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
function statusTone(status: string) {
  return ({ PENDING: 'info', PROCESSING: 'warning', APPROVED: 'success', REJECTED: 'danger', FAILED: 'danger' } as const)[status as never] || 'info'
}
function formatDate(value?: string) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

async function loadData() {
  loading.value = true
  try {
    const res = await listCorrections({
      page: page.pageNum,
      size: page.pageSize,
      status_filter: filters.status || undefined,
    })
    corrections.value = res.data.items
    page.total = res.data.total
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  page.pageNum = 1
  loadData()
}

function resetFilters() {
  filters.status = ''
  page.pageNum = 1
  loadData()
}

function handleSizeChange() {
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

<style scoped>
.review-info { margin-bottom: 16px; }
.pre-wrap { white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow-y: auto; }
.review-form :deep(.el-form-item__label) { font-weight: 600; }
</style>
