// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SourceCards } from './SourceCards'

describe('SourceCards', () => {
  it('renders numbered Baidu web search source details', () => {
    render(
      <SourceCards
        sources={[
          {
            source_type: 'WEB_SEARCH',
            citation_index: 1,
            title: '河海大学通知',
            url: 'https://www.hhu.edu.cn/news',
            site_name: '河海大学',
            snippet: '官网发布的最新通知摘要。',
            published_at: '2026-07-02',
          },
        ]}
      />,
    )

    expect(screen.getByText('W1')).toBeInTheDocument()
    fireEvent.click(screen.getByText('河海大学通知'))
    expect(screen.getByText('河海大学')).toBeInTheDocument()
    expect(screen.getByText('发布：2026-07-02')).toBeInTheDocument()
    expect(screen.getByText('官网发布的最新通知摘要。')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /查看来源/ })).toHaveAttribute(
      'href',
      'https://www.hhu.edu.cn/news',
    )
  })
})
