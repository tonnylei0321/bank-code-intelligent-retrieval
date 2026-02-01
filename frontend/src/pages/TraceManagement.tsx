/**
 * 全链追踪页面
 * 
 * 功能：
 * - 请求链路追踪
 * - 性能监控
 * - 错误追踪
 * - 调用链分析
 * - 实时监控面板
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Timeline,
  Statistic,
  Row,
  Col,
  Modal,
  Input,
  Select,
  DatePicker,
  Alert,
  Tabs,
  List,
  Typography,
  Divider,
  Tooltip,
  Progress,
  Badge,
  Tree,
  message,
} from 'antd';
import {
  AuditOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  ReloadOutlined,
  BarChartOutlined,
  LineChartOutlined,
  ApiOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  BugOutlined,
  MonitorOutlined,
  EyeOutlined,
} from '@ant-design/icons';

const { TabPane } = Tabs;
const { Text, Title } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface TraceRecord {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  operation_name: string;
  service_name: string;
  start_time: string;
  duration: number;
  status: 'success' | 'error' | 'timeout';
  tags: Record<string, any>;
  logs: any[];
  http_method?: string;
  http_url?: string;
  http_status_code?: number;
  error_message?: string;
}

interface ServiceMetrics {
  service_name: string;
  request_count: number;
  error_count: number;
  avg_duration: number;
  p95_duration: number;
  p99_duration: number;
  error_rate: number;
}

interface ErrorRecord {
  id: string;
  service_name: string;
  operation_name: string;
  error_type: string;
  error_message: string;
  stack_trace: string;
  count: number;
  first_seen: string;
  last_seen: string;
}

const TraceManagement: React.FC = () => {
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [serviceMetrics, setServiceMetrics] = useState<ServiceMetrics[]>([]);
  const [errors, setErrors] = useState<ErrorRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState<TraceRecord | null>(null);
  const [traceModalVisible, setTraceModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('traces');
  const [searchForm, setSearchForm] = useState({
    service: '',
    operation: '',
    status: '',
    timeRange: null as any,
  });

  // 获取追踪数据
  const fetchTraces = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      const mockTraces: TraceRecord[] = [
        {
          trace_id: 'trace-001',
          span_id: 'span-001',
          operation_name: 'POST /api/intelligent-qa/ask',
          service_name: 'intelligent-qa-service',
          start_time: '2024-02-01T10:30:00Z',
          duration: 1250,
          status: 'success',
          tags: {
            'http.method': 'POST',
            'http.url': '/api/intelligent-qa/ask',
            'user.id': '123',
            'model.type': 'gpt-3.5-turbo',
          },
          logs: [
            { timestamp: '2024-02-01T10:30:00.100Z', message: 'Request received' },
            { timestamp: '2024-02-01T10:30:00.500Z', message: 'Model analysis started' },
            { timestamp: '2024-02-01T10:30:01.200Z', message: 'Response generated' },
          ],
          http_method: 'POST',
          http_url: '/api/intelligent-qa/ask',
          http_status_code: 200,
        },
        {
          trace_id: 'trace-002',
          span_id: 'span-002',
          operation_name: 'Redis Query',
          service_name: 'redis-service',
          start_time: '2024-02-01T10:30:00.200Z',
          duration: 45,
          status: 'success',
          tags: {
            'db.type': 'redis',
            'db.operation': 'search',
            'cache.hit': true,
          },
          logs: [
            { timestamp: '2024-02-01T10:30:00.200Z', message: 'Redis query started' },
            { timestamp: '2024-02-01T10:30:00.245Z', message: 'Cache hit, returning data' },
          ],
        },
        {
          trace_id: 'trace-003',
          span_id: 'span-003',
          operation_name: 'Model Inference',
          service_name: 'model-service',
          start_time: '2024-02-01T10:29:30Z',
          duration: 3500,
          status: 'error',
          tags: {
            'model.name': 'gpt-4',
            'error.type': 'timeout',
          },
          logs: [
            { timestamp: '2024-02-01T10:29:30.000Z', message: 'Model inference started' },
            { timestamp: '2024-02-01T10:29:33.500Z', message: 'Request timeout' },
          ],
          error_message: 'Model inference timeout after 3.5 seconds',
        },
      ];
      setTraces(mockTraces);
    } catch (error) {
      console.error('获取追踪数据失败:', error);
      message.error('获取追踪数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取服务指标
  const fetchServiceMetrics = async () => {
    try {
      // 模拟API调用
      const mockMetrics: ServiceMetrics[] = [
        {
          service_name: 'intelligent-qa-service',
          request_count: 1250,
          error_count: 15,
          avg_duration: 850,
          p95_duration: 2100,
          p99_duration: 3200,
          error_rate: 1.2,
        },
        {
          service_name: 'redis-service',
          request_count: 3200,
          error_count: 5,
          avg_duration: 25,
          p95_duration: 45,
          p99_duration: 80,
          error_rate: 0.16,
        },
        {
          service_name: 'model-service',
          request_count: 890,
          error_count: 45,
          avg_duration: 1200,
          p95_duration: 2800,
          p99_duration: 4500,
          error_rate: 5.06,
        },
        {
          service_name: 'training-service',
          request_count: 156,
          error_count: 8,
          avg_duration: 15000,
          p95_duration: 45000,
          p99_duration: 120000,
          error_rate: 5.13,
        },
      ];
      setServiceMetrics(mockMetrics);
    } catch (error) {
      console.error('获取服务指标失败:', error);
    }
  };

  // 获取错误记录
  const fetchErrors = async () => {
    try {
      // 模拟API调用
      const mockErrors: ErrorRecord[] = [
        {
          id: 'error-001',
          service_name: 'model-service',
          operation_name: 'Model Inference',
          error_type: 'TimeoutError',
          error_message: 'Model inference timeout after 3.5 seconds',
          stack_trace: 'TimeoutError: Model inference timeout\n  at ModelService.infer()',
          count: 12,
          first_seen: '2024-02-01T08:00:00Z',
          last_seen: '2024-02-01T10:29:30Z',
        },
        {
          id: 'error-002',
          service_name: 'intelligent-qa-service',
          operation_name: 'Question Analysis',
          error_type: 'ValidationError',
          error_message: 'Invalid question format',
          stack_trace: 'ValidationError: Invalid question format\n  at QuestionValidator.validate()',
          count: 8,
          first_seen: '2024-02-01T09:15:00Z',
          last_seen: '2024-02-01T10:20:00Z',
        },
      ];
      setErrors(mockErrors);
    } catch (error) {
      console.error('获取错误记录失败:', error);
    }
  };

  // 查看追踪详情
  const handleViewTrace = (trace: TraceRecord) => {
    setSelectedTrace(trace);
    setTraceModalVisible(true);
  };

  useEffect(() => {
    fetchTraces();
    fetchServiceMetrics();
    fetchErrors();
    
    // 设置定时刷新
    const interval = setInterval(() => {
      fetchTraces();
      fetchServiceMetrics();
    }, 30000); // 每30秒刷新一次
    
    return () => clearInterval(interval);
  }, []);

  // 追踪记录表格列
  const traceColumns = [
    {
      title: '追踪ID',
      dataIndex: 'trace_id',
      key: 'trace_id',
      width: 120,
      render: (id: string) => (
        <Text code style={{ fontSize: 12 }}>
          {id.substring(0, 8)}...
        </Text>
      ),
    },
    {
      title: '服务/操作',
      key: 'service_operation',
      render: (_, record: TraceRecord) => (
        <div>
          <Tag color="blue">{record.service_name}</Tag>
          <br />
          <Text style={{ fontSize: 12 }}>{record.operation_name}</Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          'success': { color: 'success', icon: <CheckCircleOutlined />, text: '成功' },
          'error': { color: 'error', icon: <ExclamationCircleOutlined />, text: '错误' },
          'timeout': { color: 'warning', icon: <ClockCircleOutlined />, text: '超时' },
        };
        const config = statusConfig[status as keyof typeof statusConfig];
        return (
          <Badge
            status={config.color as any}
            text={
              <Space>
                {config.icon}
                {config.text}
              </Space>
            }
          />
        );
      },
    },
    {
      title: '耗时',
      dataIndex: 'duration',
      key: 'duration',
      width: 100,
      render: (duration: number) => (
        <div>
          <Text>{duration}ms</Text>
          <br />
          <Progress
            percent={Math.min((duration / 5000) * 100, 100)}
            size="small"
            showInfo={false}
            status={duration > 3000 ? 'exception' : duration > 1000 ? 'normal' : 'success'}
          />
        </div>
      ),
    },
    {
      title: 'HTTP信息',
      key: 'http_info',
      width: 150,
      render: (_, record: TraceRecord) => (
        <div>
          {record.http_method && (
            <Tag color="green">{record.http_method}</Tag>
          )}
          {record.http_status_code && (
            <Tag color={record.http_status_code < 400 ? 'blue' : 'red'}>
              {record.http_status_code}
            </Tag>
          )}
          {record.http_url && (
            <div>
              <Text style={{ fontSize: 11 }} ellipsis>
                {record.http_url}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record: TraceRecord) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewTrace(record)}
        >
          详情
        </Button>
      ),
    },
  ];

  // 服务指标表格列
  const metricsColumns = [
    {
      title: '服务名称',
      dataIndex: 'service_name',
      key: 'service_name',
      render: (name: string) => (
        <Tag color="blue" icon={<ApiOutlined />}>
          {name}
        </Tag>
      ),
    },
    {
      title: '请求数',
      dataIndex: 'request_count',
      key: 'request_count',
      width: 100,
      render: (count: number) => (
        <Statistic value={count} valueStyle={{ fontSize: 14 }} />
      ),
    },
    {
      title: '错误率',
      key: 'error_rate',
      width: 120,
      render: (_, record: ServiceMetrics) => (
        <div>
          <Text>{record.error_rate.toFixed(2)}%</Text>
          <br />
          <Progress
            percent={Math.min(record.error_rate * 10, 100)}
            size="small"
            showInfo={false}
            status={record.error_rate > 5 ? 'exception' : record.error_rate > 1 ? 'normal' : 'success'}
          />
        </div>
      ),
    },
    {
      title: '平均耗时',
      dataIndex: 'avg_duration',
      key: 'avg_duration',
      width: 100,
      render: (duration: number) => `${duration}ms`,
    },
    {
      title: 'P95耗时',
      dataIndex: 'p95_duration',
      key: 'p95_duration',
      width: 100,
      render: (duration: number) => `${duration}ms`,
    },
    {
      title: 'P99耗时',
      dataIndex: 'p99_duration',
      key: 'p99_duration',
      width: 100,
      render: (duration: number) => `${duration}ms`,
    },
  ];

  // 错误记录表格列
  const errorColumns = [
    {
      title: '服务/操作',
      key: 'service_operation',
      render: (_, record: ErrorRecord) => (
        <div>
          <Tag color="red">{record.service_name}</Tag>
          <br />
          <Text style={{ fontSize: 12 }}>{record.operation_name}</Text>
        </div>
      ),
    },
    {
      title: '错误类型',
      dataIndex: 'error_type',
      key: 'error_type',
      width: 120,
      render: (type: string) => (
        <Tag color="orange" icon={<BugOutlined />}>
          {type}
        </Tag>
      ),
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
    },
    {
      title: '出现次数',
      dataIndex: 'count',
      key: 'count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#f50' }} />
      ),
    },
    {
      title: '首次/最后出现',
      key: 'occurrence',
      width: 180,
      render: (_, record: ErrorRecord) => (
        <div>
          <Text style={{ fontSize: 12 }}>
            首次: {new Date(record.first_seen).toLocaleString('zh-CN')}
          </Text>
          <br />
          <Text style={{ fontSize: 12 }}>
            最后: {new Date(record.last_seen).toLocaleString('zh-CN')}
          </Text>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_, record: ErrorRecord) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => {
            Modal.info({
              title: '错误详情',
              content: (
                <div>
                  <p><strong>错误类型:</strong> {record.error_type}</p>
                  <p><strong>错误信息:</strong> {record.error_message}</p>
                  <p><strong>堆栈跟踪:</strong></p>
                  <pre style={{ background: '#f5f5f5', padding: 8, fontSize: 12 }}>
                    {record.stack_trace}
                  </pre>
                </div>
              ),
              width: 800,
            });
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1>全链追踪</h1>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchTraces}>
            刷新
          </Button>
          <Button icon={<MonitorOutlined />}>
            实时监控
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总请求数"
              value={serviceMetrics.reduce((sum, m) => sum + m.request_count, 0)}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总错误数"
              value={serviceMetrics.reduce((sum, m) => sum + m.error_count, 0)}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均响应时间"
              value={Math.round(serviceMetrics.reduce((sum, m) => sum + m.avg_duration, 0) / serviceMetrics.length)}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃服务"
              value={serviceMetrics.length}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 搜索栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Select
              placeholder="选择服务"
              style={{ width: '100%' }}
              value={searchForm.service}
              onChange={(value) => setSearchForm({ ...searchForm, service: value })}
              allowClear
            >
              <Option value="intelligent-qa-service">智能问答服务</Option>
              <Option value="redis-service">Redis服务</Option>
              <Option value="model-service">模型服务</Option>
              <Option value="training-service">训练服务</Option>
            </Select>
          </Col>
          <Col span={6}>
            <Input
              placeholder="操作名称"
              value={searchForm.operation}
              onChange={(e) => setSearchForm({ ...searchForm, operation: e.target.value })}
              allowClear
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="状态"
              style={{ width: '100%' }}
              value={searchForm.status}
              onChange={(value) => setSearchForm({ ...searchForm, status: value })}
              allowClear
            >
              <Option value="success">成功</Option>
              <Option value="error">错误</Option>
              <Option value="timeout">超时</Option>
            </Select>
          </Col>
          <Col span={6}>
            <RangePicker
              style={{ width: '100%' }}
              showTime
              value={searchForm.timeRange}
              onChange={(dates) => setSearchForm({ ...searchForm, timeRange: dates })}
            />
          </Col>
        </Row>
        <Row style={{ marginTop: 16 }}>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />}>
                搜索
              </Button>
              <Button onClick={() => setSearchForm({ service: '', operation: '', status: '', timeRange: null })}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="追踪记录" key="traces">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="追踪记录"
                description="显示所有请求的追踪信息，包括调用链路、耗时和状态。点击详情可查看完整的调用链。"
                type="info"
                showIcon
              />
            </div>
            
            <Table
              columns={traceColumns}
              dataSource={traces}
              loading={loading}
              rowKey="trace_id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条追踪记录`,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="服务指标" key="metrics">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="服务性能指标"
                description="显示各个服务的性能指标，包括请求数、错误率、响应时间等。"
                type="info"
                showIcon
              />
            </div>
            
            <Table
              columns={metricsColumns}
              dataSource={serviceMetrics}
              loading={loading}
              rowKey="service_name"
              pagination={false}
            />
          </Card>
        </TabPane>

        <TabPane tab="错误分析" key="errors">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="错误分析"
                description="显示系统中出现的错误，包括错误类型、出现频率和详细信息。"
                type="error"
                showIcon
              />
            </div>
            
            <Table
              columns={errorColumns}
              dataSource={errors}
              loading={loading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个错误类型`,
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 追踪详情模态框 */}
      <Modal
        title={`追踪详情: ${selectedTrace?.trace_id}`}
        visible={traceModalVisible}
        onCancel={() => setTraceModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setTraceModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        {selectedTrace && (
          <div>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={8}>
                <Statistic
                  title="总耗时"
                  value={selectedTrace.duration}
                  suffix="ms"
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="状态"
                  value={selectedTrace.status}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="Span数量"
                  value={1}
                />
              </Col>
            </Row>

            <Divider />

            <Title level={5}>标签信息</Title>
            <div style={{ marginBottom: 16 }}>
              {Object.entries(selectedTrace.tags).map(([key, value]) => (
                <Tag key={key} style={{ margin: 4 }}>
                  {key}: {String(value)}
                </Tag>
              ))}
            </div>

            <Title level={5}>执行日志</Title>
            <Timeline>
              {selectedTrace.logs.map((log, index) => (
                <Timeline.Item key={index}>
                  <div>
                    <Text strong>{new Date(log.timestamp).toLocaleTimeString('zh-CN')}</Text>
                    <br />
                    <Text>{log.message}</Text>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>

            {selectedTrace.error_message && (
              <div>
                <Title level={5}>错误信息</Title>
                <Alert
                  message="执行错误"
                  description={selectedTrace.error_message}
                  type="error"
                  showIcon
                />
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default TraceManagement;