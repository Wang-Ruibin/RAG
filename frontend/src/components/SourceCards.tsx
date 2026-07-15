import { LinkOutlined } from '@ant-design/icons'
import { Collapse, Progress, Space, Tag, Typography } from 'antd'
import type { SourceRef } from '../types'

export function SourceCards({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <Collapse
      ghost
      size="small"
      items={sources.map((source, index) => ({
        key: source.chunk_id,
        label: <Space wrap><Tag color="cyan">S{index + 1}</Tag><span>{source.title}</span></Space>,
        children: (
          <div className="source-detail">
            <Space wrap>
              {source.published_at && <Typography.Text type="secondary">发布：{source.published_at}</Typography.Text>}
              <Typography.Text type="secondary">相关度</Typography.Text>
              <Progress percent={Math.round(source.score * 100)} size="small" style={{ width: 110 }} />
              {source.source_url && (
                <a href={source.source_url} target="_blank" rel="noopener noreferrer">
                  <LinkOutlined /> 查看原文
                </a>
              )}
            </Space>
            <Typography.Paragraph>{source.snippet}</Typography.Paragraph>
          </div>
        ),
      }))}
    />
  )
}
