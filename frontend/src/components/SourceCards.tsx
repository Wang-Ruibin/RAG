import { LinkOutlined } from '@ant-design/icons'
import { Collapse, Space, Tag, Typography } from 'antd'
import type { SourceRef } from '../types'

function sourceLabel(source: SourceRef, index: number) {
  const prefix = source.source_type === 'WEB_SEARCH' ? 'W' : 'S'
  return `${prefix}${source.citation_index ?? index + 1}`
}

function sourceSite(source: SourceRef) {
  if (source.source_type === 'USER_CORRECTION') {
    return `由${source.contributor_name || '用户'}提供，经管理员审核`
  }
  if (['WEB_SEARCH', 'WEB_ARCHIVE'].includes(source.source_type || '')) {
    return source.site_name || source.domain || (source.source_type === 'WEB_ARCHIVE' ? '网页归档' : '网页来源')
  }
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
      className="source-group"
      items={[{
        key: 'sources',
        label: <Typography.Text type="secondary">引用来源（{sources.length}）</Typography.Text>,
        children: (
          <Collapse
            ghost
            size="small"
            className="source-items"
            items={sources.map((source, index) => {
              const href = sourceHref(source)
              const isLiveWeb = source.source_type === 'WEB_SEARCH'
              return {
                key: `${sourceLabel(source, index)}-${href || source.chunk_id || index}`,
                label: (
                  <Space wrap>
                    <Tag color={isLiveWeb ? 'gold' : 'blue'}>{sourceLabel(source, index)}</Tag>
                    <span>{source.title}</span>
                  </Space>
                ),
                children: (
                  <div className={isLiveWeb ? 'source-detail web-source' : 'source-detail'}>
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
        ),
      }]}
    />
  )
}
