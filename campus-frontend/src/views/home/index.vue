<template>
  <div class="chat-page">
    <aside class="conversation-pane">
      <div class="conversation-heading"><div><strong>历史会话</strong><span>{{ conversations.length }} 个会话</span></div><el-button type="primary" plain :icon="Plus" @click="startNewChat">新对话</el-button></div>
      <div class="conversation-list">
        <EmptyState v-if="!conversations.length" title="暂无历史会话" description="开启新对话，探索校园知识吧"><template #icon><ChatDotRound /></template></EmptyState>
        <button v-for="conversation in conversations" :key="conversation.id" :class="['conversation-item',{active:conversation.id===activeId}]" type="button" @click="openConversation(conversation.id)">
          <span><strong>{{ conversation.title || '未命名会话' }}</strong><small>{{ formatTime(conversation.updated_at) }} · {{ conversation.message_count }} 条消息</small></span>
          <el-popconfirm title="删除此会话？" @confirm="removeConversation(conversation.id)"><template #reference><el-button text :icon="Delete" aria-label="删除会话" @click.stop /></template></el-popconfirm>
        </button>
      </div>
      <CampusPhoto class="conversation-art" src="/assets/jiangning-library.jpg" alt="河海大学江宁校区图书馆" caption="江宁校区图书馆" />
    </aside>

    <section class="chat-panel">
      <header class="chat-heading">
        <span class="chat-heading__icon"><el-icon><ChatDotRound /></el-icon></span>
        <div><h1>校园知识问答</h1><p>基于校园知识库与联网来源，为你提供可核验的答案</p></div>
      </header>

      <div ref="messageListRef" class="message-list" @scroll="handleMessageScroll">
        <div v-if="!messages.length" class="welcome-panel">
          <div class="welcome-visual"><CampusPhoto class="welcome-art" src="/assets/jiangning-aerial.jpg" alt="河海大学江宁校区航拍图" /></div>
          <h2>你好，我是河海智问</h2>
          <p>我可以帮你解答校园学习、生活和办事相关问题</p>
          <div class="suggestions">
            <button v-for="question in suggestions" :key="question" type="button" @click="send(question)"><el-icon><Search /></el-icon>{{ question }}</button>
          </div>
        </div>

        <article v-for="message in messages" :key="message.client_id" :class="['message-row',message.role.toLowerCase()]">
          <el-avatar v-if="message.role==='ASSISTANT'" class="assistant-avatar"><el-icon><ChatDotRound /></el-icon></el-avatar>
          <div class="message-wrap">
            <div class="message-meta"><span>{{ message.role==='USER' ? '我' : '河海智问' }}</span><time v-if="message.created_at">{{ formatTime(message.created_at) }}</time></div>
            <div class="message-bubble">
              <div v-if="message.content" class="markdown-body" v-html="renderMarkdown(message.content)" />
              <div v-else-if="message.status==='STREAMING'" class="thinking"><i/><i/><i/><span>{{ streamStatus || '正在检索可靠来源…' }}</span></div>
              <span v-if="message.status==='STREAMING' && message.content" class="stream-cursor" />
              <p v-if="message.status==='CANCELLED'" class="message-state">已停止生成，以上为已保留内容</p>
              <p v-if="message.status==='ERROR'" class="message-state error">回答生成失败，请稍后重试</p>
            </div>

            <el-collapse v-if="message.role==='ASSISTANT' && message.sources?.length && message.status!=='STREAMING'" class="source-collapse">
              <el-collapse-item :name="message.client_id">
                <template #title><span class="source-title"><el-icon><Document /></el-icon>参考来源（{{ message.sources.length }}）</span></template>
                <div class="source-list">
                  <div v-for="(source,index) in message.sources" :key="`${message.client_id}-${index}`" class="source-item">
                    <span :class="['source-badge',sourceTone(source)]">{{ sourceLabel(source) }}</span>
                    <div class="source-copy">
                      <strong>{{ source.title || source.site_name || '来源信息' }}</strong>
                      <p v-if="source.snippet || source.content">{{ source.snippet || source.content }}</p>
                      <div class="source-meta">
                        <span v-if="source.site_name">{{ source.site_name }}</span><span v-if="source.domain">{{ source.domain }}</span><span v-if="source.published_at">{{ source.published_at }}</span><span v-if="typeof source.score==='number'">匹配度 {{ Math.round(source.score*100) }}%</span>
                      </div>
                    </div>
                    <a v-if="sourceHref(source)" :href="sourceHref(source)" target="_blank" rel="noopener noreferrer">查看原文<el-icon><TopRight /></el-icon></a>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>

            <!-- 操作栏：复制 / 点赞入库 / 点踩纠错 -->
            <div v-if="message.role==='ASSISTANT' && message.content && message.status==='COMPLETE'" class="message-actions">
              <el-tag v-if="message.knowledge_task" size="small" :type="taskTagType(message.knowledge_task.status)" effect="light" round>{{ taskTagText(message.knowledge_task.status) }}</el-tag>
              <el-tag v-if="message.correction" size="small" :type="correctionTagType(message.correction.status)" effect="light" round>{{ correctionTagText(message.correction.status) }}</el-tag>
              <el-tooltip content="复制此回答" placement="top">
                <button class="action-btn" type="button" @click="copyAnswer(message.content)"><el-icon><DocumentCopy /></el-icon></button>
              </el-tooltip>
              <el-tooltip content="此答案准确，加入知识库" placement="top">
                <button class="action-btn" type="button" :disabled="!canAddToKnowledge(message)" @click="likeMessage(message)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" /></svg>
                </button>
              </el-tooltip>
              <el-tooltip content="此答案不准确，我来提供答案" placement="top">
                <button class="action-btn" type="button" :disabled="!canCorrect(message)" @click="startCorrection(message)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" /></svg>
                </button>
              </el-tooltip>
            </div>

            <!-- 纠错编辑框 -->
            <div v-if="message.id != null && correctingId === message.id" class="correction-editor">
              <el-input v-model="correctionDraft" type="textarea" :autosize="{ minRows: 3, maxRows: 8 }" maxlength="6000" show-word-limit placeholder="请输入你认为准确的答案，提交后由管理员审核" />
              <div class="correction-actions">
                <el-button size="small" @click="cancelCorrection">取消</el-button>
                <el-button size="small" type="primary" :loading="correctionSubmitting" :disabled="correctionDraft.trim().length < 2" @click="submitCorrectionDraft(message)">提交纠错</el-button>
              </div>
            </div>
          </div>
          <el-avatar v-if="message.role==='USER'" class="user-avatar">{{ userInitial }}</el-avatar>
        </article>
      </div>

      <button v-if="showBackToBottom" class="back-bottom" type="button" @click="backToBottom"><el-icon><Bottom /></el-icon>回到底部</button>
      <footer class="composer">
        <div v-if="streamError" class="stream-error"><el-icon><WarningFilled /></el-icon><span>{{ streamError }}</span><el-button link @click="streamError=''">关闭</el-button></div>
        <div class="composer-box">
          <el-input v-model="input" type="textarea" :autosize="{minRows:1,maxRows:5}" placeholder="输入校园相关问题，Enter 发送，Shift + Enter 换行" :disabled="sending" @keydown.enter="handleEnter" />
          <el-button v-if="sending" type="danger" :icon="CloseBold" @click="stopCurrentStream">停止</el-button>
          <el-button v-else type="primary" circle :icon="Promotion" :disabled="!input.trim()" aria-label="发送" @click="send(input)" />
        </div>
        <p>回答可能存在偏差，重要信息请以学校正式通知为准</p>
      </footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { Bottom, ChatDotRound, CloseBold, Delete, Document, DocumentCopy, Plus, Promotion, Search, TopRight, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { deleteConversation, getConversation, listConversations, createKnowledgeTask, getKnowledgeTask, submitCorrection } from '@/api/qa'
import { streamChat, type SSEEvent } from '@/utils/sse'
import { useUserStore } from '@/stores/user'
import type { ActiveChatStream, AnswerCorrection, AnswerKnowledgeTask, ChatMessage, Conversation, SourceRef } from '@/types'
import CampusPhoto from '@/components/CampusPhoto.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const conversations = ref<Conversation[]>([])
const activeId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const input = ref('')
const sending = ref(false)
const streamStatus = ref('')
const streamError = ref('')
const activeStream = ref<ActiveChatStream | null>(null)
const messageListRef = ref<HTMLElement>()
const isNearBottom = ref(true)
const showBackToBottom = ref(false)

const suggestions = ['河海大学有多少个学院？','研究生如何申请奖学金？','图书馆开放时间是几点？','校历在哪里查看？','计算机学院有哪些专业？']
const userInitial = computed(() => (userStore.user?.nickName || userStore.user?.userName || '我').charAt(0))

function createClientId(prefix: string) {
  const value = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  return `${prefix}-${value}`
}

function renderMarkdown(value: string) { return DOMPurify.sanitize(marked.parse(value || '') as string) }
function formatTime(value?: string) { return value ? value.replace('T',' ').slice(0,16) : '' }
function sourceHref(source: SourceRef) { return source.url ?? source.source_url }
function sourceLabel(source: SourceRef) {
  if (source.source_type === 'KNOWLEDGE_BASE') return source.citation_index != null ? `S${source.citation_index}` : 'S'
  if (source.source_type === 'WEB_SEARCH') return source.citation_index != null ? `W${source.citation_index}` : 'W'
  return '来源'
}
function sourceTone(source: SourceRef) { return source.source_type === 'KNOWLEDGE_BASE' ? 'knowledge' : source.source_type === 'WEB_SEARCH' ? 'web' : 'neutral' }
function answerOrigin(value: unknown): ChatMessage['answer_origin'] | undefined {
  return value === 'KNOWLEDGE_BASE' || value === 'WEB_SEARCH' || value === 'HYBRID' || value === 'NO_ANSWER' ? value : undefined
}

function findAssistant(stream: ActiveChatStream) { return messages.value.find(message => message.client_id === stream.assistantMessageId && message.request_id === stream.requestId) }
function updateAssistant(stream: ActiveChatStream, update: (message: ChatMessage) => ChatMessage) {
  messages.value = messages.value.map(message => message.client_id === stream.assistantMessageId && message.request_id === stream.requestId ? update(message) : message)
}

function handleMessageScroll() {
  const element = messageListRef.value
  if (!element) return
  isNearBottom.value = element.scrollHeight - element.scrollTop - element.clientHeight <= 120
  showBackToBottom.value = !isNearBottom.value && messages.value.length > 0
}
async function scrollToBottom(force = false) {
  if (!force && !isNearBottom.value) return
  await nextTick()
  const element = messageListRef.value
  if (!element) return
  element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
  if (force) { isNearBottom.value = true; showBackToBottom.value = false }
}
function backToBottom() { scrollToBottom(true) }

async function loadConversationList() {
  try { conversations.value = (await listConversations()).data } catch { conversations.value = [] }
}

function stopCurrentStream() {
  const stream = activeStream.value
  if (!stream) return
  activeStream.value = null
  updateAssistant(stream, message => ({ ...message, status: 'CANCELLED' }))
  stream.controller.abort()
  sending.value = false
  streamStatus.value = ''
}

function startNewChat() {
  stopCurrentStream()
  cancelCorrection()
  activeId.value = null
  messages.value = []
  streamError.value = ''
  isNearBottom.value = true
  showBackToBottom.value = false
}

async function openConversation(id: number) {
  if (id === activeId.value && messages.value.length) return
  stopCurrentStream()
  cancelCorrection()
  try {
    const response = await getConversation(id)
    activeId.value = id
    messages.value = (response.data.messages || []).map(message => ({
      ...message,
      id: typeof message.id === 'number' ? message.id : undefined,
      client_id: createClientId(message.role === 'USER' ? 'user' : 'assistant'),
      request_id: undefined,
      sources: message.sources || [],
      status: message.status || 'COMPLETE',
    }))
    streamError.value = ''
    await scrollToBottom(true)
  } catch { ElMessage.error('会话加载失败') }
}

async function removeConversation(id: number) {
  if (id === activeId.value) stopCurrentStream()
  try {
    await deleteConversation(id)
    if (id === activeId.value) startNewChat()
    await loadConversationList()
    ElMessage.success('会话已删除')
  } catch { /* interceptor reports error */ }
}

function invalidateMismatchedStream(stream: ActiveChatStream) {
  if (activeStream.value?.requestId !== stream.requestId) return
  activeStream.value = null
  stream.controller.abort()
  sending.value = false
  streamStatus.value = ''
  streamError.value = '会话响应校验失败，本次生成已安全停止'
}

function handleSseEvent(event: SSEEvent, eventRequestId: string) {
  const stream = activeStream.value
  if (!stream || eventRequestId !== stream.requestId || !findAssistant(stream)) return
  if (event.event === 'start') {
    const serverId = event.data.conversation_id as number | string
    if (stream.requestedConversationId != null && String(serverId) !== String(stream.requestedConversationId)) {
      invalidateMismatchedStream(stream)
      return
    }
    stream.serverConversationId = serverId
    if (stream.requestedConversationId == null) {
      const numericId = Number(serverId)
      if (!Number.isFinite(numericId)) { invalidateMismatchedStream(stream); return }
      activeId.value = numericId
    }
    // 记录助手消息的数据库 ID，点赞/纠错要用
    const startMessageId = Number(event.data.message_id)
    if (Number.isFinite(startMessageId)) updateAssistant(stream, message => ({ ...message, id: startMessageId }))
    return
  }
  const ownedConversationId = stream.serverConversationId ?? stream.requestedConversationId
  if (ownedConversationId != null && activeId.value != null && String(ownedConversationId) !== String(activeId.value)) return
  if (event.event === 'status') streamStatus.value = String(event.data.message || '正在处理…')
  if (event.event === 'delta') {
    const shouldFollow = isNearBottom.value
    streamStatus.value = ''
    updateAssistant(stream, message => ({ ...message, content: message.content + String(event.data.text || '') }))
    if (shouldFollow) scrollToBottom()
  }
  if (event.event === 'sources') {
    updateAssistant(stream, message => ({
      ...message,
      sources: Array.isArray(event.data.items) ? event.data.items as SourceRef[] : [],
      answer_origin: answerOrigin(event.data.answer_origin) ?? message.answer_origin,
    }))
  }
  if (event.event === 'done') {
    updateAssistant(stream, message => ({
      ...message,
      status: 'COMPLETE',
      latency_ms: typeof event.data.latency_ms === 'number' ? event.data.latency_ms : message.latency_ms,
      model: typeof event.data.model === 'string' ? event.data.model : message.model,
      answer_origin: answerOrigin(event.data.answer_origin) ?? message.answer_origin,
    }))
    loadConversationList()
  }
  if (event.event === 'error') {
    streamError.value = String(event.data.message || '回答生成失败')
    updateAssistant(stream, message => ({ ...message, status: 'ERROR' }))
  }
}

async function send(value: string) {
  const question = value.trim()
  if (!question || sending.value) return
  const requestId = createClientId('request')
  const userMessageId = createClientId('user')
  const assistantMessageId = createClientId('assistant')
  const requestedConversationId = activeId.value
  const controller = new AbortController()
  const stream: ActiveChatStream = { requestId, requestedConversationId, serverConversationId: null, controller, assistantMessageId }
  input.value = ''
  streamError.value = ''
  streamStatus.value = '正在连接问答服务…'
  messages.value.push(
    { client_id:userMessageId, role:'USER', content:question, sources:[], status:'COMPLETE', created_at:new Date().toISOString() },
    { client_id:assistantMessageId, request_id:requestId, role:'ASSISTANT', content:'', sources:[], status:'STREAMING', created_at:new Date().toISOString() },
  )
  activeStream.value = stream
  sending.value = true
  await scrollToBottom(true)
  try {
    await streamChat(question, requestedConversationId, controller.signal, event => handleSseEvent(event, requestId))
  } catch (error) {
    if (activeStream.value?.requestId !== requestId) return
    if (controller.signal.aborted) updateAssistant(stream, message => ({ ...message, status:'CANCELLED' }))
    else {
      streamError.value = error instanceof Error ? error.message : '连接中断，请重试'
      updateAssistant(stream, message => ({ ...message, status:'ERROR' }))
    }
  } finally {
    if (activeStream.value?.requestId === requestId) {
      activeStream.value = null
      sending.value = false
      streamStatus.value = ''
    }
  }
}

function handleEnter(event: KeyboardEvent) { if (!event.shiftKey) { event.preventDefault(); send(input.value) } }

// ── 复制 / 点赞沉淀 / 点踩纠错 ──
const likeSubmitting = ref<Set<number>>(new Set())
const correctingId = ref<number | null>(null)
const correctionDraft = ref('')
const correctionSubmitting = ref(false)
const pollTimers = new Map<number, ReturnType<typeof setInterval>>()

async function copyAnswer(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function patchMessageById(id: number, patch: Partial<ChatMessage>) {
  messages.value = messages.value.map(message => (message.id === id ? { ...message, ...patch } : message))
}

// 只有已完成、有 ID、非拒答、未沉淀过的回答才能点赞（对齐后端校验）
function canAddToKnowledge(message: ChatMessage) {
  return message.id != null
    && message.status === 'COMPLETE'
    && message.answer_origin !== 'NO_ANSWER'
    && !message.knowledge_task
    && !likeSubmitting.value.has(message.id)
}

async function likeMessage(message: ChatMessage) {
  if (!canAddToKnowledge(message) || message.id == null) return
  const id = message.id
  likeSubmitting.value = new Set(likeSubmitting.value).add(id)
  try {
    const res = await createKnowledgeTask(id)
    patchMessageById(id, { knowledge_task: res.data })
    ElMessage.success('已加入知识库处理队列')
    pollKnowledgeTask(id)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || err?.message || '提交失败')
  } finally {
    const next = new Set(likeSubmitting.value)
    next.delete(id)
    likeSubmitting.value = next
  }
}

// 轮询沉淀任务直到出结果（3s 一次，最多 20 次）
function pollKnowledgeTask(messageId: number) {
  let count = 0
  stopPoll(messageId)
  const timer = setInterval(async () => {
    count += 1
    try {
      const res = await getKnowledgeTask(messageId)
      if (res.data) patchMessageById(messageId, { knowledge_task: res.data })
      const status = res.data?.status
      if (status === 'COMPLETE' || status === 'FAILED' || count >= 20) {
        stopPoll(messageId)
        if (status === 'COMPLETE') ElMessage.success('答案已沉淀进知识库')
        if (status === 'FAILED') ElMessage.warning('答案沉淀失败：' + (res.data?.error || '未知原因'))
      }
    } catch {
      stopPoll(messageId)
    }
  }, 3000)
  pollTimers.set(messageId, timer)
}

function stopPoll(messageId: number) {
  const timer = pollTimers.get(messageId)
  if (timer) { clearInterval(timer); pollTimers.delete(messageId) }
}

// 无纠错记录、或上次被拒/失败时可再次纠错
function canCorrect(message: ChatMessage) {
  if (message.id == null || message.status !== 'COMPLETE') return false
  const st = message.correction?.status
  return !st || st === 'REJECTED' || st === 'FAILED'
}

function startCorrection(message: ChatMessage) {
  if (!canCorrect(message) || message.id == null) return
  correctingId.value = message.id
  correctionDraft.value = ''
}

function cancelCorrection() {
  correctingId.value = null
  correctionDraft.value = ''
}

async function submitCorrectionDraft(message: ChatMessage) {
  if (message.id == null || correctionSubmitting.value) return
  correctionSubmitting.value = true
  try {
    const res = await submitCorrection(message.id, correctionDraft.value.trim())
    patchMessageById(message.id, { correction: res.data })
    ElMessage.success('纠错已提交，等待管理员审核')
    cancelCorrection()
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.message || err?.message || '提交失败')
  } finally {
    correctionSubmitting.value = false
  }
}

// ── 状态标签 ──
function taskTagText(status: AnswerKnowledgeTask['status']) {
  return { QUEUED: '沉淀排队中', PROCESSING: '沉淀处理中', COMPLETE: '已入知识库', FAILED: '沉淀失败' }[status] || status
}
function taskTagType(status: AnswerKnowledgeTask['status']) {
  return ({ QUEUED: 'info', PROCESSING: 'warning', COMPLETE: 'success', FAILED: 'danger' } as const)[status] || 'info'
}
function correctionTagText(status: AnswerCorrection['status']) {
  return { PENDING: '纠错待审核', PROCESSING: '纠错处理中', APPROVED: '纠错已采纳', REJECTED: '纠错被拒绝', FAILED: '纠错失败' }[status] || status
}
function correctionTagType(status: AnswerCorrection['status']) {
  return ({ PENDING: 'info', PROCESSING: 'warning', APPROVED: 'success', REJECTED: 'danger', FAILED: 'danger' } as const)[status] || 'info'
}

onMounted(loadConversationList)
onBeforeRouteLeave(() => stopCurrentStream())
onBeforeUnmount(() => {
  stopCurrentStream()
  pollTimers.forEach(timer => clearInterval(timer))
  pollTimers.clear()
})
</script>

<style scoped>
.chat-page { display:grid; height:calc(100vh - 32px); min-height:620px; grid-template-columns:clamp(300px,22vw,360px) minmax(0,1fr); gap:16px; }
.conversation-pane,.chat-panel { position:relative; overflow:hidden; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); box-shadow:var(--shadow-sm); }
.conversation-pane { display:flex; flex-direction:column; }
.conversation-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:76px; padding:16px 16px 14px 20px; border-bottom:1px solid var(--border); }
.conversation-heading>div{display:flex;flex-direction:column}.conversation-heading strong{color:var(--text);font-size:18px}.conversation-heading span{color:var(--text-muted);font-size:11px}
.conversation-list { position:relative; z-index:2; flex:1; padding:10px; overflow:auto; }
.conversation-list :deep(.empty-state){min-height:280px}.conversation-item { display:flex; align-items:center; width:100%; min-height:68px; margin-bottom:4px; padding:10px 8px 10px 12px; color:var(--text-secondary); text-align:left; background:transparent; border:0; border-radius:10px; cursor:pointer; }
.conversation-item:hover,.conversation-item.active{background:var(--surface-hover)}.conversation-item.active{box-shadow:inset 3px 0 var(--brand)}
.conversation-item>span{display:flex;min-width:0;flex:1;flex-direction:column}.conversation-item strong{overflow:hidden;font-size:13px;text-overflow:ellipsis;white-space:nowrap}.conversation-item small{margin-top:5px;color:var(--text-muted);font-size:11px}.conversation-item.active strong{color:var(--brand)}
.conversation-art { position:absolute; right:0; bottom:18px; width:100%; height:220px; }
.conversation-art :deep(img){object-position:center 38%}
.chat-panel { display:flex; min-width:0; flex-direction:column; }
.chat-heading { display:flex; align-items:center; gap:14px; min-height:76px; padding:14px 22px; border-bottom:1px solid var(--border); }
.chat-heading__icon{display:grid;width:42px;height:42px;place-items:center;color:#fff;background:var(--brand);border-radius:12px;font-size:22px;box-shadow:var(--shadow-blue)}
.chat-heading h1{margin:0;color:var(--text);font-size:20px}.chat-heading p{margin:4px 0 0;color:var(--text-muted);font-size:12px}
.message-list { position:relative; flex:1; padding:26px clamp(18px,4vw,52px); overflow:auto; scroll-behavior:smooth; }
.welcome-panel { display:flex; max-width:900px; min-height:100%; margin:auto; flex-direction:column; align-items:center; justify-content:center; text-align:center; }
.welcome-visual{position:relative;width:min(800px,94%);height:300px;margin-bottom:-10px}.welcome-art{position:absolute;inset:62px 0 0;width:100%;height:220px}.welcome-art :deep(img){object-position:center 46%;opacity:.18}.welcome-robot{position:absolute;top:0;left:50%;z-index:2;width:360px;transform:translateX(-50%)}.welcome-panel h2{margin:0 0 8px;color:var(--brand);font-size:32px}.welcome-panel>p{margin:0;color:var(--text-muted);font-size:16px}
.suggestions { display:flex; max-width:820px; gap:10px; margin-top:28px; flex-wrap:wrap; justify-content:center; }.suggestions button{display:flex;align-items:center;gap:8px;padding:11px 15px;color:var(--brand);background:var(--surface);border:1px solid var(--border-strong);border-radius:999px;box-shadow:var(--shadow-sm);cursor:pointer}.suggestions button:hover{border-color:var(--brand);transform:translateY(-1px)}
.message-row { display:flex; max-width:980px; gap:12px; margin:0 auto 24px; align-items:flex-start; }.message-row.user{justify-content:flex-end}.message-wrap{max-width:min(820px,calc(100% - 55px));}.message-row.user .message-wrap{max-width:min(680px,calc(100% - 55px))}.message-meta{display:flex;align-items:center;gap:10px;margin:0 3px 6px;color:var(--text-muted);font-size:11px}.message-row.user .message-meta{justify-content:flex-end}.message-meta span{color:var(--text-secondary);font-weight:700}
.assistant-avatar,.user-avatar{flex:0 0 auto;color:#fff;background:var(--brand)}.assistant-avatar{background:linear-gradient(145deg,#5aa2f4,var(--brand))}.message-bubble{position:relative;padding:15px 18px;color:var(--text-secondary);background:var(--surface-soft);border:1px solid var(--border);border-radius:5px 16px 16px 16px}.message-row.user .message-bubble{color:#17365e;background:linear-gradient(135deg,#eaf4ff,#dfeeff);border-color:#cae0f8;border-radius:16px 5px 16px 16px}html.dark .message-row.user .message-bubble{color:var(--text);background:#173456;border-color:#29527d}
.markdown-body :deep(p){margin:0 0 10px}.markdown-body :deep(p:last-child){margin-bottom:0}.markdown-body :deep(ol),.markdown-body :deep(ul){padding-left:22px}.markdown-body :deep(code){padding:2px 5px;background:var(--code-bg);border-radius:5px}.markdown-body :deep(pre){padding:14px;overflow:auto;background:var(--code-bg);border-radius:10px}.markdown-body :deep(a){color:var(--brand)}
.thinking{display:flex;align-items:center;gap:5px;color:var(--text-muted)}.thinking i{width:6px;height:6px;background:var(--brand-light);border-radius:50%;animation:pulse 1s infinite}.thinking i:nth-child(2){animation-delay:.15s}.thinking i:nth-child(3){animation-delay:.3s}.thinking span{margin-left:5px}.stream-cursor{display:inline-block;width:2px;height:16px;margin-left:3px;vertical-align:-2px;background:var(--brand);animation:blink .7s infinite}.message-state{margin:10px 0 0;color:var(--text-muted);font-size:12px}.message-state.error{color:#e34b4b}
.source-collapse{margin-top:10px;border:1px solid var(--border);border-radius:12px;overflow:hidden}.source-collapse :deep(.el-collapse-item__header){height:44px;padding:0 14px;color:var(--text-secondary);background:var(--surface);border:0}.source-collapse :deep(.el-collapse-item__wrap){background:var(--surface);border:0}.source-title{display:flex;align-items:center;gap:8px;font-weight:700}.source-list{padding:0 12px 12px}.source-item{display:flex;align-items:flex-start;gap:10px;padding:12px 4px;border-top:1px solid var(--border)}.source-badge{display:grid;min-width:34px;height:26px;place-items:center;color:var(--text-muted);background:var(--surface-soft);border-radius:7px;font-size:12px;font-weight:800}.source-badge.knowledge{color:var(--brand);background:var(--brand-soft)}.source-badge.web{color:#7a4bd0;background:rgba(124,80,210,.1)}.source-copy{min-width:0;flex:1}.source-copy strong{color:var(--text);font-size:13px}.source-copy p{display:-webkit-box;margin:4px 0;color:var(--text-muted);font-size:12px;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden}.source-meta{display:flex;gap:10px;flex-wrap:wrap;color:var(--text-light);font-size:11px}.source-item>a{display:flex;align-items:center;gap:3px;white-space:nowrap;font-size:12px}
.message-actions{display:flex;align-items:center;justify-content:flex-end;gap:6px;margin-top:10px}
.message-actions .action-btn{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;color:var(--text-muted);background:var(--surface);border:1px solid var(--border);border-radius:8px;cursor:pointer;transition:all .2s ease}
.message-actions .action-btn svg{width:15px;height:15px}.message-actions .action-btn .el-icon{font-size:15px}
.message-actions .action-btn:hover:not(:disabled){color:var(--brand);border-color:var(--brand);background:var(--brand-soft)}
.message-actions .action-btn:disabled{opacity:.35;cursor:not-allowed}
.correction-editor{margin-top:10px;padding:12px;background:var(--surface-soft);border:1px solid var(--border);border-radius:12px}
.correction-editor .correction-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:8px}
.back-bottom{position:absolute;right:28px;bottom:112px;z-index:4;display:flex;align-items:center;gap:5px;padding:8px 12px;color:var(--brand);background:var(--surface);border:1px solid var(--border);border-radius:999px;box-shadow:var(--shadow-md);cursor:pointer}.composer{position:relative;padding:14px 22px 12px;background:var(--surface);border-top:1px solid var(--border)}.composer-box{display:flex;align-items:flex-end;gap:10px;padding:8px 9px 8px 14px;border:1px solid var(--border-strong);border-radius:14px}.composer-box:focus-within{border-color:var(--brand);box-shadow:0 0 0 3px var(--brand-soft)}.composer-box :deep(.el-textarea__inner){padding:7px 0;background:transparent;box-shadow:none!important;resize:none}.composer-box .el-button.is-circle{width:40px;height:40px;flex:0 0 auto}.composer>p{margin:7px 0 0;color:var(--text-light);font-size:10px;text-align:center}.stream-error{display:flex;align-items:center;gap:8px;margin-bottom:9px;padding:8px 10px;color:#c63d3d;background:rgba(239,68,68,.08);border-radius:8px;font-size:12px}.stream-error span{flex:1}
@keyframes pulse{0%,100%{opacity:.35;transform:translateY(0)}50%{opacity:1;transform:translateY(-3px)}}@keyframes blink{50%{opacity:0}}
@media(max-width:1180px){.chat-page{grid-template-columns:280px minmax(0,1fr)}.message-list{padding:22px 16px}.suggestions button{font-size:12px}}
@media(max-width:720px){.chat-page{height:auto;min-height:calc(100vh - 118px);grid-template-columns:1fr}.conversation-pane{max-height:220px}.conversation-art{display:none}.chat-panel{min-height:650px}.welcome-panel h2{font-size:24px}}
</style>
