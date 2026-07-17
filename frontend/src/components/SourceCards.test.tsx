// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { SourceCards } from './SourceCards'

afterEach(() => cleanup())

describe('SourceCards', () => {
  it('keeps the source group collapsed and renders live web sources in gold', () => {
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

    expect(screen.getByText('引用来源（1）')).toBeVisible()
    expect(screen.queryByText('W1')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('引用来源（1）'))
    expect(screen.getByText('W1')).toBeVisible()
    expect(screen.getByText('W1').closest('.ant-tag')).toHaveClass('ant-tag-gold')
    fireEvent.click(screen.getByText('河海大学通知'))
    expect(screen.getByText('河海大学')).toBeInTheDocument()
    expect(screen.getByText('发布：2026-07-02')).toBeInTheDocument()
    expect(screen.getByText('官网发布的最新通知摘要。')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /查看来源/ })).toHaveAttribute(
      'href',
      'https://www.hhu.edu.cn/news',
    )
  })

  it('renders archived web pages and reviewed corrections as blue local S sources', () => {
    render(
      <SourceCards
        sources={[
          {
            source_type: 'WEB_ARCHIVE',
            citation_index: 1,
            title: '已归档的院系设置',
            source_url: 'https://www.hhu.edu.cn/xy.shtml',
            snippet: '该网页内容已经进入本地知识库。',
          },
          {
            source_type: 'USER_CORRECTION',
            citation_index: 2,
            title: '用户纠错：校训',
            contributor_name: '知识提供者',
            snippet: '这是审核通过的正确答案。',
          },
        ]}
      />,
    )

    fireEvent.click(screen.getByText('引用来源（2）'))
    expect(screen.getByText('S1').closest('.ant-tag')).toHaveClass('ant-tag-blue')
    expect(screen.getByText('S2').closest('.ant-tag')).toHaveClass('ant-tag-blue')
    expect(screen.queryByText('W1')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('用户纠错：校训'))
    expect(screen.getByText('由知识提供者提供，经管理员审核')).toBeVisible()
  })
})
