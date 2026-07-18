import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import {
  Users,
  RefreshCw,
  Shield,
  ShieldOff,
  ToggleLeft,
  ToggleRight,
  AlertCircle,
  Trash2,
  AlertTriangle,
} from 'lucide-react'

interface User {
  id: number
  name: string
  username: string
  role: 'STUDENT' | 'ADMIN'
  is_active: boolean
  created_at: string
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

export default function UsersPage() {
  const { user: currentUser } = useAuth()

  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)

  useEffect(() => {
    fetchUsers()
  }, [])

  async function fetchUsers() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listUsers()
      setUsers(data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleRole(userId: number, currentRole: string) {
    const newRole = currentRole === 'STUDENT' ? 'ADMIN' : 'STUDENT'
    setError('')
    setSuccessMsg('')
    try {
      const updated = await api.updateUser(userId, { role: newRole })
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: updated.role } : u))
      )
      setSuccessMsg(
        `已将用户 ${updated.name} 的角色变更为 ${newRole === 'ADMIN' ? '管理员' : '学生'}`
      )
    } catch (err: any) {
      setError(err?.response?.data?.detail || '更新角色失败')
    }
  }

  async function handleToggleActive(userId: number, currentActive: boolean) {
    // Prevent self-disable
    if (userId === currentUser?.id && currentActive) {
      setError('不能停用当前管理员账号')
      setTimeout(() => setError(''), 3000)
      return
    }

    setError('')
    setSuccessMsg('')
    try {
      const updated = await api.updateUser(userId, {
        is_active: !currentActive,
      })
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId ? { ...u, is_active: updated.is_active } : u
        )
      )
      setSuccessMsg(
        `已将用户 ${updated.name} 的状态变更为 ${updated.is_active ? '启用' : '停用'}`
      )
    } catch (err: any) {
      setError(err?.response?.data?.detail || '更新状态失败')
    }
  }

  async function handleDelete(userId: number) {
    setDeleteTarget(null)
    try {
      await api.deleteUser(userId)
      setSuccessMsg('用户已删除')
      setTimeout(() => setSuccessMsg(''), 3000)
      await fetchUsers()
    } catch (err: any) {
      setError(err?.response?.data?.detail || '删除用户失败')
    }
  }

  return (
    <div className="users-page">
      <div className="page-header">
        <div>
          <h1>用户管理</h1>
          <p className="page-subtitle">管理系统中的所有用户</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={fetchUsers}
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
      ) : users.length === 0 ? (
        <div className="empty-state">
          <Users size={48} />
          <p>暂无用户数据</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>姓名</th>
                <th>用户名</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isSelf = u.id === currentUser?.id
                return (
                  <tr key={u.id} className={isSelf ? 'row-self' : ''}>
                    <td className="td-name">
                      {u.name}
                      {isSelf && <span className="self-badge">当前账号</span>}
                    </td>
                    <td>{u.username}</td>
                    <td>
                      <span
                        className={`role-badge ${
                          u.role === 'ADMIN' ? 'role-admin' : 'role-student'
                        }`}
                      >
                        {u.role === 'ADMIN' ? (
                          <Shield size={14} />
                        ) : (
                          <ShieldOff size={14} />
                        )}
                        {u.role === 'ADMIN' ? '管理员' : '学生'}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`status-badge ${
                          u.is_active ? 'status-ready' : 'status-error'
                        }`}
                      >
                        {u.is_active ? '启用' : '停用'}
                      </span>
                    </td>
                    <td>{formatDate(u.created_at)}</td>
                    <td className="td-actions">
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => handleToggleRole(u.id, u.role)}
                        title="切换角色"
                      >
                        {u.role === 'ADMIN' ? (
                          <>
                            <ShieldOff size={14} />
                            设为学生
                          </>
                        ) : (
                          <>
                            <Shield size={14} />
                            设为管理员
                          </>
                        )}
                      </button>
                      <button
                        className={`btn btn-sm ${
                          u.is_active ? 'btn-warning' : 'btn-secondary'
                        }`}
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        title={u.is_active ? '停用账号' : '启用账号'}
                        disabled={isSelf && u.is_active}
                      >
                        {u.is_active ? (
                          <>
                            <ToggleRight size={14} />
                            停用
                          </>
                        ) : (
                          <>
                            <ToggleLeft size={14} />
                            启用
                          </>
                        )}
                      </button>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => setDeleteTarget(u.id)}
                        disabled={isSelf}
                        title={isSelf ? '不能删除当前账号' : '删除用户'}
                      >
                        <Trash2 size={14} />
                        删除
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {deleteTarget !== null && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>
              <AlertTriangle size={20} style={{ verticalAlign: 'middle', marginRight: 8 }} />
              确认删除
            </h3>
            <p>确定要删除此用户吗？该用户的所有数据（包括文档和对话记录）将被永久删除，且无法恢复。</p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setDeleteTarget(null)}>取消</button>
              <button className="btn btn-danger" onClick={() => handleDelete(deleteTarget)}>确认删除</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
