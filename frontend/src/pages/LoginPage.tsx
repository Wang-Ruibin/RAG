import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Form, Input, Segmented, Typography } from 'antd'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  if (user) return <Navigate to="/chat" replace />

  async function submit(values: { name?: string; email: string; password: string }) {
    setSubmitting(true)
    setError('')
    try {
      if (mode === 'login') await login(values.email, values.password)
      else await register(values.name || '', values.email, values.password)
      navigate('/chat')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="brand-mark large">河</div>
        <Typography.Title>河海智答</Typography.Title>
        <Typography.Paragraph>让分散的校园信息，成为可信、可追溯的答案。</Typography.Paragraph>
        <div className="intro-points">
          <span>混合检索</span><span>原文引用</span><span>流式问答</span>
        </div>
      </section>
      <Card className="login-card">
        <Typography.Title level={3}>欢迎使用 CampusQA</Typography.Title>
        <Segmented
          block
          value={mode}
          options={[{ label: '登录', value: 'login' }, { label: '普通用户注册', value: 'register' }]}
          onChange={(value) => setMode(value as 'login' | 'register')}
        />
        {error && <Alert type="error" message={error} showIcon closable onClose={() => setError('')} />}
        <Form layout="vertical" onFinish={submit} requiredMark={false}>
          {mode === 'register' && (
            <Form.Item name="name" label="姓名" rules={[{ required: true, min: 2 }]}>
              <Input prefix={<UserOutlined />} placeholder="你的姓名" />
            </Form.Item>
          )}
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input prefix={<MailOutlined />} placeholder="name@example.com" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: mode === 'register' ? 8 : 1 }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="至少 8 位" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" loading={submitting}>
            {mode === 'login' ? '登录' : '创建账号'}
          </Button>
        </Form>
      </Card>
    </main>
  )
}
