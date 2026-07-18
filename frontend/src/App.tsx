import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

// Lazy-loaded page components (created in separate task)
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'))
const UsersPage = lazy(() => import('./pages/UsersPage'))
const ConversationsPage = lazy(() => import('./pages/ConversationsPage'))
const CachePage = lazy(() => import('./pages/CachePage'))

function PageLoader() {
  return (
    <div className="loading-page">
      <div className="loading-spinner">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12a9 9 0 11-6.219-8.56" />
        </svg>
      </div>
      <span>加载中...</span>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={
          <Suspense fallback={<PageLoader />}>
            <LoginPage />
          </Suspense>
        }
      />
      <Route
        path="/register"
        element={
          <Suspense fallback={<PageLoader />}>
            <RegisterPage />
          </Suspense>
        }
      />

      {/* Root redirects to /login — user must log in first */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* Protected routes with Layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route
          path="chat"
          element={
            <Suspense fallback={<PageLoader />}>
              <ChatPage />
            </Suspense>
          }
        />
        <Route
          path="chat/:id"
          element={
            <Suspense fallback={<PageLoader />}>
              <ChatPage />
            </Suspense>
          }
        />
        <Route
          path="documents"
          element={
            <ProtectedRoute>
              <Suspense fallback={<PageLoader />}>
                <DocumentsPage />
              </Suspense>
            </ProtectedRoute>
          }
        />
        <Route
          path="users"
          element={
            <ProtectedRoute adminOnly>
              <Suspense fallback={<PageLoader />}>
                <UsersPage />
              </Suspense>
            </ProtectedRoute>
          }
        />
        <Route
          path="conversations"
          element={
            <Suspense fallback={<PageLoader />}>
              <ConversationsPage />
            </Suspense>
          }
        />
        <Route
          path="cache"
          element={
            <ProtectedRoute adminOnly>
              <Suspense fallback={<PageLoader />}>
                <CachePage />
              </Suspense>
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
