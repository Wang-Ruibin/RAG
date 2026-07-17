import { CheckOutlined, CloseOutlined, EyeOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { SourceCards } from '../components/SourceCards'
import { api } from '../lib/api'
import type { AdminAnswerCorrection, CampusDocument } from '../types'

type CorrectionStatus = AdminAnswerCorrection['status']

const statusMeta: Record<CorrectionStatus, { label: string; color: string }> = {
  PENDING: { label: '待审核', color: 'gold' },
  PROCESSING: { label: '入库中', color: 'processing' },
  APPROVED: { label: '已采纳', color: 'green' },
  REJECTED: { label: '已拒绝', color: 'red' },
  FAILED: { label: '入库失败', color: 'volcano' },
}

export function CorrectionReviewPage() {
  const [items, setItems] = useState<AdminAnswerCorrection[]>([])
  const [documents, setDocuments] = useState<CampusDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<CorrectionStatus | undefined>('PENDING')
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<AdminAnswerCorrection | null>(null)
  const [rejecting, setRejecting] = useState<AdminAnswerCorrection | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm<{ question: string; answer: string; source_document_ids: number[] }>()

  const path = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), size: String(pageSize) })
    if (statusFilter) params.set('status_filter', statusFilter)
    return `/api/admin/answer-corrections?${params}`
  }, [page, pageSize, statusFilter])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api<{ items: AdminAnswerCorrection[]; total: number }>(path)
      setItems(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    let cancelled = false
    api<{ items: AdminAnswerCorrection[]; total: number }>(path)
      .then((result) => {
        if (!cancelled) {
          setItems(result.items)
          setTotal(result.total)
        }
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [path])

  useEffect(() => {
    api<{ items: CampusDocument[] }>('/api/documents?page=1&size=100')
      .then((result) => setDocuments(result.items.filter((document) => document.status === 'READY')))
      .catch(() => setDocuments([]))
  }, [])

  const processing = items.some((item) => item.status === 'PROCESSING')
  useEffect(() => {
    if (!processing) return
    const timer = window.setInterval(() => void load(), 2500)
    return () => window.clearInterval(timer)
  }, [load, processing])

  function openReview(item: AdminAnswerCorrection) {
    setSelected(item)
    form.setFieldsValue({
      question: item.reviewed_question || item.original_question,
      answer: item.reviewed_answer || item.proposed_answer,
      source_document_ids: item.source_document_ids || [],
    })
  }

  async function approve(values: { question: string; answer: string; source_document_ids: number[] }) {
    if (!selected) return
    setSubmitting(true)
    try {
      await api(`/api/admin/answer-corrections/${selected.id}/approve`, {
        method: 'POST',
        body: JSON.stringify(values),
      })
      void message.success('已批准，正在生成并索引知识文档')
      setSelected(null)
      await load()
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '批准失败')
    } finally {
      setSubmitting(false)
    }
  }

  async function reject() {
    if (!rejecting || rejectReason.trim().length < 2) return
    setSubmitting(true)
    try {
      await api(`/api/admin/answer-corrections/${rejecting.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason: rejectReason.trim() }),
      })
      void message.success('已拒绝该纠错')
      setRejecting(null)
      setRejectReason('')
      if (selected?.id === rejecting.id) setSelected(null)
      await load()
    } catch (reason) {
      void message.error(reason instanceof Error ? reason.message : '拒绝失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <Typography.Title level={3}>纠错审核</Typography.Title>
          <Typography.Text type="secondary">审核用户提交的正确答案，批准后将作为普通知识文档入库</Typography.Text>
        </div>
        <Select
          allowClear
          placeholder="全部状态"
          value={statusFilter}
          style={{ width: 150 }}
          options={Object.entries(statusMeta).map(([value, meta]) => ({ value, label: meta.label }))}
          onChange={(value) => { setPage(1); setStatusFilter(value) }}
        />
      </header>
      <Card>
        <Table
          rowKey="id"
          loading={loading}
          dataSource={items}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (nextPage, nextSize) => {
              setPage(nextSize === pageSize ? nextPage : 1)
              setPageSize(nextSize)
            },
          }}
          columns={[
            { title: '问题', dataIndex: 'original_question', ellipsis: true },
            { title: '提交者', width: 210, render: (_, row) => <div><strong>{row.contributor_name}</strong><br /><Typography.Text type="secondary">{row.contributor_email}</Typography.Text></div> },
            { title: '状态', dataIndex: 'status', width: 110, render: (value: CorrectionStatus) => <Tag color={statusMeta[value].color}>{statusMeta[value].label}</Tag> },
            { title: '提交时间', dataIndex: 'created_at', width: 180, render: (value: string) => new Date(value).toLocaleString('zh-CN') },
            { title: '操作', width: 145, render: (_, row) => <Space>
              <Button aria-label="查看" type="text" icon={<EyeOutlined />} onClick={() => openReview(row)} />
              {['PENDING', 'FAILED'].includes(row.status) && <>
                <Button aria-label="批准" type="text" icon={<CheckOutlined />} onClick={() => openReview(row)} />
                <Button aria-label="拒绝" type="text" danger icon={<CloseOutlined />} onClick={() => { setRejecting(row); setRejectReason('') }} />
              </>}
            </Space> },
          ]}
        />
      </Card>

      <Drawer
        title="纠错详情与审核"
        width={760}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        extra={selected && ['PENDING', 'FAILED'].includes(selected.status)
          ? <Space>
              <Button danger onClick={() => { setRejecting(selected); setRejectReason('') }}>拒绝</Button>
              <Button type="primary" loading={submitting} onClick={() => form.submit()}>批准并入库</Button>
            </Space>
          : null}
      >
        {selected && <>
          <Descriptions column={1} bordered size="small" items={[
            { key: 'status', label: '状态', children: <Tag color={statusMeta[selected.status].color}>{statusMeta[selected.status].label}</Tag> },
            { key: 'user', label: '提交者', children: `${selected.contributor_name} <${selected.contributor_email}>` },
            { key: 'question', label: '原问题', children: selected.original_question },
            { key: 'answer', label: '原回答', children: <div className="review-text">{selected.original_answer}</div> },
            { key: 'proposed', label: '用户答案', children: <div className="review-text">{selected.proposed_answer}</div> },
            ...(selected.review_note ? [{ key: 'note', label: '拒绝原因', children: selected.review_note }] : []),
            ...(selected.error ? [{ key: 'error', label: '入库错误', children: <Typography.Text type="danger">{selected.error}</Typography.Text> }] : []),
          ]} />
          {selected.original_sources.length > 0 && <SourceCards sources={selected.original_sources} />}
          {['PENDING', 'FAILED'].includes(selected.status) && <Form
            form={form}
            layout="vertical"
            className="correction-review-form"
            onFinish={(values) => void approve(values)}
          >
            <Form.Item name="question" label="审核后问题" rules={[{ required: true, min: 2 }]}>
              <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} maxLength={1000} />
            </Form.Item>
            <Form.Item name="answer" label="审核后答案" rules={[{ required: true, min: 2 }]}>
              <Input.TextArea autoSize={{ minRows: 7, maxRows: 18 }} maxLength={6000} showCount />
            </Form.Item>
            <Form.Item name="source_document_ids" label="关联已有文档（可选，仅用于审核追溯）">
              <Select
                mode="multiple"
                showSearch
                optionFilterProp="label"
                maxCount={20}
                options={documents.map((document) => ({ value: document.id, label: document.title }))}
              />
            </Form.Item>
          </Form>}
        </>}
      </Drawer>

      <Modal
        title="拒绝纠错"
        open={Boolean(rejecting)}
        confirmLoading={submitting}
        okButtonProps={{ danger: true, disabled: rejectReason.trim().length < 2 }}
        okText="确认拒绝"
        cancelText="取消"
        onCancel={() => setRejecting(null)}
        onOk={() => void reject()}
      >
        <Typography.Paragraph type="secondary">拒绝原因将向提交者展示，用户修改后可重新提交。</Typography.Paragraph>
        <Input.TextArea value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} maxLength={1000} showCount autoSize={{ minRows: 4, maxRows: 8 }} />
      </Modal>
    </div>
  )
}
