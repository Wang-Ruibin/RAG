import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  MessageSquare,
  BookOpen,
  Users,
  History,
  LogOut,
  Menu,
  X,
  GraduationCap,
  Database,
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { to: '/chat', label: 'AI 问答', icon: MessageSquare },
  { to: '/documents', label: '知识库', icon: BookOpen },
  { to: '/users', label: '用户管理', icon: Users, adminOnly: true },
  { to: '/cache', label: '缓存管理', icon: Database, adminOnly: true },
  { to: '/conversations', label: '问答记录', icon: History },
];

export default function Layout() {
  const { user, isAdmin, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const visibleNavItems = navItems.filter(
    (item) => !item.adminOnly || isAdmin
  );

  return (
    <div className="app-layout">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 99,
          }}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <GraduationCap size={28} />
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">校园问答助手</span>
            <span className="sidebar-brand-sub">河海大学</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="sidebar-link" onClick={logout} style={{ width: '100%', border: 'none', background: 'none', cursor: 'pointer' }}>
            <LogOut size={20} />
            <span>退出登录</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Top header */}
        <div className="top-header">
          <div className="top-header-left">
            <button
              className="btn btn-ghost btn-icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{ display: 'none' }}
              id="mobile-menu-btn"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
          <div className="top-header-right">
            <span className="top-header-user">
              {user?.name || user?.username || '用户'}
              {isAdmin && (
                <span className="badge badge-info" style={{ marginLeft: 8 }}>
                  管理员
                </span>
              )}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={logout}>
              <LogOut size={16} />
              退出
            </button>
          </div>
        </div>

        {/* Page content via react-router */}
        <Outlet />
      </main>

      {/* Mobile menu button (fixed) */}
      <button
        className="btn btn-primary btn-icon"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        style={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 200,
          display: 'none',
          borderRadius: '50%',
          width: 48,
          height: 48,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
        }}
        id="mobile-fab"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Responsive: show mobile elements via media query in index.css is cleaner,
          but we also toggle display here. The CSS in index.css handles the sidebar transform.
          The mobile menu button will be shown via a small injected style.
          We use a style tag approach here for simplicity. */}
      <style>{`
        @media (max-width: 768px) {
          #mobile-menu-btn { display: flex !important; }
          #mobile-fab { display: flex !important; }
        }
      `}</style>
    </div>
  );
}
