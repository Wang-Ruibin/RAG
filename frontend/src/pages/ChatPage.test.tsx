// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '../lib/api'
import { ChatPage } from './ChatPage'

vi.mock('../lib/api', () => ({ api: vi.fn() }))

beforeAll(() => {
  Object.defineProperty(globalThis, 'ResizeObserver', {
    writable: true,
    value: class ResizeObserver {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  })
  Object.defineProperty(Element.prototype, 'scrollIntoView', {
    writable: true,
    value: vi.fn(),
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
})

beforeEach(() => {
  vi.mocked(api).mockReset()
})

afterEach(() => cleanup())

describe('ChatPage', () => {
  it('proactively introduces itself in every blank conversation', async () => {
    vi.mocked(api).mockResolvedValue([])

    render(<ChatPage />)

    const welcome = await screen.findByTestId('welcome-message')
    expect(welcome).toHaveTextContent('河海智答')
    expect(welcome).toHaveTextContent('河海大学')

    fireEvent.click(screen.getByRole('button', { name: /新对话/ }))
    expect(screen.getByTestId('welcome-message')).toHaveTextContent('河海智答')
    expect(screen.getByTestId('welcome-message')).toHaveTextContent('河海大学')
  })

  it('restores the web-search answer badge from conversation history', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/api/conversations') {
        return [{ id: 1, title: '校历查询', created_at: '2026-07-16T00:00:00Z' }]
      }
      if (path === '/api/conversations/1') {
        return {
          id: 1,
          title: '校历查询',
          created_at: '2026-07-16T00:00:00Z',
          messages: [
            {
              id: 2,
              role: 'ASSISTANT',
              content: '请以官网校历为准。[W1]',
              sources: [],
              status: 'COMPLETE',
              answer_origin: 'WEB_SEARCH',
            },
          ],
        }
      }
      throw new Error(`Unexpected API path: ${path}`)
    })

    render(<ChatPage />)
    fireEvent.click(await screen.findByText('校历查询'))

    expect(await screen.findByText('联网搜索回答')).toBeInTheDocument()
    expect(screen.getByText(/请以官网校历为准/)).toBeInTheDocument()
  })

  it('copies an answer and submits mutually exclusive positive feedback', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/api/conversations') return [{ id: 2, title: '校训', created_at: '2026-07-17T00:00:00Z' }]
      if (path === '/api/conversations/2') {
        return {
          id: 2,
          title: '校训',
          created_at: '2026-07-17T00:00:00Z',
          messages: [{
            id: 20,
            role: 'ASSISTANT',
            content: '河海大学校训是艰苦朴素、实事求是。[S1]',
            sources: [],
            status: 'COMPLETE',
            answer_origin: 'KNOWLEDGE_BASE',
          }],
        }
      }
      if (path === '/api/messages/20/knowledge-task') {
        return {
          id: 8,
          assistant_message_id: 20,
          status: 'COMPLETE',
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-17T00:00:00Z',
        }
      }
      throw new Error(`Unexpected API path: ${path}`)
    })

    render(<ChatPage />)
    fireEvent.click(await screen.findByText('校训'))
    fireEvent.click(await screen.findByRole('button', { name: '复制此回答' }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('河海大学校训是艰苦朴素、实事求是。[S1]'))
    fireEvent.click(screen.getByRole('button', { name: '此答案准确，加入知识库' }))
    expect(await screen.findByText('已加入知识库')).toBeVisible()
    expect(screen.getByRole('button', { name: '此答案不准确，我来提供答案' })).toBeDisabled()
  })

  it('allows correcting a no-answer response and persists the review status', async () => {
    vi.mocked(api).mockImplementation(async (path: string) => {
      if (path === '/api/conversations') return [{ id: 3, title: '未知问题', created_at: '2026-07-17T00:00:00Z' }]
      if (path === '/api/conversations/3') {
        return {
          id: 3,
          title: '未知问题',
          created_at: '2026-07-17T00:00:00Z',
          messages: [{
            id: 30,
            role: 'ASSISTANT',
            content: '暂未找到足够相关的信息。',
            sources: [],
            status: 'COMPLETE',
            answer_origin: 'NO_ANSWER',
          }],
        }
      }
      if (path === '/api/messages/30/correction') {
        return {
          id: 9,
          assistant_message_id: 30,
          status: 'PENDING',
          proposed_answer: '这是用户提供的正确答案。',
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-17T00:00:00Z',
        }
      }
      throw new Error(`Unexpected API path: ${path}`)
    })

    render(<ChatPage />)
    fireEvent.click(await screen.findByText('未知问题'))
    expect(await screen.findByRole('button', { name: '此答案准确，加入知识库' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: '此答案不准确，我来提供答案' }))
    fireEvent.change(screen.getByPlaceholderText('请输入你认为准确的答案'), {
      target: { value: '这是用户提供的正确答案。' },
    })
    fireEvent.click(screen.getByRole('button', { name: /提\s*交/ }))
    expect(await screen.findByText('纠错待审核')).toBeVisible()
    expect(screen.getByRole('button', { name: '此答案准确，加入知识库' })).toBeDisabled()
  })

  it('searches conversation titles and persists an inline rename', async () => {
    let title = '校训查询'
    vi.mocked(api).mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === '/api/conversations/1' && init?.method === 'PATCH') {
        title = String(JSON.parse(String(init.body)).title)
        return {
          id: 1,
          title,
          message_count: 2,
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-18T00:00:00Z',
        }
      }
      if (path === '/api/conversations?q=%E6%A0%A1%E8%AE%AD') {
        return [{
          id: 1,
          title,
          message_count: 2,
          created_at: '2026-07-17T00:00:00Z',
          updated_at: '2026-07-18T00:00:00Z',
        }]
      }
      if (path === '/api/conversations') {
        return [
          { id: 1, title, message_count: 2, created_at: '2026-07-17T00:00:00Z' },
          { id: 2, title: '宿舍信息', message_count: 4, created_at: '2026-07-17T00:00:00Z' },
        ]
      }
      throw new Error(`Unexpected API path: ${path}`)
    })

    render(<ChatPage />)
    expect(await screen.findByText('宿舍信息')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('搜索历史会话'), {
      target: { value: '校训' },
    })
    await waitFor(() => expect(api).toHaveBeenCalledWith('/api/conversations?q=%E6%A0%A1%E8%AE%AD'))
    expect(screen.queryByText('宿舍信息')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '重命名会话：校训查询' }))
    fireEvent.change(screen.getByRole('textbox', { name: '编辑会话标题' }), {
      target: { value: '河海大学校训' },
    })
    fireEvent.click(screen.getByRole('button', { name: '保存会话标题' }))

    await waitFor(() => expect(api).toHaveBeenCalledWith('/api/conversations/1', {
      method: 'PATCH',
      body: JSON.stringify({ title: '河海大学校训' }),
    }))
    expect(await screen.findByText('河海大学校训')).toBeInTheDocument()
  })
})
