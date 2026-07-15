import { useState, useEffect } from 'react';
import { Card, Table, Tag, Select, Button, Modal, Form, Input, message, Popconfirm } from 'antd';
import { UserOutlined, PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons';
import api from '../services/api';

export default function UserManagement() {
  const [users, setUsers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [editingUser, setEditingUser] = useState<any>(null);
  const [form] = Form.useForm();
  const [keyword, setKeyword] = useState('');
  const [filterRole, setFilterRole] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<number | undefined>();

  useEffect(() => { loadUsers(); }, [page, filterRole, filterStatus]);
  useEffect(() => { setPage(1); loadUsers(); }, [keyword]);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (keyword) params.set('keyword', keyword);
      if (filterRole) params.set('role', filterRole);
      if (filterStatus !== undefined) params.set('status', String(filterStatus));
      const r: any = await api.get(`/user/list?${params}`);
      if (r.code === 200) { setUsers(r.data.items || []); setTotal(r.data.total); }
    } catch (e) {} finally { setLoading(false); }
  };

  const openCreate = () => { setModalType('create'); setEditingUser(null); form.resetFields(); setModalOpen(true); };
  const openEdit = (u: any) => { setModalType('edit'); setEditingUser(u); form.setFieldsValue({ nickname: u.nickname, email: u.email }); setModalOpen(true); };
  const handleSubmit = async () => {
    try {
      const values = form.getFieldsValue();
      if (modalType === 'create') { await api.post('/user/register', { ...values, password: '123456' }); message.success('创建成功，默认密码 123456'); }
      else { await api.put(`/user/${editingUser.id}`, values); message.success('已更新'); }
      setModalOpen(false); loadUsers();
    } catch (e) {}
  };
  const updateRole = async (id: number, role: string) => { try { await api.put(`/user/${id}/role?role=${role}`); loadUsers(); } catch (e) {} };
  const toggleStatus = async (id: number, s: number) => { try { await api.put(`/user/${id}/status?status=${s}`); message.success(s === 1 ? '已启用' : '已禁用'); loadUsers(); } catch (e) {} };
  const deleteUser = async (id: number) => { try { await api.delete(`/user/${id}`); message.success('已删除'); loadUsers(); } catch (e) {} };

  return (
    <Card className="shadow-sm" title={<><UserOutlined className="mr-2" />人员管理</>} extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增用户</Button>}>
      <div className="flex flex-wrap gap-3 mb-4">
        <Input placeholder="搜索用户名/昵称/邮箱" value={keyword} onChange={(e) => setKeyword(e.target.value)} onPressEnter={loadUsers} prefix={<SearchOutlined />} style={{ width: 260 }} allowClear />
        <Select placeholder="角色筛选" value={filterRole} onChange={(v) => setFilterRole(v)} allowClear style={{ width: 120 }}
          options={[{ label: '学生', value: 'student' }, { label: '教师', value: 'teacher' }, { label: '管理员', value: 'admin' }]} />
        <Select placeholder="状态筛选" value={filterStatus} onChange={(v) => setFilterStatus(v)} allowClear style={{ width: 120 }}
          options={[{ label: '正常', value: 1 }, { label: '已禁用', value: 0 }]} />
        <Button icon={<SearchOutlined />} onClick={loadUsers}>查询</Button>
      </div>
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
            s === 1 ? <Tag color="success" style={{ cursor: 'pointer' }} onClick={() => toggleStatus(r.id, 0)}>正常</Tag>
                    : <Tag color="error" style={{ cursor: 'pointer' }} onClick={() => toggleStatus(r.id, 1)}>已禁用</Tag>
          )},
          { title: '注册时间', dataIndex: 'created_at', width: 160, render: (d: string) => new Date(d).toLocaleString() },
          { title: '操作', width: 140, render: (_: any, r: any) => (
            <div className="flex gap-1">
              <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>编辑</Button>
              <Popconfirm title="确认删除？" onConfirm={() => deleteUser(r.id)} okText="删除" cancelText="取消">
                <Button type="link" danger size="small" icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </div>
          )},
        ]} />
      <Modal title={modalType === 'create' ? '新增用户' : '编辑用户'} open={modalOpen} onCancel={() => setModalOpen(false)} onOk={handleSubmit}
        okText={modalType === 'create' ? '创建' : '保存'}>
        <Form form={form} layout="vertical">
          {modalType === 'create' && <Form.Item label="用户名" name="username" rules={[{ required: true, message: '必填' }]}><Input placeholder="用户名" /></Form.Item>}
          <Form.Item label="昵称" name="nickname"><Input placeholder="昵称" /></Form.Item>
          <Form.Item label="邮箱" name="email"><Input placeholder="邮箱" /></Form.Item>
          {modalType === 'create' && <Form.Item label="角色" name="role" initialValue="student"><Select options={[{ label: '学生', value: 'student' }, { label: '教师', value: 'teacher' }, { label: '管理员', value: 'admin' }]} /></Form.Item>}
          {modalType === 'create' && <div className="text-xs text-gray-400">默认密码: 123456</div>}
        </Form>
      </Modal>
    </Card>
  );
}
