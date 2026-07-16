import { FileTextOutlined, LogoutOutlined, MessageOutlined, TeamOutlined } from '@ant-design/icons'
import { Button, Layout, Menu, Spin, Typography } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'

const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage').then((module) => ({ default: module.DocumentsPage })))
const UsersPage = lazy(() => import('./pages/UsersPage').then((module) => ({ default: module.UsersPage })))

function Protected({ admin = false }: { admin?: boolean }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center-screen"><Spin size="large" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (admin && user.role !== 'ADMIN') return <Navigate to="/chat" replace />
  return <Outlet />
}

function Shell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const items = [
    { key: '/chat', icon: <MessageOutlined />, label: '校园问答' },
    ...(user?.role === 'ADMIN'
      ? [
          { key: '/admin/documents', icon: <FileTextOutlined />, label: '知识库' },
          { key: '/admin/users', icon: <TeamOutlined />, label: '用户管理' },
        ]
      : []),
  ]
  return (
    <Layout className="app-shell">
      <Layout.Sider breakpoint="lg" collapsedWidth="0" className="app-sider">
        <div className="brand">
          <div className="brand-mark">河</div>
          <div><strong>河海智答</strong><span>CampusQA</span></div>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={items}
          onClick={({ key }) => navigate(key)}
        />
        <div className="sider-user">
          <Typography.Text ellipsis>{user?.name}</Typography.Text>
          <Typography.Text type="secondary">{user?.role === 'ADMIN' ? '管理员' : '学生'}</Typography.Text>
          <Button type="text" icon={<LogoutOutlined />} onClick={() => { logout(); navigate('/login') }}>
            退出登录
          </Button>
        </div>
      </Layout.Sider>
      <Layout.Content className="app-content"><Outlet /></Layout.Content>
    </Layout>
  )
}

export default function App() {
  return (
    <Suspense fallback={<div className="center-screen"><Spin size="large" /></div>}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Protected />}>
          <Route element={<Shell />}>
            <Route path="/chat" element={<ChatPage />} />
            <Route element={<Protected admin />}>
              <Route path="/admin/documents" element={<DocumentsPage />} />
              <Route path="/admin/users" element={<UsersPage />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/chat" replace />} />
      </Routes>
    </Suspense>
  )
}
