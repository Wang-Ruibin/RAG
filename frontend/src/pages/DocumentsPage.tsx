import { useState, useEffect, FormEvent, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import {
  FileText,
  Upload,
  RefreshCw,
  Trash2,
  RotateCw,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react'

interface Document {
  id: number
  title: string
  filename: string
  size: number
  status: 'PROCESSING' | 'READY' | 'ERROR'
  chunk_count: number
  error?: string | null
  uploader_name?: string | null
  created_at: string
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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

export default function DocumentsPage() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()

  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Upload form
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  // Confirm dialog
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  async function fetchDocuments() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listDocuments()
      setDocuments(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '获取文档列表失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault()
    if (!title.trim() || !file) return

    setUploading(true)
    setUploadError('')

    try {
      await api.uploadDocument(title.trim(), file)
      setTitle('')
      setFile(null)
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      await fetchDocuments()
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleteTarget(null)
    try {
      await api.deleteDocument(id)
      await fetchDocuments()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '删除失败')
    }
  }

  async function handleReprocess(id: number) {
    try {
      setDocuments((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: 'PROCESSING' } : d))
      )
      await api.reprocessDocument(id)
      await fetchDocuments()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '重新处理失败')
      await fetchDocuments()
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] || null
    setFile(selected)
  }

  function getStatusBadge(status: string) {
    switch (status) {
      case 'PROCESSING':
        return (
          <span className="status-badge status-processing">
            <Clock size={14} />
            处理中
          </span>
        )
      case 'READY':
        return (
          <span className="status-badge status-ready">
            <CheckCircle size={14} />
            就绪
          </span>
        )
      case 'ERROR':
        return (
          <span className="status-badge status-error">
            <XCircle size={14} />
            错误
          </span>
        )
      default:
        return <span className="status-badge">{status}</span>
    }
  }

  return (
    <div className="documents-page">
      <div className="page-header">
        <div>
          <h1>知识库管理</h1>
          <p className="page-subtitle">管理知识库中的文档</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchDocuments}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {/* Upload Form */}
      <div className="upload-card">
        <h2>
          <Upload size={20} />
          上传文档
        </h2>
        <form className="upload-form" onSubmit={handleUpload}>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="doc-title">文档标题</label>
              <input
                id="doc-title"
                type="text"
                placeholder="请输入文档标题"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                minLength={2}
                maxLength={120}
              />
            </div>
            <div className="form-group">
              <label htmlFor="file-input">选择文件</label>
              <input
                id="file-input"
                type="file"
                accept=".txt,.md,.pdf,.docx"
                onChange={handleFileChange}
                required
              />
            </div>
          </div>

          {uploadError && (
            <div className="alert alert-error">
              <AlertCircle size={16} />
              <span>{uploadError}</span>
            </div>
          )}

          <button
            className="btn btn-primary"
            type="submit"
            disabled={uploading || !title.trim() || !file}
          >
            {uploading ? (
              <>
                <RefreshCw size={16} className="spin" />
                上传中...
              </>
            ) : (
              <>
                <Upload size={16} />
                上传
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error Display */}
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Document Table */}
      {loading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>加载中...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} />
          <p>暂无文档，请上传知识库文档</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>标题</th>
                <th>文件名</th>
                <th>大小</th>
                <th>状态</th>
                <th>片段数</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td className="td-title">{doc.title}</td>
                  <td className="td-filename">{doc.filename}</td>
                  <td>{formatFileSize(doc.size)}</td>
                  <td>{getStatusBadge(doc.status)}</td>
                  <td>{doc.chunk_count}</td>
                  <td>{formatDate(doc.created_at)}</td>
                  <td className="td-actions">
                    {(doc.status === 'READY' || doc.status === 'ERROR') && (
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => handleReprocess(doc.id)}
                        title="重新处理"
                      >
                        <RotateCw size={14} />
                        重新处理
                      </button>
                    )}
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => setDeleteTarget(doc.id)}
                      title="删除"
                    >
                      <Trash2 size={14} />
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirm Delete Dialog */}
      {deleteTarget !== null && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>确认删除</h3>
            <p>确定要删除此文档吗？删除后无法恢复。</p>
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
