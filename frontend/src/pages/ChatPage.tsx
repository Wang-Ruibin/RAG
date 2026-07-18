import { useState, useEffect, useRef, useCallback, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import {
  Send,
  Plus,
  MessageSquare,
  Loader2,
  ExternalLink,
  Trash2,
} from 'lucide-react'

interface Conversation {
  id: number
  title: string
  message_count: number
  updated_at: string
}

interface Source {
  title?: string
  filename?: string
  page?: number
  score?: number
  content?: string
}

interface Message {
  id?: number
  role: 'USER' | 'ASSISTANT'
  content: string
  sources?: Source[]
}

interface ConversationDetail {
  id: number
  title: string
  messages: Message[]
}

type SSEEvent = { type: string; data: any }

export default function ChatPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loadingConversations, setLoadingConversations] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Fetch conversations on mount
  useEffect(() => {
    fetchConversations()
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  async function fetchConversations() {
    setLoadingConversations(true)
    try {
      const data = await api.listConversations()
      setConversations(data)
    } catch {
      // silently fail - conversation list is non-critical
    } finally {
      setLoadingConversations(false)
    }
  }

  async function handleSelectConversation(id: number) {
    if (streaming) return
    setActiveConversationId(id)
    setLoadingMessages(true)
    setError('')
    try {
      const data: ConversationDetail = await api.getConversation(id)
      setMessages(data.messages)
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: data.title } : c))
      )
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载对话失败')
    } finally {
      setLoadingMessages(false)
    }
  }

  function handleNewChat() {
    if (streaming) return
    setActiveConversationId(null)
    setMessages([])
    setError('')
    setInput('')
    inputRef.current?.focus()
  }

  async function handleSubmit(e?: FormEvent) {
    e?.preventDefault()
    const question = input.trim()
    if (!question || streaming) return

    setError('')
    setInput('')

    // Add user message immediately
    const userMessage: Message = { role: 'USER', content: question }
    setMessages((prev) => [...prev, userMessage])

    // Add placeholder assistant message
    const assistantMessage: Message = { role: 'ASSISTANT', content: '' }
    setMessages((prev) => [...prev, assistantMessage])
    setStreaming(true)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      let currentSources: Source[] = []

      const eventStream = api.streamChat(question, activeConversationId ?? undefined)

      for await (const event of eventStream) {
        if (event.type === 'meta') {
          if (event.data.sources) currentSources = event.data.sources
          if (event.data.conversation_id) {
            setActiveConversationId(event.data.conversation_id)
          }
        } else if (event.type === 'token') {
          const text = event.data?.text || ''
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'ASSISTANT') {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + text,
                sources: currentSources,
              }
            }
            return updated
          })
        } else if (event.type === 'done') {
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'ASSISTANT' && currentSources.length > 0) {
              updated[updated.length - 1] = {
                ...last,
                sources: currentSources,
              }
            }
            return updated
          })
        }
      }

      // Refresh conversation list after stream completes
      fetchConversations()
    } catch (err: any) {
      if (err?.name === 'AbortError') {
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.role === 'ASSISTANT' && !last.content) {
            updated.pop() // Remove empty assistant message
          }
          return updated
        })
      } else {
        setError(err?.message || '发送消息失败')
        // Remove empty assistant message on error
        setMessages((prev) => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          if (last?.role === 'ASSISTANT' && !last.content) {
            updated.pop()
          }
          return updated
        })
      }
    } finally {
      setStreaming(false)
      abortControllerRef.current = null
      inputRef.current?.focus()
    }
  }

  async function handleDeleteConversation(
    id: number,
    e: React.MouseEvent
  ) {
    e.stopPropagation()
    if (streaming) return
    if (!window.confirm('确定要删除此对话吗？')) return

    try {
      await api.deleteConversation(id)
      if (activeConversationId === id) {
        setActiveConversationId(null)
        setMessages([])
      }
      fetchConversations()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '删除对话失败')
    }
  }

  function formatTime(dateStr: string): string {
    try {
      const d = new Date(dateStr)
      const now = new Date()
      const diffMs = now.getTime() - d.getTime()
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

      if (diffDays === 0) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      if (diffDays === 1) return '昨天'
      if (diffDays < 7) return `${diffDays}天前`
      return d.toLocaleDateString('zh-CN')
    } catch {
      return ''
    }
  }

  return (
    <div className="chat-page">
      {/* Sidebar */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <button className="btn btn-primary btn-block" onClick={handleNewChat}>
            <Plus size={16} />
            新对话
          </button>
        </div>

        <div className="chat-conversation-list">
          {loadingConversations ? (
            <div className="chat-sidebar-loading">
              <Loader2 size={20} className="spin" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="chat-sidebar-empty">暂无对话</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`chat-conversation-item ${
                  activeConversationId === conv.id ? 'active' : ''
                }`}
                onClick={() => handleSelectConversation(conv.id)}
              >
                <MessageSquare size={16} className="chat-conv-icon" />
                <div className="chat-conv-info">
                  <span className="chat-conv-title">{conv.title}</span>
                  <span className="chat-conv-meta">
                    {conv.message_count} 条消息 · {formatTime(conv.updated_at)}
                  </span>
                </div>
                <button
                  className="chat-conv-delete"
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  title="删除对话"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-main">
        {error && <div className="chat-error-bar">{error}</div>}

        {loadingMessages ? (
          <div className="chat-loading">
            <Loader2 size={32} className="spin" />
            <p>加载对话中...</p>
          </div>
        ) : messages.length === 0 && !streaming ? (
          <div className="chat-empty">
            <MessageSquare size={48} />
            <h2>河海大学校园问答助手</h2>
            <p>请输入您的问题，开始智能问答</p>
          </div>
        ) : (
          <div className="chat-messages">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`chat-message ${
                  msg.role === 'USER' ? 'chat-message-user' : 'chat-message-assistant'
                }`}
              >
                <div className="chat-message-avatar">
                  {msg.role === 'USER' ? 'U' : 'AI'}
                </div>
                <div className="chat-message-content">
                  <div className="chat-message-text">
                    {msg.content || (streaming && idx === messages.length - 1 ? (
                      <span className="chat-cursor">|</span>
                    ) : (
                      ''
                    ))}
                  </div>

                  {/* Sources */}
                  {msg.role === 'ASSISTANT' &&
                    msg.sources &&
                    msg.sources.length > 0 && (
                      <div className="chat-message-sources">
                        <span className="sources-label">来源：</span>
                        {msg.sources.map((src, si) => (
                          <span key={si} className="source-badge">
                            <ExternalLink size={12} />
                            {src.title || src.filename || `来源 ${si + 1}`}
                            {src.score != null && (
                              <span className="source-score">
                                {(src.score * 100).toFixed(0)}%
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input Area */}
        <form className="chat-input-area" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="chat-input"
            placeholder="输入您的问题..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
            autoFocus
          />
          <button
            className="btn btn-primary chat-send-btn"
            type="submit"
            disabled={!input.trim() || streaming}
          >
            {streaming ? (
              <Loader2 size={18} className="spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </form>
      </main>
    </div>
  )
}
