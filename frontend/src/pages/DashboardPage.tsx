import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import { FileText, Database, MessageSquare, RefreshCw, AlertCircle } from 'lucide-react'

interface Stats {
  documents: number
  chunks: number
  conversations: number
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  async function fetchStats() {
    setLoading(true)
    setError('')
    try {
      const data = await api.getStats()
      setStats(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '获取统计数据失败')
    } finally {
      setLoading(false)
    }
  }

  const cards = [
    {
      icon: FileText,
      count: stats?.documents ?? 0,
      label: '知识库文档',
      iconClass: 'icon-blue',
    },
    {
      icon: Database,
      count: stats?.chunks ?? 0,
      label: '知识片段',
      iconClass: 'icon-purple',
    },
    {
      icon: MessageSquare,
      count: stats?.conversations ?? 0,
      label: '问答对话',
      iconClass: 'icon-green',
    },
  ]

  return (
    <div className="dashboard-page">
      <div className="page-header">
        <div>
          <h1>欢迎回来{user?.name ? `，${user.name}` : ''}</h1>
          <p className="page-subtitle">河海大学校园问答助手 数据概览</p>
        </div>
        <button className="btn btn-secondary" onClick={fetchStats} disabled={loading}>
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
      ) : (
        <div className="stats-grid">
          {cards.map((card) => (
            <div key={card.label} className="stat-card">
              <div className={`stat-icon ${card.iconClass}`}>
                <card.icon size={24} />
              </div>
              <div className="stat-count">{card.count}</div>
              <div className="stat-label">{card.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
