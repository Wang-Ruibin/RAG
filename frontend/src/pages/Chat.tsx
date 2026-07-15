import { useState, useEffect, useRef } from 'react';
import {
  Card,
  Input,
  Button,
  List,
  Tag,
  message,
  Spin,
  Empty,
  Tooltip,
  Avatar,
  Badge,
  Space,
} from 'antd';
import {
  SendOutlined,
  PlusOutlined,
  DeleteOutlined,
  LikeOutlined,
  DislikeOutlined,
  RobotOutlined,
  UserOutlined,
  FireOutlined, DownOutlined, PaperClipOutlined,
} from '@ant-design/icons';
import api from '../services/api';
import { getAuth } from '../services/api';

interface Message {
  id: number;
  role: 'user' | 'ai';
  content: string;
  recordId?: number;
  fromCache?: boolean;
  sources?: any[];
  feedback?: number;
  isRAG?: boolean;
}

interface Session {
  session_id: string;
  question_count: number;
  last_question: string;
  last_answer: string;
  updated_at: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<string>('');
  const [hotQuestions, setHotQuestions] = useState<{ question: string; count: number }[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = getAuth();
  const [isRagMode, setIsRagMode] = useState(true); // RAG 模式默认开启
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());

  const generateSessionId = () => 'session-' + Date.now();

  useEffect(() => {
    loadSessions();
    loadHotQuestions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const res: any = await api.get('/qa/history');
      if (res.code === 200) {
        setSessions(res.data.items || []);
      }
    } catch (e) {}
  };

  const loadHotQuestions = async () => {
    try {
      const res: any = await api.get('/qa/hot?limit=10');
      if (res.code === 200) {
        setHotQuestions(res.data.questions || []);
      }
    } catch (e) {}
  };

  const loadSessionMessages = async (sessionId: string) => {
    setCurrentSession(sessionId);
    setMessages([]);
    setLoading(true);
    try {
      const res: any = await api.get(`/qa/session/${sessionId}?page_size=100`);
      if (res.code === 200) {
        const loaded: Message[] = [];
        res.data.items.forEach((item: any) => {
          loaded.push({ id: item.id * 2, role: 'user', content: item.question });
          if (item.answer) {
            loaded.push({
              id: item.id * 2 + 1,
              role: 'ai',
              content: item.answer,
              recordId: item.id,
              sources: item.sources,
              feedback: item.feedback,
            });
          }
        });
        setMessages(loaded);
      }
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = () => {
    setCurrentSession(generateSessionId());
    setMessages([]);
  };

  const sendMessage = async () => {
    if (!input.trim()) return;
    const question = input.trim();
    setInput('');

    const sessionId = currentSession || generateSessionId();
    if (!currentSession) setCurrentSession(sessionId);

    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content: question }]);
    setLoading(true);

    try {
      if (isRagMode) {
        const res: any = await api.post('/ai/query', { question, top_k: 5 });
        if (res.code === 200) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now(),
              role: 'ai',
              content: res.data.answer || "未获取到回答",
              sources: res.data.sources,
              isRAG: true,
            },
          ]);
          loadSessions();
          loadHotQuestions();
        }
      } else {
        const res: any = await api.post(`/qa/ask?question=${encodeURIComponent(question)}&session_id=${sessionId}`);
        if (res.code === 200) {
          if (res.data.from_cache) {
            setMessages((prev) => [
              ...prev,
              {
                id: res.data.id || Date.now(),
                role: 'ai',
                content: res.data.answer,
                fromCache: true,
              },
            ]);
          } else {
            // Simulate AI answer for demo (in real scenario, would call RAG engine)
            const answer = `关于"${question}"，我暂时没有找到匹配的校园资料。这是系统演示回复，实际接入 RAG 后会根据知识库生成回答。`;
            await api.post('/qa/answer', {
              record_id: res.data.id,
              answer,
              sources: [{ title: '校园知识库', url: '#' }],
              tokens_used: 120,
              duration_ms: 800,
            });
            setMessages((prev) => [
              ...prev,
              {
                id: res.data.id || Date.now(),
                role: 'ai',
                content: answer,
                recordId: res.data.id,
                sources: [{ title: '校园知识库', url: '#' }],
              },
            ]);
          }
          loadSessions();
          loadHotQuestions();
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleSources = (messageId: number) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  };

  const submitFeedback = async (recordId: number, feedback: number) => {
    try {
      await api.post(`/qa/feedback?record_id=${recordId}&feedback=${feedback}`);
      message.success('反馈已提交');
      setMessages((prev) =>
        prev.map((m) => (m.recordId === recordId ? { ...m, feedback } : m))
      );
    } catch (e) {}
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await api.delete(`/qa/session/${sessionId}`);
      message.success('会话已删除');
      loadSessions();
      if (sessionId === currentSession) {
        setCurrentSession('');
        setMessages([]);
      }
    } catch (e) {}
  };

  return (
    <div className="flex gap-6 h-[calc(100vh-120px)]">
      {/* Left Sidebar */}
      <Card className="w-72 flex-shrink-0 flex flex-col shadow-sm" bodyStyle={{ padding: 16, height: '100%' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={createNewSession}
          className="mb-4 bg-gradient-to-r from-blue-500 to-indigo-600"
        >
          新会话
        </Button>

        <div className="text-sm font-medium text-gray-700 mb-2">历史会话</div>
        <div className="flex-1 overflow-auto">
          {sessions.length === 0 ? (
            <Empty description="暂无会话" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <List
              dataSource={sessions}
              renderItem={(s) => (
                <List.Item
                  className={`cursor-pointer rounded-lg px-3 py-2 mb-1 transition-colors ${
                    s.session_id === currentSession ? 'bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => loadSessionMessages(s.session_id)}
                  actions={[
                    <Tooltip title="删除会话">
                      <DeleteOutlined
                        className="text-gray-400 hover:text-red-500"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(s.session_id);
                        }}
                      />
                    </Tooltip>,
                  ]}
                >
                  <div className="overflow-hidden">
                    <div className="text-sm truncate font-medium text-gray-800">
                      {s.last_question || '新会话'}
                    </div>
                    <div className="text-xs text-gray-400">
                      {s.question_count} 条消息 · {new Date(s.updated_at).toLocaleString()}
                    </div>
                  </div>
                </List.Item>
              )}
            />
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="text-sm font-medium text-gray-700 mb-2">
            <FireOutlined className="text-orange-500 mr-1" />
            热门问题
          </div>
          <div className="space-y-1">
            {hotQuestions.map((q, i) => (
              <div
                key={i}
                className="text-xs text-gray-500 hover:text-blue-600 cursor-pointer truncate"
                onClick={() => setInput(q.question)}
              >
                {q.question}
                <Badge count={q.count} style={{ backgroundColor: '#1890ff', marginLeft: 6 }} />
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Chat Area */}
      <Card className="flex-1 flex flex-col shadow-sm" bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="px-6 py-3 border-b border-gray-100 flex items-center justify-between">
          <div>
            <span className="font-medium text-gray-800">
              {currentSession ? '当前会话' : '新会话'}
            </span>
            {currentSession && (
              <Tag className="ml-2 text-xs">{currentSession.slice(-8)}</Tag>
            )}
          </div>
          <Avatar icon={<UserOutlined />} size="small" /> {user?.nickname || user?.username}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <Empty
                description="开始提问吧"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
              >
                <Avatar
                  icon={m.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  className={m.role === 'ai' ? 'bg-gradient-to-br from-blue-500 to-indigo-600' : 'bg-gray-300'}
                />
                <div
                  className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-blue-500 text-white rounded-tr-none'
                      : 'bg-white shadow-sm border border-gray-100 rounded-tl-none'
                  }`}
                >
                  <div>{m.content}</div>
                  {m.role === 'ai' && (
                    <div className="mt-2 flex items-center gap-2">
                      {m.isRAG && (
                        <Tag color="blue" className="text-xs">RAG</Tag>
                      )}
                      {m.fromCache && (
                        <Tag color="green" className="text-xs">命中缓存</Tag>
                      )}
                      {m.recordId && (
                        <Space size="small">
                          <Tooltip title="有用">
                            <Button
                              type="text"
                              size="small"
                              icon={<LikeOutlined className={m.feedback === 1 ? 'text-blue-500' : ''} />}
                              onClick={() => submitFeedback(m.recordId!, 1)}
                            />
                          </Tooltip>
                          <Tooltip title="无用">
                            <Button
                              type="text"
                              size="small"
                              icon={<DislikeOutlined className={m.feedback === 2 ? 'text-red-500' : ''} />}
                              onClick={() => submitFeedback(m.recordId!, 2)}
                            />
                          </Tooltip>
                        </Space>
                      )}
                    </div>
                  )}
                  {m.sources && m.sources.length > 0 && (
                    <div className="mt-3 border-t border-gray-100 pt-2">
                      <div
                        className="flex items-center gap-1.5 cursor-pointer text-xs text-gray-500 hover:text-blue-600 transition-colors"
                        onClick={() => toggleSources(m.id)}
                      >
                        <PaperClipOutlined className="text-gray-400" />
                        <span>关于来源</span>
                        <Tag className="text-xs ml-0.5" color="default">{m.sources.length}</Tag>
                        <DownOutlined
                          className={`text-[10px] text-gray-400 transition-transform duration-200 ${
                            expandedSources.has(m.id) ? 'rotate-180' : ''
                          }`}
                        />
                      </div>
                      {expandedSources.has(m.id) && (
                        <div className="mt-2 space-y-2">
                          {m.sources.map((src: any, i: number) => (
                            <div key={i} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                              <div className="text-sm font-medium text-gray-800 truncate">{src.title}</div>
                              <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                                {src.content_preview
                                  ? src.content_preview.length > 100
                                    ? src.content_preview.substring(0, 100) + '...'
                                    : src.content_preview
                                  : ''}
                              </div>
                              {src.score !== undefined && (
                                <Tag
                                  color={src.score > 0.7 ? 'success' : src.score > 0.5 ? 'warning' : 'default'}
                                  className="mt-2 text-xs"
                                >
                                  {(src.score * 100).toFixed(1)}%
                                </Tag>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-3">
              <Avatar icon={<RobotOutlined />} className="bg-gradient-to-br from-blue-500 to-indigo-600" />
              <div className="bg-white shadow-sm border border-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
                <Spin size="small" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-100 bg-white">
          <div className="flex gap-3">
            <Input.TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入关于河海大学的问题，例如：河海大学是哪一年创办的？"
              autoSize={{ minRows: 1, maxRows: 4 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              className="flex-1"
            />
            <Button
              type={isRagMode ? 'primary' : 'default'}
              icon={<PaperClipOutlined />}
              onClick={() => setIsRagMode(!isRagMode)}
              className={isRagMode ? 'bg-gradient-to-r from-green-500 to-teal-600 border-0 text-white' : ''}
            >
              {isRagMode ? 'RAG已开启' : 'RAG问答'}
            </Button>
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={loading}
              onClick={sendMessage}
              className="bg-gradient-to-r from-blue-500 to-indigo-600 h-auto"
            >
              发送
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
