<template>
  <div class="qa-layout">
    <!-- ========== 左侧会话栏 ========== -->
    <aside class="conversation-panel">
      <el-button type="primary" :icon="Plus" block @click="startNewChat" class="new-chat-btn">
        新对话
      </el-button>
      <div class="conversation-list">
        <div v-if="conversations.length === 0" class="empty-hint">暂无历史会话</div>
        <div
          v-for="conv in conversations"
          :key="conv.id"
          :class="['conversation-item', { active: conv.id === activeId }]"
          @click="openConversation(conv.id)"
        >
          <div class="conv-info">
            <span class="conv-title">{{ conv.title }}</span>
            <span class="conv-meta">{{ conv.message_count }} 条消息</span>
          </div>
          <el-popconfirm title="删除此会话？" width="180" @confirm="removeConversation(conv.id, $event)">
            <template #reference>
              <el-button class="conv-delete" text size="small" :icon="Delete" @click.stop />
            </template>
          </el-popconfirm>
        </div>
      </div>
    </aside>

    <!-- ========== 右侧对话区 ========== -->
    <main class="chat-main">
      <header class="chat-topbar">
        <h3>校园知识问答</h3>
        <p>答案来自校园知识库，重要信息请核对原文</p>
      </header>

      <!-- 消息列表 -->
      <section class="message-list" ref="msgListRef">
        <div v-if="messages.length === 0" class="welcome">
          <el-icon class="welcome-icon"><ChatDotRound /></el-icon>
          <h4>你好，我是河海智问</h4>
          <p>试试下面的问题，或者输入你想了解的校园资讯</p>
          <div class="suggestions">
            <span v-for="q in suggestions" :key="q" class="suggestion-tag" @click="send(q)">
              {{ q }}
            </span>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role.toLowerCase()]">
          <div class="message-avatar">
            <template v-if="msg.role === 'USER'">{{ userStore.user?.nickName?.charAt(0) || '我' }}</template>
            <el-icon v-else><ChatDotRound /></el-icon>
          </div>
          <div class="message-body">
            <!-- 流式输出中的文本 + 光标 -->
            <div class="message-content" v-html="renderMarkdown(msg.content)"></div>
            <span v-if="msg.status === 'STREAMING'" class="streaming-cursor">▌</span>

            <!-- 状态提示 -->
            <div v-if="msg.role === 'ASSISTANT' && !msg.content && msg.status === 'STREAMING'" class="status-text">
              <span class="dot-pulse"></span> {{ streamStatus || '正在思考...' }}
            </div>
            <div v-else-if="msg.status === 'ERROR'" class="status-error">回答生成失败，请重试</div>
            <div v-else-if="msg.status === 'CANCELLED'" class="status-cancelled">已停止生成</div>

            <!-- 引用来源（折叠面板） -->
            <div v-if="msg.sources?.length && msg.status !== 'STREAMING'" class="source-panel">
              <el-collapse>
                <el-collapse-item>
                  <template #title>
                    <div class="source-title-bar">
                      <el-icon><Document /></el-icon>
                      <span>参考来源（{{ msg.sources.length }}）</span>
                    </div>
                  </template>
                  <div v-for="(s, si) in msg.sources" :key="si" class="source-item">
                    <div class="source-header">
                      <span class="source-badge">S{{ si + 1 }}</span>
                      <span class="source-doc-title">{{ s.title }}</span>
                      <span v-if="s.score" class="source-score">{{ (s.score * 100).toFixed(0) }}%</span>
                    </div>
                    <div v-if="s.snippet" class="source-snippet">{{ s.snippet }}</div>
                    <a v-if="s.source_url" :href="s.source_url" target="_blank" class="source-link">查看原文 →</a>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>

        <div ref="bottomRef" />
      </section>

      <!-- 输入区 -->
      <footer class="composer">
        <div v-if="streamError" class="stream-error">
          <el-icon><WarningFilled /></el-icon> {{ streamError }}
          <el-button link type="primary" @click="streamError = ''">关闭</el-button>
        </div>
        <div class="input-row">
          <el-input
            v-model="input"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="输入校园相关问题，Enter 发送，Shift+Enter 换行"
            :disabled="sending"
            @keydown.enter="onEnter"
            class="chat-textarea"
          />
          <el-button
            v-if="sending"
            type="danger"
            :icon="CloseBold"
            @click="stopStreaming"
          >停止</el-button>
          <el-button
            v-else
            type="primary"
            :icon="Promotion"
            :disabled="!input.trim()"
            @click="send(input)"
            class="send-btn"
          >发送</el-button>
        </div>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { listConversations, getConversation, deleteConversation } from '@/api/qa'
import { streamChat, type SSEEvent } from '@/utils/sse'
import type { Conversation, ChatMessage, SourceRef } from '@/types'
import { Promotion, ChatDotRound, Document, Delete, Plus, CloseBold, WarningFilled } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const userStore = useUserStore()

// ── 会话 ──
const conversations = ref<Conversation[]>([])
const activeId = ref<number | null>(null)
const loadConversationList = () => listConversations().then(r => conversations.value = r.data).catch(() => {})

// ── 消息 ──
interface LocalMessage {
  role: 'USER' | 'ASSISTANT'
  content: string
  sources: SourceRef[]
  status: 'STREAMING' | 'COMPLETE' | 'CANCELLED' | 'ERROR'
}
const messages = ref<LocalMessage[]>([])
const msgListRef = ref<HTMLElement>()
const bottomRef = ref<HTMLElement>()

// ── 输入 ──
const input = ref('')
const sending = ref(false)
const streamStatus = ref('')
const streamError = ref('')
let abortController: AbortController | null = null

const suggestions = [
  '河海大学有多少个学院？',
  '研究生如何申请奖学金？',
  '图书馆开放时间是几点？',
  '校历在哪里查看？',
  '计算机学院有哪些专业？',
]

// ── Markdown ──
function renderMarkdown(text: string) {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text) as string)
}

// ── 滚动到底 ──
async function scrollToBottom() {
  await nextTick()
  bottomRef.value?.scrollIntoView({ behavior: 'smooth' })
}

// ── 会话操作 ──
function startNewChat() {
  activeId.value = null
  messages.value = []
  streamError.value = ''
}

async function openConversation(id: number) {
  try {
    const res = await getConversation(id)
    activeId.value = id
    messages.value = (res.data.messages || []).map(m => ({
      role: m.role,
      content: m.content,
      sources: m.sources || [],
      status: (m.status as LocalMessage['status']) || 'COMPLETE',
    }))
    streamError.value = ''
    await scrollToBottom()
  } catch {
    // 加载失败静默
  }
}

async function removeConversation(id: number, event?: any) {
  try {
    await deleteConversation(id)
    if (activeId.value === id) startNewChat()
    await loadConversationList()
  } catch { /* ignore */ }
}

// ── SSE 事件处理 ──
function handleSSEEvent(event: SSEEvent) {
  switch (event.event) {
    case 'start':
      activeId.value = Number(event.data.conversation_id)
      break
    case 'status':
      streamStatus.value = String(event.data.message || '正在处理...')
      break
    case 'delta':
      streamStatus.value = ''
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1
          ? { ...m, content: m.content + String(event.data.text || '') }
          : m
      )
      break
    case 'sources':
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1
          ? { ...m, sources: (event.data.items || []) as SourceRef[] }
          : m
      )
      break
    case 'done':
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1 ? { ...m, status: 'COMPLETE' } : m
      )
      loadConversationList()
      break
    case 'error':
      streamError.value = String(event.data.message || '回答生成失败')
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1 ? { ...m, status: 'ERROR' } : m
      )
      break
  }
}

// ── 发送 ──
async function send(text: string) {
  const question = (typeof text === 'string' ? text : input.value).trim()
  if (!question || sending.value) return
  input.value = ''
  streamError.value = ''
  streamStatus.value = '正在连接问答服务...'

  messages.value.push(
    { role: 'USER', content: question, sources: [], status: 'COMPLETE' },
    { role: 'ASSISTANT', content: '', sources: [], status: 'STREAMING' },
  )
  await scrollToBottom()
  sending.value = true

  abortController = new AbortController()
  try {
    await streamChat(question, activeId.value, abortController.signal, handleSSEEvent)
  } catch (err: any) {
    if (abortController?.signal.aborted) {
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1 ? { ...m, status: 'CANCELLED' } : m
      )
    } else {
      streamError.value = err?.message || '连接中断，请重试'
      messages.value = messages.value.map((m, i) =>
        i === messages.value.length - 1 ? { ...m, status: 'ERROR' } : m
      )
    }
  } finally {
    abortController = null
    streamStatus.value = ''
    sending.value = false
    await scrollToBottom()
  }
}

function stopStreaming() {
  abortController?.abort()
}

function onEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    e.preventDefault()
    send(input.value)
  }
}

watch(() => messages.value.length, () => scrollToBottom())

onMounted(() => loadConversationList())
</script>

<style scoped lang="scss">
// ========== 整体布局 ==========
.qa-layout {
  display: flex;
  height: calc(100vh - 104px);
  margin: -24px -40px; // 顶满 main-content padding
  overflow: hidden;
}

// ========== 左侧会话栏 ==========
.conversation-panel {
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--sidebar-line);
  display: flex;
  flex-direction: column;
  padding: 16px;
  gap: 12px;
  overflow: hidden;

  .new-chat-btn {
    border-radius: 10px;
    height: 40px;
  }

  .conversation-list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .empty-hint {
    text-align: center;
    font-size: 13px;
    color: var(--sidebar-text);
    padding: 24px 0;
    opacity: 0.7;
  }

  .conversation-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.2s ease;

    &:hover { background: var(--sidebar-hover); }
    &.active {
      background: var(--accent-subtle);
      .conv-title { color: var(--accent); font-weight: 600; }
    }

    .conv-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .conv-title {
      font-size: 13px;
      color: var(--sidebar-text-hover);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .conv-meta {
      font-size: 11px;
      color: var(--sidebar-text);
      opacity: 0.7;
    }
    .conv-delete {
      opacity: 0;
      transition: opacity 0.2s ease;
      color: var(--sidebar-text);
      &:hover { color: var(--dot-red); }
    }
    &:hover .conv-delete { opacity: 1; }
  }
}

// ========== 右侧对话区 ==========
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  min-width: 0;
}

.chat-topbar {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;

  h3 {
    display: flex;
    align-items: center;
    margin: 0 0 4px;
    font-size: 17px;
    font-weight: 700;
    color: var(--primary);
    font-family: var(--font-display);
    &::before {
      content: '';
      width: 9px;
      height: 9px;
      background: var(--seal);
      border-radius: 2px;
      transform: rotate(45deg);
      margin-right: 10px;
      box-shadow: 0 2px 6px rgba(196, 71, 47, 0.3);
    }
  }
  p {
    margin: 0 0 0 14px;
    font-size: 12px;
    color: var(--text-secondary);
  }
}

// ========== 消息列表 ==========
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

// 欢迎态
.welcome {
  text-align: center;
  padding: 48px 20px;
  animation: rise-in 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;

  .welcome-icon {
    font-size: 34px;
    color: #fff;
    width: 72px;
    height: 72px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 24px;
    background: var(--grad);
    box-shadow: var(--glow-lg);
    margin-bottom: 20px;
  }
  h4 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 700;
    font-family: var(--font-display);
    letter-spacing: -0.01em;
    background: linear-gradient(90deg, var(--primary) 30%, var(--accent));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  p {
    color: var(--text-secondary);
    font-size: 14px;
    margin-bottom: 28px;
  }
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
    .suggestion-tag {
      padding: 8px 16px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--accent);
      border-radius: 999px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.22s cubic-bezier(0.22, 1, 0.36, 1);
      &:hover {
        color: var(--accent-2);
        border-color: transparent;
        background: var(--grad-soft);
        box-shadow: 0 4px 14px rgba(14, 140, 114, 0.18);
        transform: translateY(-2px);
      }
      &:active { transform: translateY(0) scale(0.97); }
    }
  }
}

// ========== 消息气泡 ==========
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  animation: msg-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;

  .message-avatar {
    width: 34px;
    height: 34px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 600;
    flex-shrink: 0;
  }

  &.user {
    flex-direction: row-reverse;
    .message-avatar {
      background: var(--grad);
      color: #fff;
      box-shadow: 0 2px 8px rgba(14, 140, 114, 0.3);
    }
    .message-body {
      background: var(--grad);
      color: #fff;
      border: none;
      border-radius: 16px 4px 16px 16px;
      box-shadow: 0 4px 14px rgba(14, 140, 114, 0.25);
      :deep(p) { color: #fff; }
    }
  }

  &.assistant {
    .message-avatar {
      background: var(--accent-subtle);
      color: var(--accent);
      font-size: 16px;
    }
    .message-body {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 4px 16px 16px 16px;
    }
  }

  .message-body {
    max-width: 75%;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.7;
    transition: box-shadow 0.25s ease;
    min-width: 0;

    :deep(p) { margin: 0 0 8px; &:last-child { margin-bottom: 0; } }
    :deep(ul), :deep(ol) { padding-left: 1.2em; margin: 4px 0; }
    :deep(code) {
      background: var(--bg-hover);
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 13px;
    }
    :deep(pre) {
      background: var(--bg);
      padding: 12px;
      border-radius: 8px;
      overflow-x: auto;
      code { background: none; padding: 0; }
    }
    :deep(a) { color: var(--accent); text-decoration: underline; }
    :deep(blockquote) {
      border-left: 3px solid var(--accent);
      margin: 8px 0;
      padding: 4px 12px;
      color: var(--text-secondary);
    }
  }
}

.streaming-cursor {
  color: var(--accent);
  animation: blink-cursor 0.8s infinite;
  font-weight: 300;
}

@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes rise-in {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.status-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  .dot-pulse {
    display: inline-block;
    width: 6px;
    height: 6px;
    background: var(--accent);
    border-radius: 50%;
    animation: dot-breathe 1.4s ease-in-out infinite;
  }
}

.status-error { color: var(--dot-red); font-size: 13px; }
.status-cancelled { color: var(--text-secondary); font-size: 13px; }

@keyframes dot-breathe {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

// ========== 引用来源面板 ==========
.source-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);

  :deep(.el-collapse) { border: none; }
  :deep(.el-collapse-item__header) { border: none; background: none; height: auto; padding: 0; line-height: 1; }
  :deep(.el-collapse-item__wrap) { border: none; background: none; }
  :deep(.el-collapse-item__content) { padding: 8px 0 0; }

  .source-title-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
  }

  .source-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--border);
    &:last-child { border-bottom: none; }

    .source-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }
    .source-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      background: var(--grad);
      color: #fff;
      border-radius: 5px;
      font-size: 11px;
      font-weight: 600;
      flex-shrink: 0;
    }
    .source-doc-title {
      flex: 1;
      font-size: 13px;
      font-weight: 600;
      color: var(--primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .source-score {
      font-size: 12px;
      color: var(--accent);
      font-weight: 600;
      background: var(--accent-subtle);
      padding: 1px 8px;
      border-radius: 999px;
    }
    .source-snippet {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.6;
      margin: 4px 0;
      padding-left: 28px;
    }
    .source-link {
      display: inline-block;
      margin-left: 28px;
      font-size: 12px;
      color: var(--accent);
      text-decoration: none;
      &:hover { text-decoration: underline; }
    }
  }
}

// ========== 输入区 ==========
.composer {
  padding: 12px 24px 18px;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
  flex-shrink: 0;

  .stream-error {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--dot-red);
    background: rgba(239, 68, 68, 0.08);
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 10px;
  }

  .input-row {
    display: flex;
    align-items: flex-end;
    gap: 10px;
  }

  .chat-textarea {
    flex: 1;
    :deep(.el-textarea__inner) {
      border-radius: 12px;
      font-size: 14px;
      padding: 10px 14px;
      line-height: 1.5;
      resize: none;
    }
  }

  .send-btn {
    border-radius: 12px;
    flex-shrink: 0;
    height: 40px;
  }
}
</style>
