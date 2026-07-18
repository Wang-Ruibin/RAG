import { CheckOutlined, CloseOutlined, CopyOutlined, DeleteOutlined, DislikeOutlined, EditOutlined, LikeOutlined, PlusOutlined, SearchOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import { Alert, Button, Input, List, Popconfirm, Space, Spin, Tag, Tooltip, Typography, message } from 'antd'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../lib/api'
import { streamChat, type SSEEvent } from '../lib/sse'
import type { AnswerCorrection, AnswerKnowledgeTask, ChatMessage, Conversation, SourceRef } from '../types'
import { SourceCards } from '../components/SourceCards'

const WELCOME_MESSAGES = [
  '你好，我是河海智答，专门帮助你了解河海大学。想先了解学校概况、招生信息，还是校园生活？',
  '欢迎来到河海智答！我是你的河海大学校园知识助手，有什么关于河海大学的问题都可以问我。',
  '你好呀，我是河海智答。我可以帮你查询河海大学的院系、招生、校史和校园服务等信息。',
  '很高兴见到你！我是河海大学校园知识助手“河海智答”，请告诉我你想了解什么。',
]
const TASK_STATUS_PRESENTATION: Record<AnswerKnowledgeTask['status'], { text: string; color: string }> = {
  QUEUED: { text: '知识库排队中', color: 'gold' },
  PROCESSING: { text: '知识库处理中', color: 'blue' },
  COMPLETE: { text: '已加入知识库', color: 'green' },
  FAILED: { text: '加入知识库失败', color: 'red' },
}
const CORRECTION_STATUS_PRESENTATION: Record<AnswerCorrection['status'], { text: string; color: string }> = {
  PENDING: { text: '纠错待审核', color: 'gold' },
  PROCESSING: { text: '纠错入库中', color: 'blue' },
  APPROVED: { text: '纠错已采纳', color: 'green' },
  REJECTED: { text: '纠错已拒绝', color: 'red' },
  FAILED: { text: '纠错入库失败', color: 'red' },
}

function randomWelcomeMessage(previous?: string) {
  const candidates = previous
    ? WELCOME_MESSAGES.filter((item) => item !== previous)
    : WELCOME_MESSAGES
  return candidates[Math.floor(Math.random() * candidates.length)]
}

function updateLastMessage(
  messages: ChatMessage[],
  update: (message: ChatMessage) => ChatMessage,
) {
  if (messages.length === 0) return messages
  const next = [...messages]
  next[next.length - 1] = update(next[next.length - 1])
  return next
}

function conversationListPath(query: string) {
  const normalized = query.trim()
  return normalized ? `/api/conversations?q=${encodeURIComponent(normalized)}` : '/api/conversations'
}

export function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationQuery, setConversationQuery] = useState('')
  const [editingConversationId, setEditingConversationId] = useState<number | null>(null)
  const [conversationTitleDraft, setConversationTitleDraft] = useState('')
  const [renamingConversationId, setRenamingConversationId] = useState<number | null>(null)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [streamError, setStreamError] = useState('')
  const [streamStatus, setStreamStatus] = useState('')
  const [knowledgeSubmitting, setKnowledgeSubmitting] = useState<Set<number>>(new Set())
  const [correctionSubmitting, setCorrectionSubmitting] = useState<Set<number>>(new Set())
  const [correctingMessageId, setCorrectingMessageId] = useState<number | null>(null)
  const [correctionDraft, setCorrectionDraft] = useState('')
  const [welcomeMessage, setWelcomeMessage] = useState(() => randomWelcomeMessage())
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const deletingConversationIds = useRef(new Set<number>())
  const pollingTaskIds = useRef(new Set<number>())

  const loadConversations = (query = conversationQuery) => (
    api<Conversation[]>(conversationListPath(query)).then(setConversations)
  )
  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(() => {
      void api<Conversation[]>(conversationListPath(conversationQuery))
        .then((items) => { if (!cancelled) setConversations(items) })
        .catch((reason) => {
          if (!cancelled) void message.error(reason instanceof Error ? reason.message : '搜索会话失败')
        })
    }, 250)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [conversationQuery])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function openConversation(id: number) {
    setLoadingHistory(true)
    try {
      const conversation = await api<Conversation>(`/api/conversations/${id}`)
      setActiveId(id)
      setMessages(conversation.messages || [])
      ;(conversation.messages || []).forEach((item) => {
        const task = item.knowledge_task
        if (task && ['QUEUED', 'PROCESSING'].includes(task.status)) pollKnowledgeTask(task.id)
      })
      setStreamError('')
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '加载失败')
    } finally {
      setLoadingHistory(false)
    }
  }

  function handleEvent(event: SSEEvent) {
    if (event.event === 'start') {
      const id = Number(event.data.conversation_id)
      const messageId = Number(event.data.message_id)
      setActiveId(id)
      if (Number.isFinite(messageId)) {
        setMessages((current) => updateLastMessage(current, (item) => ({ ...item, id: messageId })))
      }
    } else if (event.event === 'status') {
      setStreamStatus(String(event.data.message || '正在处理…'))
    } else if (event.event === 'sources') {
      const sources = (event.data.items || []) as SourceRef[]
      const answer_origin = event.data.answer_origin as ChatMessage['answer_origin']
      setMessages((current) => updateLastMessage(current, (item) => ({
        ...item,
        sources,
        answer_origin: answer_origin ?? item.answer_origin,
      })))
    } else if (event.event === 'delta') {
      const text = String(event.data.text || '')
      setMessages((current) => updateLastMessage(current, (item) => ({
        ...item,
        content: item.content + text,
      })))
    } else if (event.event === 'done') {
      setStreamStatus('')
      const answer_origin = event.data.answer_origin as ChatMessage['answer_origin']
      setMessages((current) => updateLastMessage(current, (item) => ({
        ...item,
        status: 'COMPLETE',
        answer_origin: answer_origin ?? item.answer_origin,
      })))
    } else if (event.event === 'error') {
      setStreamStatus('')
      setStreamError(String(event.data.message || '回答生成失败'))
      setMessages((current) => updateLastMessage(current, (item) => ({ ...item, status: 'ERROR' })))
    }
  }

  async function send() {
    const question = input.trim()
    if (!question || sending) return
    setInput('')
    setSending(true)
    setStreamError('')
    setStreamStatus('正在连接问答服务…')
    setMessages((current) => [
      ...current,
      { role: 'USER', content: question, sources: [], status: 'COMPLETE' },
      { role: 'ASSISTANT', content: '', sources: [], status: 'STREAMING' },
    ])
    const controller = new AbortController()
    abortRef.current = controller
    try {
      await streamChat(question, activeId, controller.signal, handleEvent)
      await loadConversations()
    } catch (reason) {
      const status = controller.signal.aborted ? 'CANCELLED' : 'ERROR'
      setMessages((current) => updateLastMessage(current, (item) => ({ ...item, status })))
      if (!controller.signal.aborted) {
        setStreamError(reason instanceof Error ? reason.message : '连接中断')
      }
    } finally {
      abortRef.current = null
      setStreamStatus('')
      setSending(false)
    }
  }

  async function removeConversation(id: number) {
    if (deletingConversationIds.current.has(id)) return
    deletingConversationIds.current.add(id)
    try {
      await api(`/api/conversations/${id}`, { method: 'DELETE' })
      if (activeId === id) {
        setActiveId(null)
        setMessages([])
        setWelcomeMessage((current) => randomWelcomeMessage(current))
      }
      await loadConversations()
      void message.success('会话已删除')
    } finally {
      deletingConversationIds.current.delete(id)
    }
  }

  function startConversationRename(item: Conversation) {
    setEditingConversationId(item.id)
    setConversationTitleDraft(item.title)
  }

  function cancelConversationRename() {
    setEditingConversationId(null)
    setConversationTitleDraft('')
  }

  async function renameConversation(id: number) {
    const title = conversationTitleDraft.trim()
    if (!title) {
      void message.warning('会话标题不能为空')
      return
    }
    if (renamingConversationId === id) return
    setRenamingConversationId(id)
    try {
      await api<Pick<Conversation, 'id' | 'title' | 'created_at' | 'updated_at'>>(`/api/conversations/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ title }),
      })
      cancelConversationRename()
      await loadConversations()
      void message.success('会话已重命名')
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '重命名失败')
    } finally {
      setRenamingConversationId(null)
    }
  }

  async function addToKnowledge(item: ChatMessage) {
    if (!item.id || knowledgeSubmitting.has(item.id)) return
    setKnowledgeSubmitting((current) => new Set(current).add(item.id as number))
    try {
      const task = await api<AnswerKnowledgeTask>(`/api/messages/${item.id}/knowledge-task`, {
        method: 'POST',
      })
      setMessages((current) => current.map((messageItem) =>
        messageItem.id === item.id ? { ...messageItem, knowledge_task: task } : messageItem,
      ))
      if (['QUEUED', 'PROCESSING'].includes(task.status)) pollKnowledgeTask(task.id)
      void message.success('已加入知识库处理队列')
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '加入知识库失败')
    } finally {
      setKnowledgeSubmitting((current) => {
        const next = new Set(current)
        if (item.id) next.delete(item.id)
        return next
      })
    }
  }

  async function copyAnswer(content: string) {
    try {
      await navigator.clipboard.writeText(content)
      void message.success('回答已复制')
    } catch {
      void message.error('复制失败，请手动选择文本')
    }
  }

  function startCorrection(item: ChatMessage) {
    if (!item.id) return
    setCorrectingMessageId(item.id)
    setCorrectionDraft(item.correction?.proposed_answer || '')
  }

  async function submitCorrection(item: ChatMessage) {
    if (!item.id || correctionSubmitting.has(item.id) || !correctionDraft.trim()) return
    setCorrectionSubmitting((current) => new Set(current).add(item.id as number))
    try {
      const correction = await api<AnswerCorrection>(`/api/messages/${item.id}/correction`, {
        method: 'POST',
        body: JSON.stringify({ corrected_answer: correctionDraft.trim() }),
      })
      setMessages((current) => current.map((messageItem) =>
        messageItem.id === item.id ? { ...messageItem, correction } : messageItem,
      ))
      setCorrectingMessageId(null)
      setCorrectionDraft('')
      void message.success('纠错已提交，等待管理员审核')
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '纠错提交失败')
    } finally {
      setCorrectionSubmitting((current) => {
        const next = new Set(current)
        if (item.id) next.delete(item.id)
        return next
      })
    }
  }

  function taskTag(task: AnswerKnowledgeTask) {
    const presentation = TASK_STATUS_PRESENTATION[task.status]
    return <Tag color={presentation.color}>{presentation.text}</Tag>
  }

  function correctionTag(correction: AnswerCorrection) {
    const presentation = CORRECTION_STATUS_PRESENTATION[correction.status]
    return (
      <Tooltip title={correction.review_note || correction.error || presentation.text}>
        <Tag color={presentation.color}>{presentation.text}</Tag>
      </Tooltip>
    )
  }

  function mergeKnowledgeTask(task: AnswerKnowledgeTask) {
    setMessages((current) => current.map((item) =>
      item.id === task.assistant_message_id ? { ...item, knowledge_task: task } : item,
    ))
  }

  function pollKnowledgeTask(taskId: number, attempt = 0) {
    if (pollingTaskIds.current.has(taskId) && attempt === 0) return
    pollingTaskIds.current.add(taskId)
    window.setTimeout(() => {
      api<AnswerKnowledgeTask>(`/api/knowledge-tasks/${taskId}`)
        .then((task) => {
          mergeKnowledgeTask(task)
          if (['QUEUED', 'PROCESSING'].includes(task.status) && attempt < 60) {
            pollKnowledgeTask(taskId, attempt + 1)
          } else {
            pollingTaskIds.current.delete(taskId)
          }
        })
        .catch(() => pollingTaskIds.current.delete(taskId))
    }, 2500)
  }

  function canAddToKnowledge(item: ChatMessage) {
    return item.role === 'ASSISTANT'
      && item.status === 'COMPLETE'
      && Boolean(item.id)
      && Boolean(item.content.trim())
      && item.answer_origin !== 'NO_ANSWER'
      && !item.knowledge_task
      && !item.correction
  }

  function canCorrect(item: ChatMessage) {
    return item.role === 'ASSISTANT'
      && item.status === 'COMPLETE'
      && Boolean(item.id)
      && Boolean(item.content.trim())
      && !item.knowledge_task
      && (!item.correction || ['REJECTED', 'FAILED'].includes(item.correction.status))
  }

  function startNewConversation() {
    setConversationQuery('')
    cancelConversationRename()
    setActiveId(null)
    setMessages([])
    setStreamError('')
    setStreamStatus('')
    setWelcomeMessage((current) => randomWelcomeMessage(current))
  }

  return (
    <div className="chat-layout">
      <aside className="conversation-panel">
        <Button type="primary" icon={<PlusOutlined />} block onClick={startNewConversation}>
          新对话
        </Button>
        <Input
          className="conversation-search"
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索历史会话"
          value={conversationQuery}
          onChange={(event) => {
            setConversationQuery(event.target.value)
            cancelConversationRename()
          }}
        />
        <List
          dataSource={conversations}
          locale={{ emptyText: conversationQuery.trim() ? '没有匹配的历史会话' : '还没有历史会话' }}
          renderItem={(item) => {
            const isEditing = editingConversationId === item.id
            return (
              <List.Item
                className={activeId === item.id ? 'conversation active' : 'conversation'}
                onClick={() => {
                  if (!isEditing && !deletingConversationIds.current.has(item.id)) void openConversation(item.id)
                }}
                actions={isEditing ? [
                  <Tooltip title="保存" key="save">
                    <Button
                      aria-label="保存会话标题"
                      type="text"
                      size="small"
                      loading={renamingConversationId === item.id}
                      icon={<CheckOutlined />}
                      onClick={(event) => {
                        event.stopPropagation()
                        void renameConversation(item.id)
                      }}
                    />
                  </Tooltip>,
                  <Tooltip title="取消" key="cancel">
                    <Button
                      aria-label="取消重命名"
                      type="text"
                      size="small"
                      icon={<CloseOutlined />}
                      onClick={(event) => {
                        event.stopPropagation()
                        cancelConversationRename()
                      }}
                    />
                  </Tooltip>,
                ] : [
                  <Tooltip title="重命名" key="rename">
                    <Button
                      aria-label={`重命名会话：${item.title}`}
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={(event) => {
                        event.stopPropagation()
                        startConversationRename(item)
                      }}
                    />
                  </Tooltip>,
                  <Popconfirm
                    key="delete"
                    title="删除这个会话？"
                    onConfirm={(event) => {
                      event?.stopPropagation()
                      return removeConversation(item.id)
                    }}
                    onCancel={(event) => event?.stopPropagation()}
                  >
                    <Button aria-label={`删除会话：${item.title}`} type="text" danger size="small" icon={<DeleteOutlined />} onClick={(event) => event.stopPropagation()} />
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  title={isEditing ? (
                    <Input
                      aria-label="编辑会话标题"
                      autoFocus
                      maxLength={200}
                      size="small"
                      value={conversationTitleDraft}
                      onChange={(event) => setConversationTitleDraft(event.target.value)}
                      onClick={(event) => event.stopPropagation()}
                      onPressEnter={() => void renameConversation(item.id)}
                    />
                  ) : item.title}
                  description={`${item.message_count} 条消息`}
                />
              </List.Item>
            )
          }}
        />
      </aside>
      <main className="chat-main">
        <header className="page-header">
          <div><Typography.Title level={3}>校园知识问答</Typography.Title><Typography.Text type="secondary">答案来自校园知识库，请通过引用原文核实重要信息</Typography.Text></div>
        </header>
        <section className="message-list">
          {loadingHistory ? <Spin /> : messages.length === 0 ? (
            <article className="message assistant" data-testid="welcome-message">
              <div className="message-role">河海智答</div>
              <div className="message-body">
                <Typography.Paragraph>{welcomeMessage}</Typography.Paragraph>
              </div>
            </article>
          ) : messages.map((item, index) => (
            <article className={`message ${item.role.toLowerCase()}`} key={`${item.id || 'local'}-${index}`}>
              <div className="message-role">{item.role === 'USER' ? '你' : '河海智答'}</div>
              <div className="message-body">
                {item.role === 'ASSISTANT' && item.answer_origin === 'WEB_SEARCH' && (
                  <Tag color="gold" className="answer-origin-tag">联网搜索回答</Tag>
                )}
                {item.role === 'ASSISTANT' && item.answer_origin === 'HYBRID' && (
                  <Tag color="blue" className="answer-origin-tag">知识库 + 联网搜索</Tag>
                )}
                {item.role === 'ASSISTANT' ? (
                  item.content ? <ReactMarkdown components={{ a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}>{item.content}</ReactMarkdown>
                    : item.status === 'ERROR' ? <Typography.Text type="danger">回答生成失败，请重试。</Typography.Text>
                      : item.status === 'CANCELLED' ? <Typography.Text type="secondary">本次回答已停止。</Typography.Text>
                        : <Space><Spin size="small" /><Typography.Text type="secondary">{index === messages.length - 1 ? streamStatus || '正在处理…' : '正在处理…'}</Typography.Text></Space>
                ) : <Typography.Paragraph>{item.content}</Typography.Paragraph>}
                {item.role === 'ASSISTANT' && item.content && (
                  <>
                    <div className="message-actions">
                      {item.knowledge_task ? taskTag(item.knowledge_task) : null}
                      {item.correction ? correctionTag(item.correction) : null}
                      <Tooltip title="复制此回答">
                        <Button aria-label="复制此回答" type="text" size="small" icon={<CopyOutlined />} onClick={() => void copyAnswer(item.content)} />
                      </Tooltip>
                      <Tooltip title="此答案准确，加入知识库">
                        <Button
                          aria-label="此答案准确，加入知识库"
                          type="text"
                          size="small"
                          icon={<LikeOutlined />}
                          disabled={!canAddToKnowledge(item)}
                          loading={item.id ? knowledgeSubmitting.has(item.id) : false}
                          onClick={() => void addToKnowledge(item)}
                        />
                      </Tooltip>
                      <Tooltip title="此答案不准确，我来提供答案">
                        <Button
                          aria-label="此答案不准确，我来提供答案"
                          type="text"
                          size="small"
                          icon={<DislikeOutlined />}
                          disabled={!canCorrect(item)}
                          onClick={() => startCorrection(item)}
                        />
                      </Tooltip>
                    </div>
                    {correctingMessageId === item.id && (
                      <div className="correction-editor">
                        <Input.TextArea
                          value={correctionDraft}
                          maxLength={6000}
                          showCount
                          autoSize={{ minRows: 3, maxRows: 10 }}
                          placeholder="请输入你认为准确的答案"
                          onChange={(event) => setCorrectionDraft(event.target.value)}
                        />
                        <Space>
                          <Button size="small" onClick={() => { setCorrectingMessageId(null); setCorrectionDraft('') }}>取消</Button>
                          <Button
                            size="small"
                            type="primary"
                            disabled={!correctionDraft.trim()}
                            loading={item.id ? correctionSubmitting.has(item.id) : false}
                            onClick={() => void submitCorrection(item)}
                          >
                            提交
                          </Button>
                        </Space>
                      </div>
                    )}
                  </>
                )}
                {item.content ? <SourceCards sources={item.sources || []} /> : null}
              </div>
            </article>
          ))}
          <div ref={bottomRef} />
        </section>
        <footer className="composer">
          {streamError && <Alert type="error" message={streamError} showIcon closable onClose={() => setStreamError('')} />}
          <Space.Compact block>
            <Input.TextArea
              value={input}
              autoSize={{ minRows: 1, maxRows: 5 }}
              placeholder="输入校园相关问题，Enter 发送，Shift+Enter 换行"
              disabled={sending}
              onChange={(event) => setInput(event.target.value)}
              onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void send() } }}
            />
            {sending ? (
              <Button danger icon={<StopOutlined />} onClick={() => abortRef.current?.abort()}>停止</Button>
            ) : (
              <Button type="primary" icon={<SendOutlined />} onClick={() => void send()}>发送</Button>
            )}
          </Space.Compact>
        </footer>
      </main>
    </div>
  )
}
