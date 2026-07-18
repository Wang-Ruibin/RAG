import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import {
  Shield,
  Plus,
  RefreshCw,
  X,
  Edit3,
  Trash2,
  AlertCircle,
  Users,
  User,
  Clock,
} from 'lucide-react'

interface Role {
  name: string
  description: string
  is_system: boolean
  user_count: number
  created_at: string
}

interface RoleDetail extends Role {
  users: Array<{
    id: number
    name: string
    username: string
    is_active: boolean
    created_at: string
  }>
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

export default function RolesPage() {
  const { name: routeName } = useParams()
  const navigate = useNavigate()

  const [roles, setRoles] = useState<Role[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  // Detail modal
  const [detailRole, setDetailRole] = useState<RoleDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [editingDesc, setEditingDesc] = useState(false)
  const [editDescValue, setEditDescValue] = useState('')
  const [savingDesc, setSavingDesc] = useState(false)

  // Create modal
  const [showCreate, setShowCreate] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createDesc, setCreateDesc] = useState('')
  const [creating, setCreating] = useState(false)

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchRoles()
  }, [])

  // If URL has a role name, open detail automatically
  useEffect(() => {
    if (routeName && roles.length > 0) {
      openDetail(routeName)
    }
  }, [routeName, roles])

  async function fetchRoles() {
    setLoading(true)
    setError('')
    try {
      const data = await api.listRoles()
      setRoles(data)
    } catch (err: any) {
      setError(err?.message || '获取角色列表失败')
    } finally {
      setLoading(false)
    }
  }

  async function openDetail(name: string) {
    setDetailLoading(true)
    setError('')
    setEditingDesc(false)
    try {
      const data = await api.getRole(name)
      setDetailRole(data)
      setEditDescValue(data.description || '')
    } catch (err: any) {
      setError(err?.message || '获取角色详情失败')
    } finally {
      setDetailLoading(false)
    }
  }

  function closeDetail() {
    setDetailRole(null)
    setEditingDesc(false)
    // Clear route param if we navigated via URL
    if (routeName) navigate('/roles', { replace: true })
  }

  async function handleSaveDescription() {
    if (!detailRole) return
    setSavingDesc(true)
    setError('')
    try {
      const updated = await api.updateRole(detailRole.name, editDescValue)
      setDetailRole({ ...detailRole, description: updated.description })
      setEditingDesc(false)
      setSuccessMsg('描述已更新')
      // Update list too
      setRoles((prev) =>
        prev.map((r) =>
          r.name === detailRole.name ? { ...r, description: updated.description } : r
        )
      )
    } catch (err: any) {
      setError(err?.message || '更新描述失败')
    } finally {
      setSavingDesc(false)
    }
  }

  async function handleCreateRole() {
    if (!createName.trim()) return
    setCreating(true)
    setError('')
    try {
      await api.createRole(createName.trim().toUpperCase(), createDesc.trim())
      setShowCreate(false)
      setCreateName('')
      setCreateDesc('')
      setSuccessMsg(`角色 ${createName.trim().toUpperCase()} 创建成功`)
      await fetchRoles()
    } catch (err: any) {
      setError(err?.message || '创建角色失败')
    } finally {
      setCreating(false)
    }
  }

  async function handleDeleteRole(name: string) {
    setDeleting(true)
    setError('')
    try {
      await api.deleteRole(name)
      setDeleteTarget(null)
      setDetailRole(null)
      setSuccessMsg(`角色 ${name} 已删除，相关用户已转为 STUDENT`)
      await fetchRoles()
    } catch (err: any) {
      setError(err?.message || '删除角色失败')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="roles-page">
      <div className="page-header">
        <div>
          <h1>角色管理</h1>
          <p className="page-subtitle">管理系统中的所有角色</p>
        </div>
        <div className="page-header-actions">
          <button
            className="btn btn-secondary"
            onClick={fetchRoles}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <Plus size={16} />
            新建角色
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
      ) : roles.length === 0 ? (
        <div className="empty-state">
          <Shield size={48} />
          <p>暂无角色数据</p>
        </div>
      ) : (
        <div className="roles-grid">
          {roles.map((role) => (
            <div
              key={role.name}
              className="role-card"
              onClick={() => openDetail(role.name)}
            >
              <div className="role-card-header">
                <span className="role-card-name">{role.name}</span>
                {role.is_system && <span className="badge badge-info">系统内置</span>}
              </div>
              <p className="role-card-desc">
                {role.description || <span className="text-muted">暂无描述</span>}
              </p>
              <div className="role-card-footer">
                <span className="role-card-count">
                  <Users size={14} />
                  {role.user_count} 个用户
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ===== Detail Modal ===== */}
      {detailRole && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal-dialog modal-dialog-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-header-info">
                <h3>{detailRole.name}</h3>
                {detailRole.is_system && <span className="badge badge-info">系统内置</span>}
              </div>
              <button className="btn btn-ghost btn-icon" onClick={closeDetail}>
                <X size={20} />
              </button>
            </div>

            {detailLoading ? (
              <div className="loading-container" style={{ padding: '40px 20px' }}>
                <div className="spinner" />
                <p>加载详情...</p>
              </div>
            ) : (
              <>
                <div className="modal-body">
                  {/* Description */}
                  <div className="detail-section">
                    <label className="detail-label">描述</label>
                    {editingDesc ? (
                      <div className="detail-edit-row">
                        <textarea
                          className="detail-textarea"
                          value={editDescValue}
                          onChange={(e) => setEditDescValue(e.target.value)}
                          rows={3}
                        />
                        <div className="detail-edit-actions">
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => {
                              setEditingDesc(false)
                              setEditDescValue(detailRole.description || '')
                            }}
                          >
                            取消
                          </button>
                          <button
                            className="btn btn-sm btn-primary"
                            onClick={handleSaveDescription}
                            disabled={savingDesc}
                          >
                            {savingDesc ? '保存中...' : '保存'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="detail-value-row">
                        <span className="detail-value">
                          {detailRole.description || <span className="text-muted">暂无描述</span>}
                        </span>
                        {!detailRole.is_system && (
                          <button
                            className="btn btn-sm btn-ghost"
                            onClick={() => setEditingDesc(true)}
                          >
                            <Edit3 size={14} />
                            编辑
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Metadata */}
                  <div className="detail-section detail-meta">
                    <div className="detail-meta-item">
                      <Users size={16} />
                      <span>{detailRole.users.length} 个用户拥有此角色</span>
                    </div>
                    <div className="detail-meta-item">
                      <Clock size={16} />
                      <span>创建于 {formatDate(detailRole.created_at)}</span>
                    </div>
                  </div>

                  {/* Users table */}
                  <div className="detail-section">
                    <label className="detail-label">拥有该角色的用户</label>
                    {detailRole.users.length === 0 ? (
                      <p className="text-muted" style={{ padding: '12px 0', fontSize: '0.875rem' }}>
                        暂无用户
                      </p>
                    ) : (
                      <div className="detail-table-wrapper">
                        <table className="detail-table">
                          <thead>
                            <tr>
                              <th>用户名</th>
                              <th>姓名</th>
                              <th>状态</th>
                              <th>创建时间</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detailRole.users.map((u) => (
                              <tr key={u.id}>
                                <td>{u.username}</td>
                                <td>{u.name}</td>
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
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer actions */}
                <div className="modal-footer">
                  {detailRole.is_system ? (
                    <span className="text-muted text-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Shield size={14} />
                      系统角色不可删除
                    </span>
                  ) : (
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => setDeleteTarget(detailRole.name)}
                    >
                      <Trash2 size={14} />
                      删除角色
                    </button>
                  )}
                  <button className="btn btn-sm btn-secondary" onClick={closeDetail}>
                    关闭
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ===== Create Role Modal ===== */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>新建角色</h3>
              <button
                className="btn btn-ghost btn-icon"
                onClick={() => setShowCreate(false)}
              >
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>角色名称</label>
                <input
                  type="text"
                  placeholder="输入角色名称（将自动转为大写）"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value.toUpperCase())}
                />
              </div>
              <div className="form-group">
                <label>角色描述</label>
                <textarea
                  placeholder="输入角色描述"
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setShowCreate(false)}
              >
                取消
              </button>
              <button
                className="btn btn-sm btn-primary"
                onClick={handleCreateRole}
                disabled={creating || !createName.trim()}
              >
                {creating ? '创建中...' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== Delete Confirm Modal ===== */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>确认删除</h3>
            <p>
              删除后将把该角色的所有用户转为 <strong>STUDENT</strong>，确定继续？
            </p>
            <div className="modal-actions">
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setDeleteTarget(null)}
              >
                取消
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={() => handleDeleteRole(deleteTarget)}
                disabled={deleting}
              >
                {deleting ? '删除中...' : '确认删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
