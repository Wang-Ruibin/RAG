import { useState, useEffect } from 'react';
import { Card, Table, Tag, Select, message } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import api from '../services/api';

export default function UserManagement() {
  const [users, setUsers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadUsers(); }, [page]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const r: any = await api.get(`/user/list?page=${page}&page_size=20`);
      if (r.code === 200) { setUsers(r.data.items || []); setTotal(r.data.total); }
    } catch (e) {} finally { setLoading(false); }
  };

  const updateRole = async (id: number, role: string) => {
    try { await api.put(`/user/${id}/role?role=${role}`); message.success('角色已更新'); loadUsers(); } catch (e) {}
  };

  const toggleStatus = async (id: number, status: number) => {
    try { await api.put(`/user/${id}/status?status=${status}`); message.success(status === 1 ? '已启用' : '已禁用'); loadUsers(); } catch (e) {}
  };

  return (
    <Card className="shadow-sm" title={<><UserOutlined className="mr-2" />人员管理</>}>
      <Table rowKey="id" dataSource={users} loading={loading}
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => setPage(p), showTotal: (t) => `共 ${t} 用户` }}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '用户名', dataIndex: 'username' },
          { title: '昵称', dataIndex: 'nickname' },
          { title: '邮箱', dataIndex: 'email' },
          { title: '角色', dataIndex: 'role', width: 150, render: (role: string, r: any) => (
            <Select value={role} style={{ width: 100 }} onChange={(v) => updateRole(r.id, v)}
              options={[{ label: '学生', value: 'student' }, { label: '教师', value: 'teacher' }, { label: '管理员', value: 'admin' }]} />
          )},
          { title: '状态', dataIndex: 'status', width: 100, render: (s: number, r: any) => (
            s === 1
              ? <Tag color="success" style={{ cursor: 'pointer' }} onClick={() => toggleStatus(r.id, 0)}>正常</Tag>
              : <Tag color="error" style={{ cursor: 'pointer' }} onClick={() => toggleStatus(r.id, 1)}>已禁用</Tag>
          )},
          { title: '注册时间', dataIndex: 'created_at', width: 170, render: (d: string) => new Date(d).toLocaleString() },
        ]}
      />
    </Card>
  );
}
