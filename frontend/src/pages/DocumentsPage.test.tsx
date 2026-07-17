// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import type { CampusDocument } from '../types'
import { DocumentsPage } from './DocumentsPage'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../lib/api', () => ({ api: vi.fn(), apiBlob: vi.fn() }))

const documentRow: CampusDocument = {
  id: 1,
  title: '校园办事指南',
  original_name: 'guide.md',
  mime_type: 'text/markdown',
  size: 128,
  category: '校园生活',
  document_kind: 'KNOWLEDGE_BASE',
  status: 'READY',
  stage: 'COMPLETE',
  chunk_count: 1,
  created_at: '2026-07-17T00:00:00Z',
  updated_at: '2026-07-17T00:00:00Z',
}

beforeAll(() => {
  Object.defineProperty(globalThis, 'ResizeObserver', {
    writable: true,
    value: class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches: false,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  })
})

beforeEach(() => {
  vi.mocked(api).mockImplementation(async (path: string) => {
    if (path.startsWith('/api/documents?')) return { items: [documentRow], total: 1 }
    if (path === '/api/documents/1') return documentRow
    if (path === '/api/documents/1/preview?offset=0&limit=20000') {
      return {
        content: '# 校园办事指南\n\n这是知识文档原文。',
        offset: 0,
        limit: 20000,
        total_chars: 22,
        has_more: false,
        format: 'md',
      }
    }
    throw new Error(`Unexpected API path: ${path}`)
  })
})

afterEach(() => cleanup())

describe('DocumentsPage', () => {
  it('gives ordinary users a preview-only knowledge-base view', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 2, name: '普通用户', email: 'user@example.com', role: 'STUDENT', is_active: true, created_at: '2026-07-17T00:00:00Z' },
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })
    render(<DocumentsPage />)

    expect(await screen.findByText('校园办事指南')).toBeVisible()
    expect(screen.queryByText('点击或拖拽校园资料到这里')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '预览' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: '编辑' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '重建' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '删除' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '预览' }))
    expect(await screen.findByText(/这是知识文档原文/)).toBeVisible()
  })

  it('shows all four named document operations to administrators', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, name: '管理员', email: 'admin@example.com', role: 'ADMIN', is_active: true, created_at: '2026-07-17T00:00:00Z' },
      loading: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    })
    render(<DocumentsPage />)

    await screen.findByText('校园办事指南')
    expect(screen.getByRole('button', { name: '预览' })).toBeVisible()
    expect(screen.getByRole('button', { name: '编辑' })).toBeVisible()
    expect(screen.getByRole('button', { name: '重建' })).toBeVisible()
    expect(screen.getByRole('button', { name: '删除' })).toBeVisible()
  })
})
