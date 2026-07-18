import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import {
  MessageSquare,
  Trash2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  User,
  Bot,
} from 'lucide-react'

interface Conversation {
  id: number
  title: string
  message_count: number
  updated_at: string
  created_at: string
}

interface Source {
  title?: string
  filename?: string
  page?: number
  score?: number
}

interface Message {
  id: number
  role: 'USER' | 'ASSISTANT'
  content: string
  sources?: Source[]
  created_at: string
}

interface ConversationDetail extends Conversation {
  messages: Message[]
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

function formatRelativeTime(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) {
      return d.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
    }
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return dateStr
  }
}

export default function ConversationsPage() {
  const navigate = useNavigate()

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Expanded conversation (view messages)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [expandedData, setExpandedData] =
    useState<ConversationDetail | null>(null)
  const [loadingMessages, setLoadingMessages] = useState(false)

  // Delete confirmation
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  useEffect(() => {
    fetchConversations()
  }, [])

  async function fetchConversations() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listConversations()
      setConversations(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '获取问答记录失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleExpand(id: number) {
    if (expandedId === id) {
      setExpandedId(null)
      setExpandedData(null)
      return
    }

    setExpandedId(id)
    setLoadingMessages(true)
    setError('')
    try {
      const data: ConversationDetail = await api.getConversation(id)
      setExpandedData(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载对话详情失败')
      setExpandedId(null)
    } finally {
      setLoadingMessages(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleteTarget(null)
    try {
      await api.deleteConversation(id)
      if (expandedId === id) {
        setExpandedId(null)
        setExpandedData(null)
      }
      await fetchConversations()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '删除对话失败')
    }
  }

  return (
    <div className="conversations-page">
      <div className="page-header">
        <div>
          <h1>问答记录</h1>
          <p className="page-subtitle">查看和管理历史问答记录</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchConversations}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>加载中...</p>
        </div>
      ) : conversations.length === 0 ? (
        <div className="empty-state">
          <MessageSquare size={48} />
          <p>暂无问答记录</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/chat')}
          >
            开始对话
          </button>
        </div>
      ) : (
        <div className="conversation-list">
          {conversations.map((conv) => {
            const isExpanded = expandedId === conv.id
            return (
              <div
                key={conv.id}
                className={`conversation-item ${
                  isExpanded ? 'expanded' : ''
                }`}
              >
                <div
                  className="conversation-header"
                  onClick={() => handleToggleExpand(conv.id)}
                >
                  <MessageSquare size={18} className="conv-icon" />
                  <div className="conv-info">
                    <span className="conv-title">{conv.title}</span>
                    <span className="conv-meta">
                      {conv.message_count} 条消息 ·{' '}
                      {formatRelativeTime(conv.updated_at)}
                    </span>
                  </div>
                  <button
                    className="btn btn-icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteTarget(conv.id)
                    }}
                    title="删除对话"
                  >
                    <Trash2 size={16} />
                  </button>
                  <span className="conv-expand-icon">
                    {isExpanded ? (
                      <ChevronUp size={18} />
                    ) : (
                      <ChevronDown size={18} />
                    )}
                  </span>
                </div>

                {/* Expanded messages */}
                {isExpanded && (
                  <div className="conversation-messages">
                    {loadingMessages ? (
                      <div className="loading-container">
                        <div className="spinner" />
                        <p>加载消息中...</p>
                      </div>
                    ) : expandedData?.messages &&
                      expandedData.messages.length > 0 ? (
                      expandedData.messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`conv-message ${
                            msg.role === 'USER'
                              ? 'conv-message-user'
                              : 'conv-message-assistant'
                          }`}
                        >
                          <div className="conv-message-avatar">
                            {msg.role === 'USER' ? (
                              <User size={16} />
                            ) : (
                              <Bot size={16} />
                            )}
                          </div>
                          <div className="conv-message-body">
                            <div className="conv-message-role">
                              {msg.role === 'USER' ? '用户' : 'AI 助手'}
                            </div>
                            <div className="conv-message-text">
                              {msg.content}
                            </div>
                            {msg.role === 'ASSISTANT' &&
                              msg.sources &&
                              msg.sources.length > 0 && (
                                <div className="conv-message-sources">
                                  <span className="sources-label">
                                    来源：
                                  </span>
                                  {msg.sources.map((src, si) => (
                                    <span key={si} className="source-badge">
                                      <ExternalLink size={12} />
                                      {src.title ||
                                        src.filename ||
                                        `来源 ${si + 1}`}
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
                      ))
                    ) : (
                      <div className="conv-messages-empty">暂无消息</div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Confirm Delete Dialog */}
      {deleteTarget !== null && (
        <div
          className="modal-overlay"
          onClick={() => setDeleteTarget(null)}
        >
          <div
            className="modal-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>确认删除</h3>
            <p>确定要删除此对话记录吗？删除后无法恢复。</p>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setDeleteTarget(null)}
              >
                取消
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleDelete(deleteTarget)}
              >
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
