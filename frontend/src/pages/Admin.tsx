import { useState, useEffect } from 'react';
import { Card, Statistic, Button, Row, Col, message, Table, Tag, Input, Badge } from 'antd';
import { DeleteOutlined, ReloadOutlined, FireOutlined, DatabaseOutlined, ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';
import api from '../services/api';

export default function Admin() {
  const [stats, setStats] = useState<any>({});
  const [keys, setKeys] = useState<any[]>([]);
  const [keyPattern, setKeyPattern] = useState('campus:qa:*');
  const [warmupLimit, setWarmupLimit] = useState(10);

  useEffect(() => { loadCacheData(); const timer = setInterval(loadCacheData, 5000); return () => clearInterval(timer); }, []);

  const loadCacheData = async () => {
    try {
      const s: any = await api.get('/admin/cache/stats'); if (s.code === 200) setStats(s.data);
      const k: any = await api.get(`/admin/cache/keys?pattern=${keyPattern}`); if (k.code === 200) setKeys(k.data.keys || []);
    } catch (e) {}
  };

  const clearCache = async (type: string) => {
    const paths: Record<string, string> = { all: '/admin/cache/clear', qa: '/admin/cache/clear/qa', sessions: '/admin/cache/clear/sessions', hot: '/admin/cache/clear/hot' };
    try { const r: any = await api.delete(paths[type]); message.success(r.message); loadCacheData(); } catch (e) {}
  };

  return (
    <div>
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={12} sm={6}><Card size="small"><Statistic title="总 Keys" value={stats.total_keys || 0} prefix={<DatabaseOutlined />} /><div className="text-xs text-gray-400">命中: {stats.hit_ratio !== 'N/A' ? `${stats.hit_ratio}%` : '-'}</div></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="Q&A 缓存" value={stats.keys_by_prefix?.['Q&A 缓存']?.count || 0} prefix={<ThunderboltOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="会话缓存" value={stats.keys_by_prefix?.['会话缓存']?.count || 0} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="内存" value={stats.memory_human || '-'} prefix={<DatabaseOutlined />} /><div className="text-xs text-gray-400">{stats.server_type === 'real' ? <Badge status="success" text="Redis" /> : <Badge status="warning" text="Fake" />}</div></Card></Col>
      </Row>
      <div className="mb-4 flex flex-wrap gap-2">
        <Button danger icon={<DeleteOutlined />} onClick={() => clearCache('all')}>清空全部</Button>
        <Button icon={<DeleteOutlined />} onClick={() => clearCache('qa')}>清空 Q&A</Button>
        <Button icon={<DeleteOutlined />} onClick={() => clearCache('sessions')}>清空会话</Button>
        <Button icon={<ReloadOutlined />} onClick={() => clearCache('hot')}>重置热门</Button>
        <Button type="primary" icon={<ReloadOutlined />} onClick={loadCacheData}>刷新</Button>
      </div>
      <div className="mb-4 flex items-center gap-2">
        <Input type="number" value={warmupLimit} onChange={(e) => setWarmupLimit(Number(e.target.value))} style={{ width: 80 }} min={1} />
        <Button icon={<FireOutlined />} onClick={async () => { try { const r: any = await api.post(`/admin/cache/warmup?limit=${warmupLimit}`); message.success(r.message); } catch (e) {} }}>预热热门</Button>
      </div>
      <div className="mb-2 flex items-center gap-2">
        <Input value={keyPattern} onChange={(e) => setKeyPattern(e.target.value)} style={{ width: 200 }} onPressEnter={loadCacheData} />
        <Button onClick={loadCacheData}>查询</Button>
      </div>
      <Table rowKey="key" dataSource={keys} size="small" pagination={false}
        columns={[
          { title: 'Key', dataIndex: 'key', ellipsis: true },
          { title: 'Type', dataIndex: 'type', width: 80, render: (t: string) => { const c: Record<string,string>={string:'green',zset:'purple',list:'blue',hash:'orange'}; return <Tag color={c[t]||'default'}>{t}</Tag> } },
          { title: 'TTL', dataIndex: 'ttl', width: 80, render: (t: number) => t >= 0 ? t : '-' },
        ]}
      />
    </div>
  );
}
