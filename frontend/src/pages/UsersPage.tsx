import { Card, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import type { Role, User } from '../types'

export function UsersPage() {
  const { user: current } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const load = async () => { setLoading(true); try { setUsers(await api<User[]>('/api/admin/users')) } finally { setLoading(false) } }
  useEffect(() => {
    let cancelled = false
    api<User[]>('/api/admin/users')
      .then((result) => { if (!cancelled) setUsers(result) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  async function update(id: number, patch: { role?: Role; is_active?: boolean }) {
    try {
      await api(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
      void message.success('用户已更新'); await load()
    } catch (reason) { void message.error(reason instanceof Error ? reason.message : '更新失败') }
  }

  return (
    <div className="page-container">
      <header className="page-header"><div><Typography.Title level={3}>用户管理</Typography.Title><Typography.Text type="secondary">管理普通用户账号状态和管理员角色</Typography.Text></div></header>
      <Card>
        <Table
          rowKey="id" loading={loading} dataSource={users} pagination={{ pageSize: 12 }}
          columns={[
            { title: '用户', render: (_, row) => <div><strong>{row.name}</strong><br /><Typography.Text type="secondary">{row.email}</Typography.Text></div> },
            { title: '角色', dataIndex: 'role', render: (role: Role, row) => row.id === current?.id ? <Tag color="purple">当前管理员</Tag> : <Select value={role} style={{ width: 120 }} options={[{ value: 'STUDENT', label: '普通用户' }, { value: 'ADMIN', label: '管理员' }]} onChange={(value) => void update(row.id, { role: value })} /> },
            { title: '状态', dataIndex: 'is_active', render: (active: boolean, row) => <Space><Switch checked={active} disabled={row.id === current?.id} onChange={(value) => void update(row.id, { is_active: value })} /><span>{active ? '已启用' : '已停用'}</span></Space> },
            { title: '注册时间', dataIndex: 'created_at', render: (value: string) => new Date(value).toLocaleString('zh-CN') },
          ]}
        />
      </Card>
    </div>
  )
}
