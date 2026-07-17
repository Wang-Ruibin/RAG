// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'
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

describe('ChatPage', () => {
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
})
