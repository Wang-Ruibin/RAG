import { DeleteOutlined, EditOutlined, EyeOutlined, InboxOutlined, ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Descriptions, Drawer, Form, Input, Modal, Popconfirm, Progress, Space, Spin, Table, Tag, Tooltip, Typography, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api, apiBlob } from '../lib/api'
import type { CampusDocument, DocumentPreview } from '../types'

const statusLabel: Record<CampusDocument['status'], { text: string; color: string }> = {
  QUEUED: { text: '排队中', color: 'gold' },
  PROCESSING: { text: '处理中', color: 'blue' },
  READY: { text: '已完成', color: 'green' },
  FAILED: { text: '失败', color: 'red' },
  DELETING: { text: '删除中', color: 'default' },
}

const stagePercent: Record<string, number> = {
  SAVED: 10, EXTRACTING: 25, CLEANING: 40, CHUNKING: 55, EMBEDDING: 75, INDEXING: 90, COMPLETE: 100,
}

export function DocumentsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const [documents, setDocuments] = useState<CampusDocument[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [editing, setEditing] = useState<CampusDocument | null>(null)
  const [viewing, setViewing] = useState<CampusDocument | null>(null)
  const [preview, setPreview] = useState<DocumentPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editForm] = Form.useForm<{
    title: string
    category: string
    source_url?: string
    published_at?: string
  }>()

  const listPath = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      size: String(pageSize),
      q: query,
    })
    return `/api/documents?${params}`
  }, [page, pageSize, query])
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api<{ items: CampusDocument[]; total: number }>(listPath)
      setDocuments(result.items)
      setTotal(result.total)
    } finally { setLoading(false) }
  }, [listPath])
  useEffect(() => {
    let cancelled = false
    api<{ items: CampusDocument[]; total: number }>(listPath)
      .then((result) => {
        if (!cancelled) {
          setDocuments(result.items)
          setTotal(result.total)
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [listPath])
  const processing = useMemo(() => documents.some((doc) => ['QUEUED', 'PROCESSING'].includes(doc.status)), [documents])
  useEffect(() => {
    if (!processing) return
    const timer = window.setInterval(() => void load(), 2500)
    return () => window.clearInterval(timer)
  }, [load, processing])

  const uploadProps: UploadProps = {
    accept: '.md,.txt,.pdf,.docx',
    multiple: false,
    showUploadList: false,
    customRequest: async ({ file, onSuccess, onError }) => {
      const source = file as File
      if (source.size > 50 * 1024 * 1024) {
        const error = new Error('文件不能超过 50MB')
        onError?.(error); void message.error(error.message); return
      }
      const form = new FormData()
      form.append('file', source)
      form.append('title', source.name.replace(/\.[^.]+$/, ''))
      form.append('category', '其他')
      try {
        await api('/api/documents', { method: 'POST', body: form })
        onSuccess?.({}); void message.success('上传成功，正在后台处理'); await load()
      } catch (reason) {
        const error = reason instanceof Error ? reason : new Error('上传失败')
        onError?.(error); void message.error(error.message)
      }
    },
  }

  async function reindex(id: number) {
    await api(`/api/documents/${id}/reindex`, { method: 'POST' })
    void message.success('已进入重新处理队列'); await load()
  }
  async function remove(id: number) {
    await api(`/api/documents/${id}`, { method: 'DELETE' })
    void message.success('文档已完整删除'); await load()
  }
  async function showDetail(id: number) {
    setPreviewLoading(true)
    try {
      const [detail, firstPage] = await Promise.all([
        api<CampusDocument>(`/api/documents/${id}`),
        api<DocumentPreview>(`/api/documents/${id}/preview?offset=0&limit=20000`),
      ])
      setViewing(detail)
      setPreview(firstPage)
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '预览失败')
    } finally {
      setPreviewLoading(false)
    }
  }
  async function loadMorePreview() {
    if (!viewing || !preview?.has_more || previewLoading) return
    setPreviewLoading(true)
    try {
      const next = await api<DocumentPreview>(
        `/api/documents/${viewing.id}/preview?offset=${preview.offset + preview.content.length}&limit=20000`,
      )
      setPreview({ ...next, offset: 0, content: preview.content + next.content })
    } finally { setPreviewLoading(false) }
  }
  async function downloadOriginal() {
    if (!viewing) return
    try {
      const blob = await apiBlob(`/api/documents/${viewing.id}/download`)
      const href = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = href
      anchor.download = viewing.original_name
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(href)
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '下载失败')
    }
  }
  function startEdit(document: CampusDocument) {
    setEditing(document)
    editForm.setFieldsValue({
      title: document.title,
      category: document.category,
      source_url: document.source_url || '',
      published_at: document.published_at || '',
    })
  }
  async function saveEdit(values: {
    title: string
    category: string
    source_url?: string
    published_at?: string
  }) {
    if (!editing) return
    setSaving(true)
    try {
      await api(`/api/documents/${editing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          ...values,
          source_url: values.source_url || null,
          published_at: values.published_at || null,
        }),
      })
      void message.success('知识库资料已更新')
      setEditing(null)
      await load()
    } finally { setSaving(false) }
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <div><Typography.Title level={3}>知识库</Typography.Title><Typography.Text type="secondary">共 {total} 篇文档，{isAdmin ? '可上传并维护知识资料' : '当前为只读浏览'}</Typography.Text></div>
        <Input.Search
          placeholder="搜索标题"
          allowClear
          onSearch={(value) => { setLoading(true); setPage(1); setQuery(value) }}
          style={{ width: 260 }}
        />
      </header>
      {isAdmin && <Upload.Dragger {...uploadProps} className="upload-card">
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">点击或拖拽校园资料到这里</p>
        <p className="ant-upload-hint">支持 Markdown、TXT、PDF、DOCX，单文件不超过 50MB</p>
      </Upload.Dragger>}
      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={documents}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            showTotal: (count) => `共 ${count} 篇文档`,
            onChange: (nextPage, nextPageSize) => {
              if (nextPageSize !== pageSize) {
                setLoading(true)
                setPage(1)
                setPageSize(nextPageSize)
              } else {
                setLoading(true)
                setPage(nextPage)
              }
            },
          }}
          scroll={{ x: 900 }}
          columns={[
            { title: '文档', dataIndex: 'title', width: 260, render: (value, row) => <div><strong>{value}</strong><br /><Typography.Text type="secondary">{row.original_name}</Typography.Text></div> },
            { title: '分类', dataIndex: 'category', width: 100 },
            { title: '状态', dataIndex: 'status', width: 180, render: (value: CampusDocument['status'], row) => <div><Tag color={statusLabel[value].color}>{statusLabel[value].text}</Tag>{['QUEUED', 'PROCESSING'].includes(value) && <Progress percent={stagePercent[row.stage] || 5} size="small" />}{row.error && <Alert type="error" message={row.error} showIcon />}</div> },
            { title: '切块', dataIndex: 'chunk_count', width: 80 },
            { title: '大小', dataIndex: 'size', width: 100, render: (value: number) => `${(value / 1024).toFixed(1)} KB` },
            { title: '操作', fixed: 'right', width: isAdmin ? 180 : 80, render: (_, row) => <Space>
              <Tooltip title="预览"><Button aria-label="预览" type="text" icon={<EyeOutlined />} onClick={() => void showDetail(row.id)} /></Tooltip>
              {isAdmin && <Tooltip title="编辑"><Button aria-label="编辑" type="text" icon={<EditOutlined />} disabled={['QUEUED', 'PROCESSING'].includes(row.status)} onClick={() => startEdit(row)} /></Tooltip>}
              {isAdmin && <Tooltip title="重建"><Button aria-label="重建" type="text" icon={<ReloadOutlined />} disabled={['QUEUED', 'PROCESSING'].includes(row.status)} onClick={() => void reindex(row.id)} /></Tooltip>}
              {isAdmin && <Popconfirm title="同时删除原文件和知识库中的文本块、向量？" onConfirm={() => void remove(row.id)}><Tooltip title="删除"><Button aria-label="删除" type="text" danger icon={<DeleteOutlined />} /></Tooltip></Popconfirm>}
            </Space> },
          ]}
        />
      </Card>
      <Modal
        title="编辑知识库资料"
        open={Boolean(editing)}
        confirmLoading={saving}
        onCancel={() => setEditing(null)}
        onOk={() => editForm.submit()}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical" onFinish={(values) => void saveEdit(values)}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}><Input maxLength={300} /></Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true, message: '请输入分类' }]}><Input maxLength={100} /></Form.Item>
          <Form.Item name="source_url" label="来源链接" rules={[{ type: 'url', message: '请输入合法的 http(s) 链接' }]}><Input placeholder="https://..." /></Form.Item>
          <Form.Item name="published_at" label="发布日期"><Input type="date" /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="知识库资料预览" width={720} open={Boolean(viewing)} onClose={() => { setViewing(null); setPreview(null) }}>
        {viewing && <Descriptions column={1} bordered size="small" items={[
          { key: 'title', label: '标题', children: viewing.title },
          { key: 'filename', label: '原始文件', children: viewing.original_name },
          { key: 'category', label: '分类', children: viewing.category },
          { key: 'kind', label: '知识类型', children: viewing.document_kind === 'USER_CORRECTION' ? '用户纠错（已审核）' : viewing.document_kind === 'WEB_ARCHIVE' ? '网页归档' : '知识文档' },
          ...(viewing.contributor_name ? [{ key: 'contributor', label: '提供者', children: `${viewing.contributor_name}（管理员已审核）` }] : []),
          { key: 'status', label: '状态', children: <Tag color={statusLabel[viewing.status].color}>{statusLabel[viewing.status].text}</Tag> },
          { key: 'stage', label: '处理阶段', children: viewing.stage },
          { key: 'chunks', label: '知识块', children: viewing.chunk_count },
          { key: 'published', label: '发布日期', children: viewing.published_at || '未知' },
          { key: 'source', label: '来源', children: viewing.source_url ? <a href={viewing.source_url} target="_blank" rel="noopener noreferrer">打开官网原文</a> : '无' },
          { key: 'created', label: '上传时间', children: new Date(viewing.created_at).toLocaleString() },
          { key: 'updated', label: '更新时间', children: new Date(viewing.updated_at).toLocaleString() },
          { key: 'error', label: '错误信息', children: viewing.error || '无' },
        ]} />}
        {viewing && <Space className="preview-actions">
          <Button onClick={() => void downloadOriginal()}>下载原文件</Button>
          {preview && <Typography.Text type="secondary">{preview.format} · 共 {preview.total_chars} 字符</Typography.Text>}
        </Space>}
        {previewLoading && !preview ? <Spin /> : preview && <>
          <pre className="document-preview">{preview.content}</pre>
          {preview.has_more && <Button block loading={previewLoading} onClick={() => void loadMorePreview()}>加载更多</Button>}
        </>}
      </Drawer>
    </div>
  )
}
