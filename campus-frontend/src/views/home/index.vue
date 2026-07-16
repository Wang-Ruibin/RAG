<template>
  <div class="home-page">
    <div class="chat-container">
      <!-- 顶部标题 -->
      <div class="chat-header">
        <h3>河海智问</h3>
        <p>基于 AI 的河海大学校园知识助手，随时为你解答校园相关问题</p>
      </div>

      <!-- 对话区 -->
      <div class="chat-messages" ref="msgContainer">
        <div v-if="messages.length === 0" class="welcome">
          <el-icon class="welcome-icon"><ChatDotRound /></el-icon>
          <h4>你好，我是河海智问</h4>
          <p>你可以问我关于河海大学的任何问题</p>
          <div class="suggestions">
            <span v-for="q in suggestions" :key="q" class="suggestion-tag" @click="askQuestion(q)">
              {{ q }}
            </span>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" :class="['message', msg.role]">
          <div class="avatar">
            <template v-if="msg.role === 'user'">{{ userStore.user?.nickName?.charAt(0) || '我' }}</template>
            <el-icon v-else><ChatDotRound /></el-icon>
          </div>
          <div class="bubble">
            <div class="content" v-html="renderMarkdown(msg.content)"></div>
            <div v-if="msg.sources?.length" class="sources">
              <div class="sources-title">
                <el-icon><Document /></el-icon>
                <span>参考来源</span>
              </div>
              <span v-for="s in msg.sources" :key="s.title" class="source-tag">
                {{ s.title }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="avatar"><el-icon><ChatDotRound /></el-icon></div>
          <div class="bubble typing">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="chat-input">
        <el-input
          v-model="question"
          placeholder="输入你的问题，按 Enter 发送..."
          size="large"
          @keyup.enter="askQuestion(question)"
          :disabled="loading"
        >
          <template #append>
            <el-button :icon="Promotion" @click="askQuestion(question)" :disabled="loading || !question.trim()" />
          </template>
        </el-input>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { askQuestion as askApi } from '@/api/qa'
import { Promotion, ChatDotRound, Document } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const userStore = useUserStore()
const question = ref('')
const loading = ref(false)
const msgContainer = ref<HTMLElement>()

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: { title: string }[]
}
const messages = ref<Message[]>([])

const suggestions = [
  '河海大学有多少个学院？',
  '研究生如何申请奖学金？',
  '图书馆开放时间是几点？',
  '校历在哪里查看？',
  '计算机学院有哪些专业？'
]

function renderMarkdown(text: string) {
  return DOMPurify.sanitize(marked.parse(text) as string)
}

async function askQuestion(q: string) {
  const text = q.trim()
  if (!text || loading.value) return
  question.value = ''
  messages.value.push({ role: 'user', content: text })
  await scrollToBottom()
  loading.value = true
  try {
    const res = await askApi(text)
    messages.value.push({
      role: 'assistant',
      content: res.data.answer,
      sources: res.data.sources
    })
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。' })
  } finally {
    loading.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

onMounted(() => scrollToBottom())
</script>

<style scoped lang="scss">
.home-page {
  max-width: 860px;
  margin: 0 auto;
  height: calc(100vh - 104px);
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: var(--shadow);
  overflow: hidden;
  animation: rise-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes rise-in {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}

.chat-header {
  position: relative;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--grad-soft);
  h3 {
    display: flex;
    align-items: center;
    margin: 0 0 4px;
    font-size: 17px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--primary);
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

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome {
  text-align: center;
  padding: 48px 20px;
  animation: rise-in 0.6s cubic-bezier(0.22, 1, 0.36, 1) 0.15s both;

  .welcome-icon {
    position: relative;
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
    animation: icon-hover 4s ease-in-out infinite;
  }
  h4 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.01em;
    background: linear-gradient(90deg, var(--primary) 30%, var(--accent));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  p {
    color: var(--text-secondary);
    font-size: 14px;
    margin-bottom: 32px;
  }
  .suggestions {
    display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;
    .suggestion-tag {
      padding: 8px 16px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      color: var(--primary-light);
      border-radius: 999px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.22s cubic-bezier(0.22, 1, 0.36, 1);
      &:hover {
        color: var(--accent);
        border-color: transparent;
        background: var(--grad-soft);
        box-shadow: 0 4px 14px rgba(14, 140, 114, 0.18);
        transform: translateY(-2px);
      }
      &:active { transform: translateY(0) scale(0.97); }
    }
  }
}

@keyframes icon-hover {
  0%, 100% { transform: translateY(0); box-shadow: var(--glow); }
  50%      { transform: translateY(-5px); box-shadow: var(--glow-lg); }
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  animation: msg-in 0.35s cubic-bezier(0.22, 1, 0.36, 1) both;

  .avatar {
    width: 34px; height: 34px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
  }
  &.user {
    flex-direction: row-reverse;
    .avatar {
      background: var(--grad);
      color: #fff;
      box-shadow: 0 2px 8px rgba(14, 140, 114, 0.3);
    }
    .bubble {
      background: var(--grad);
      color: #fff;
      border: none;
      border-radius: 16px 4px 16px 16px;
      box-shadow: 0 4px 14px rgba(14, 140, 114, 0.25);
      .content { color: #fff; }
    }
  }
  &.assistant {
    .avatar {
      background: var(--accent-subtle);
      color: var(--accent);
      font-size: 16px;
      box-shadow: 0 2px 8px rgba(14, 33, 28, 0.12);
    }
    .bubble {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px 16px 16px 16px;
    }
  }
  .bubble {
    max-width: 75%;
    padding: 12px 16px;
    font-size: 14px;
    line-height: 1.6;
    transition: box-shadow 0.25s ease;
    .content { color: var(--primary-light); }
    .sources {
      margin-top: 12px; padding-top: 12px;
      border-top: 1px dashed var(--border);
      .sources-title {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        margin-bottom: 8px;
      }
      .source-tag {
        display: inline-block;
        padding: 3px 12px;
        background: var(--grad-soft);
        border: 1px solid transparent;
        border-radius: 999px;
        font-size: 12px;
        color: var(--accent);
        margin: 2px 4px 2px 0;
        transition: all 0.2s ease;
        &:hover { box-shadow: 0 2px 8px rgba(14, 140, 114, 0.2); }
      }
    }
  }
  .bubble.typing {
    .dot {
      display: inline-block; width: 7px; height: 7px;
      border-radius: 50%; background: var(--accent);
      margin-right: 4px;
      animation: blink 1.4s infinite both;
      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }
  }
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes blink {
  0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.chat-input {
  padding: 16px 24px 20px;
  border-top: 1px solid var(--border);
  :deep(.el-input__wrapper) {
    border-radius: 12px 0 0 12px;
  }
  :deep(.el-input-group__append) {
    background: var(--grad);
    border: none;
    border-radius: 0 12px 12px 0;
    box-shadow: var(--glow);
    transition: filter 0.2s ease;
    .el-button { color: #fff; }
    &:hover { filter: brightness(1.08); }
  }
}
</style>
