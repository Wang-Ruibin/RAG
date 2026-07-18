import { useState, useEffect } from 'react'
import { api } from '../services/api'
import {
  Database,
  Trash2,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
} from 'lucide-react'

interface CacheEntry {
  id: number
  question: string
  answer: string
  sources: any[]
  hit_count: number
  created_at: string
  updated_at: string
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

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen) + '...'
}

export default function CachePage() {
  const [entries, setEntries] = useState<CacheEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Confirm dialogs
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [showFlushConfirm, setShowFlushConfirm] = useState(false)

  useEffect(() => {
    fetchCache()
  }, [])

  async function fetchCache() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listCache()
      // Sort by hit_count descending so most-frequent appear first
      const sorted = [...(data as CacheEntry[])].sort(
        (a, b) => b.hit_count - a.hit_count
      )
      setEntries(sorted)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '获取缓存列表失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleteTarget(null)
    try {
      await api.deleteCacheEntry(id)
      setSuccessMsg('缓存已删除')
      setTimeout(() => setSuccessMsg(''), 3000)
      await fetchCache()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '删除缓存失败')
    }
  }

  async function handleFlush() {
    setShowFlushConfirm(false)
    try {
      const result = await api.flushCache()
      const count = result?.count ?? 0
      setSuccessMsg(`已清空 ${count} 条缓存`)
      setTimeout(() => setSuccessMsg(''), 3000)
      await fetchCache()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '清空缓存失败')
    }
  }

  return (
    <div className="cache-page">
      <div className="page-header">
        <div>
          <h1>缓存管理</h1>
          <p className="page-subtitle">管理问答系统的缓存数据</p>
        </div>
        <div className="page-header-actions">
          <button
            className="btn btn-secondary"
            onClick={fetchCache}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
          <button
            className="btn btn-danger"
            onClick={() => setShowFlushConfirm(true)}
            disabled={entries.length === 0}
          >
            <Trash2 size={16} />
            清空全部
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="alert alert-success">
          <AlertCircle size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>加载中...</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <Database size={48} />
          <h3>暂无缓存数据</h3>
          <p>尚未缓存任何问答数据</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>问题</th>
                <th>回答</th>
                <th>命中次数</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="td-title">{truncate(entry.question, 60)}</td>
                  <td>{truncate(entry.answer, 80)}</td>
                  <td>
                    <span className="badge badge-info">
                      {entry.hit_count}
                    </span>
                  </td>
                  <td>{formatDate(entry.created_at)}</td>
                  <td className="td-actions">
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => setDeleteTarget(entry.id)}
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

      {/* Confirm Delete Single Entry Dialog */}
      {deleteTarget !== null && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>
              <AlertTriangle size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />
              确认删除
            </h3>
            <p>确定要删除此缓存条目吗？删除后无法恢复。</p>
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

      {/* Confirm Flush All Dialog */}
      {showFlushConfirm && (
        <div className="modal-overlay" onClick={() => setShowFlushConfirm(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>
              <AlertTriangle size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />
              确认清空
            </h3>
            <p>确定要清空所有缓存吗？此操作将删除全部 {entries.length} 条缓存数据，且无法恢复。</p>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowFlushConfirm(false)}
              >
                取消
              </button>
              <button
                className="btn btn-danger"
                onClick={handleFlush}
              >
                确认清空
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
