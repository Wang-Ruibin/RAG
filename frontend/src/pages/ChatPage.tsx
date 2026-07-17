import { BookOutlined, DeleteOutlined, PlusOutlined, SendOutlined, StopOutlined } from '@ant-design/icons'
import { Alert, Button, Empty, Input, List, Popconfirm, Space, Spin, Tag, Typography, message } from 'antd'
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../lib/api'
import { streamChat, type SSEEvent } from '../lib/sse'
import type { AnswerKnowledgeTask, ChatMessage, Conversation, SourceRef } from '../types'
import { SourceCards } from '../components/SourceCards'

export function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [streamError, setStreamError] = useState('')
  const [streamStatus, setStreamStatus] = useState('')
  const [knowledgeSubmitting, setKnowledgeSubmitting] = useState<Set<number>>(new Set())
  const abortRef = useRef<AbortController | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const deletingConversationIds = useRef(new Set<number>())
  const pollingTaskIds = useRef(new Set<number>())

  const loadConversations = () => api<Conversation[]>('/api/conversations').then(setConversations)
  useEffect(() => { void loadConversations() }, [])
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
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 && Number.isFinite(messageId) ? { ...item, id: messageId } : item,
      ))
    } else if (event.event === 'status') {
      setStreamStatus(String(event.data.message || '正在处理…'))
    } else if (event.event === 'sources') {
      const sources = (event.data.items || []) as SourceRef[]
      const answer_origin = event.data.answer_origin as ChatMessage['answer_origin']
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 ? { ...item, sources, answer_origin: answer_origin ?? item.answer_origin } : item,
      ))
    } else if (event.event === 'delta') {
      const text = String(event.data.text || '')
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 ? { ...item, content: item.content + text } : item,
      ))
    } else if (event.event === 'done') {
      setStreamStatus('')
      const answer_origin = event.data.answer_origin as ChatMessage['answer_origin']
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 ? { ...item, status: 'COMPLETE', answer_origin: answer_origin ?? item.answer_origin } : item,
      ))
    } else if (event.event === 'error') {
      setStreamStatus('')
      setStreamError(String(event.data.message || '回答生成失败'))
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 ? { ...item, status: 'ERROR' } : item,
      ))
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
      setMessages((current) => current.map((item, index) =>
        index === current.length - 1 ? { ...item, status } : item,
      ))
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
      if (activeId === id) { setActiveId(null); setMessages([]) }
      await loadConversations()
      void message.success('会话已删除')
    } finally {
      deletingConversationIds.current.delete(id)
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

  function taskTag(task: AnswerKnowledgeTask) {
    const mapping: Record<AnswerKnowledgeTask['status'], { text: string; color: string }> = {
      QUEUED: { text: '知识库排队中', color: 'gold' },
      PROCESSING: { text: '知识库处理中', color: 'blue' },
      COMPLETE: { text: '已加入知识库', color: 'green' },
      FAILED: { text: '加入知识库失败', color: 'red' },
    }
    return <Tag color={mapping[task.status].color}>{mapping[task.status].text}</Tag>
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
  }

  return (
    <div className="chat-layout">
      <aside className="conversation-panel">
        <Button type="primary" icon={<PlusOutlined />} block onClick={() => { setActiveId(null); setMessages([]) }}>
          新对话
        </Button>
        <List
          dataSource={conversations}
          locale={{ emptyText: '还没有历史会话' }}
          renderItem={(item) => (
            <List.Item
              className={activeId === item.id ? 'conversation active' : 'conversation'}
              onClick={() => {
                if (!deletingConversationIds.current.has(item.id)) void openConversation(item.id)
              }}
              actions={[
                <Popconfirm
                  key="delete"
                  title="删除这个会话？"
                  onConfirm={(event) => {
                    event?.stopPropagation()
                    return removeConversation(item.id)
                  }}
                  onCancel={(event) => event?.stopPropagation()}
                >
                  <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={(event) => event.stopPropagation()} />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta title={item.title} description={`${item.message_count} 条消息`} />
            </List.Item>
          )}
        />
      </aside>
      <main className="chat-main">
        <header className="page-header">
          <div><Typography.Title level={3}>校园知识问答</Typography.Title><Typography.Text type="secondary">答案来自校园知识库，请通过引用原文核实重要信息</Typography.Text></div>
        </header>
        <section className="message-list">
          {loadingHistory ? <Spin /> : messages.length === 0 ? (
            <Empty description="试试问：河海大学的校训是什么？" />
          ) : messages.map((item, index) => (
            <article className={`message ${item.role.toLowerCase()}`} key={`${item.id || 'local'}-${index}`}>
              <div className="message-role">{item.role === 'USER' ? '你' : '河海智答'}</div>
              <div className="message-body">
                {item.role === 'ASSISTANT' && item.answer_origin === 'WEB_SEARCH' && (
                  <Tag color="gold" className="answer-origin-tag">联网搜索回答</Tag>
                )}
                {item.role === 'ASSISTANT' ? (
                  item.content ? <ReactMarkdown components={{ a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}>{item.content}</ReactMarkdown>
                    : item.status === 'ERROR' ? <Typography.Text type="danger">回答生成失败，请重试。</Typography.Text>
                      : item.status === 'CANCELLED' ? <Typography.Text type="secondary">本次回答已停止。</Typography.Text>
                        : <Space><Spin size="small" /><Typography.Text type="secondary">{index === messages.length - 1 ? streamStatus || '正在处理…' : '正在处理…'}</Typography.Text></Space>
                ) : <Typography.Paragraph>{item.content}</Typography.Paragraph>}
                {item.role === 'ASSISTANT' && item.content && (
                  <div className="message-actions">
                    {item.knowledge_task ? taskTag(item.knowledge_task) : canAddToKnowledge(item) ? (
                      <Button
                        size="small"
                        icon={<BookOutlined />}
                        loading={item.id ? knowledgeSubmitting.has(item.id) : false}
                        onClick={() => void addToKnowledge(item)}
                      >
                        加入知识库
                      </Button>
                    ) : null}
                  </div>
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
