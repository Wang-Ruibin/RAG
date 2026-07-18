import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { LogIn, User, Lock, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/chat', { replace: true })
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* Decorative wave SVG */}
      <div className="auth-wave-bg">
        <svg viewBox="0 0 1440 120" preserveAspectRatio="none">
          <path d="M0,32 C360,80 720,0 1080,48 C1260,72 1350,56 1440,32 L1440,120 L0,120 Z" fill="var(--hhu-navy)" />
        </svg>
      </div>

      {/* Brand header above card */}
      <div className="auth-brand-header">
        <div className="auth-school-name">河 海 大 学</div>
        <div className="auth-motto">艰苦朴素 · 实事求是 · 严格要求 · 勇于探索</div>
      </div>

      <div className="auth-card">
        <div className="auth-card-header">
          <div className="auth-icon-wrap">
            <LogIn size={24} />
          </div>
          <h1>登录</h1>
          <p>校园问答助手</p>
        </div>

        {error && (
          <div className="auth-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">
              <User size={16} />
              账号
            </label>
            <input
              id="username"
              type="text"
              placeholder="请输入用户名"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <Lock size={16} />
              密码
            </label>
            <input
              id="password"
              type="password"
              placeholder="请输入密码"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          <button className="btn btn-block" type="submit" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="auth-footer">
          <span>还没有账号？</span>
          <Link to="/register">立即注册</Link>
        </div>
      </div>
    </div>
  )
}
