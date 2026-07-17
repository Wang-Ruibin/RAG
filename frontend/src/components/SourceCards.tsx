import { BookOutlined, GlobalOutlined, LinkOutlined } from '@ant-design/icons'
import { Collapse, Space, Tag, Typography } from 'antd'
import type { SourceRef } from '../types'

function SourceTag({ source, index }: { source: SourceRef; index: number }) {
  if (source.type === 'web') {
    return (
      <Tag icon={<GlobalOutlined />} color="green">
        {source.citation || `W${index + 1}`}
      </Tag>
    )
  }
  return (
    <Tag icon={<BookOutlined />} color="cyan">
      {source.citation || `S${source.citation_index ?? index + 1}`}
    </Tag>
  )
}

export function SourceCards({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <Collapse
      ghost
      size="small"
      items={sources.map((source, index) => ({
        key: source.chunk_id ?? index,
        label: (
          <Space wrap>
            <SourceTag source={source} index={index} />
            <span>{source.title}</span>
          </Space>
        ),
        children: (
          <div className="source-detail">
            <Space wrap>
              {source.published_at && <Typography.Text type="secondary">发布：{source.published_at}</Typography.Text>}
              {(source.source_url || source.url) && (
                <a href={source.source_url || source.url} target="_blank" rel="noopener noreferrer">
                  <LinkOutlined /> 查看原文
                </a>
              )}
            </Space>
            <Typography.Paragraph>{source.snippet || source.content}</Typography.Paragraph>
          </div>
        ),
      }))}
    />
  )
}
