import {
  BookOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  GlobalOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { Space, Tag, Typography } from 'antd'
import type { AgentStep } from '../types'

function StepIcon({ step }: { step: AgentStep }) {
  if (step.type === 'tool_call') {
    return <LoadingOutlined style={{ color: '#1677ff' }} />
  }
  if (step.status === 'error') {
    return <CloseCircleFilled style={{ color: '#ff4d4f' }} />
  }
  return <CheckCircleFilled style={{ color: '#52c41a' }} />
}

function ToolLabel({ toolName }: { toolName: string }) {
  if (toolName === 'knowledge_search') {
    return (
      <Tag icon={<BookOutlined />} color="blue">
        知识库
      </Tag>
    )
  }
  return (
    <Tag icon={<GlobalOutlined />} color="green">
      联网
    </Tag>
  )
}

export function AgentSteps({ steps }: { steps: AgentStep[] }) {
  if (!steps.length) return null
  return (
    <div
      className="agent-steps"
      style={{
        margin: '12px 0',
        padding: '12px',
        background: '#fafafa',
        borderRadius: 8,
        border: '1px solid #f0f0f0',
      }}
    >
      {steps.map((step, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            gap: 8,
            marginBottom: 8,
            alignItems: 'flex-start',
          }}
        >
          <div style={{ marginTop: 4 }}>
            <StepIcon step={step} />
          </div>
          <div style={{ flex: 1 }}>
            <Space>
              <ToolLabel toolName={step.tool_name} />
              {step.type === 'tool_call' ? (
                <Typography.Text type="secondary">正在搜索…</Typography.Text>
              ) : (
                <Typography.Text
                  style={{
                    color: step.status === 'error' ? '#ff4d4f' : '#52c41a',
                  }}
                >
                  {step.result?.summary ||
                    (step.status === 'error' ? '搜索失败' : '搜索完成')}
                </Typography.Text>
              )}
            </Space>
          </div>
        </div>
      ))}
    </div>
  )
}
