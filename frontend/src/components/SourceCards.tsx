import { LinkOutlined } from '@ant-design/icons'
import { Collapse, Space, Tag, Typography } from 'antd'
import type { SourceRef } from '../types'

function sourceLabel(source: SourceRef, index: number) {
  const prefix = source.source_type === 'WEB_SEARCH' ? 'W' : 'S'
  return `${prefix}${source.citation_index ?? index + 1}`
}

function sourceSite(source: SourceRef) {
  if (source.source_type === 'WEB_SEARCH') return source.site_name || source.domain || '网页来源'
  if (!source.source_url) return '知识库'
  try {
    return new URL(source.source_url).hostname
  } catch {
    return '知识库'
  }
}

function sourceHref(source: SourceRef) {
  return source.url || source.source_url || ''
}

export function SourceCards({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <Collapse
      ghost
      size="small"
      items={sources.map((source, index) => {
        const href = sourceHref(source)
        const isWeb = source.source_type === 'WEB_SEARCH'
        return {
          key: `${sourceLabel(source, index)}-${href || source.chunk_id || index}`,
          label: (
            <Space wrap>
              <Tag color={isWeb ? 'gold' : 'cyan'}>{sourceLabel(source, index)}</Tag>
              <span>{source.title}</span>
            </Space>
          ),
          children: (
            <div className={isWeb ? 'source-detail web-source' : 'source-detail'}>
              <Space wrap>
                <Typography.Text type="secondary">{sourceSite(source)}</Typography.Text>
                {source.published_at && (
                  <Typography.Text type="secondary">发布：{source.published_at}</Typography.Text>
                )}
                {href && (
                  <a href={href} target="_blank" rel="noopener noreferrer">
                    <LinkOutlined /> 查看来源
                  </a>
                )}
              </Space>
              <Typography.Paragraph>{source.snippet || source.content}</Typography.Paragraph>
            </div>
          ),
        }
      })}
    />
  )
}
