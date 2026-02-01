import React, { useState, useEffect } from 'react';
import { Card, Form, Select, InputNumber, Button, Progress, Table, message, Modal, Space, Tag, Divider, Row, Col, Input, Checkbox } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { useAppSelector } from '../hooks/redux';

const { Option } = Select;
const { TextArea } = Input;

interface GenerationStrategy {
  value: string;
  label: string;
  description: string;
}

interface GenerationTask {
  task_id: string;
  dataset_id: number;
  status: string;
  progress: number;
  created_at: string;
  generated_samples: number;
}

interface TaskStatus {
  task_id: string;
  status: string;
  progress: number;
  current_step: string;
  processed_count: number;
  total_count: number;
  generated_samples: number;
  error_count: number;
  start_time: string;
  estimated_completion?: string;
  logs: string[];
}

const SampleGeneration: React.FC = () => {
  const [form] = Form.useForm();
  const { token } = useAppSelector((state) => state.auth);
  
  // 状态管理
  const [datasets, setDatasets] = useState<any[]>([]);
  const [strategies, setStrategies] = useState<{
    selection_strategies: GenerationStrategy[];
    record_count_strategies: GenerationStrategy[];
    llm_strategies: GenerationStrategy[];
  }>({
    selection_strategies: [],
    record_count_strategies: [],
    llm_strategies: []
  });
  
  const [tasks, setTasks] = useState<GenerationTask[]>([]);
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [logModalVisible, setLogModalVisible] = useState(false);
  
  // 表单状态
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [recordCountStrategy, setRecordCountStrategy] = useState<string>('all');
  const [selectionStrategy, setSelectionStrategy] = useState<string>('all');

  useEffect(() => {
    loadInitialData();
    loadTasks();
    
    // 设置定时器更新任务状态
    const interval = setInterval(() => {
      loadTasks();
      if (currentTask && ['running', 'pending'].includes(currentTask.status)) {
        loadTaskStatus(currentTask.task_id);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);

  const loadInitialData = async () => {
    try {
      // 加载数据集
      const datasetsResponse = await fetch('/api/v1/datasets/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const datasetsData = await datasetsResponse.json();
      setDatasets(datasetsData);

      // 加载生成策略
      const strategiesResponse = await fetch('/api/sample-generation/strategies', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const strategiesData = await strategiesResponse.json();
      setStrategies(strategiesData);
      
    } catch (error) {
      message.error('加载数据失败');
    }
  };

  const loadTasks = async () => {
    try {
      const response = await fetch('/api/sample-generation/tasks', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setTasks(data.tasks || []);
    } catch (error) {
      console.error('加载任务列表失败:', error);
    }
  };

  const loadTaskStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/sample-generation/status/${taskId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setCurrentTask(data);
    } catch (error) {
      console.error('加载任务状态失败:', error);
    }
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    
    try {
      const requestData = {
        dataset_id: values.dataset_id,
        selection_strategy: values.selection_strategy,
        selection_filters: values.selection_filters || {},
        record_count_strategy: values.record_count_strategy,
        custom_count: values.custom_count,
        percentage: values.percentage,
        llm_strategies: values.llm_strategies,
        questions_per_record: values.questions_per_record || 3,
        model_type: values.model_type || 'local',
        temperature: values.temperature || 0.7,
        max_tokens: values.max_tokens || 512,
        task_name: values.task_name,
        description: values.description
      };

      const response = await fetch('/api/sample-generation/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestData)
      });

      if (response.ok) {
        const result = await response.json();
        message.success('样本生成任务已启动');
        form.resetFields();
        loadTasks();
        
        // 开始监控任务
        setCurrentTask({
          task_id: result.task_id,
          status: 'pending',
          progress: 0,
          current_step: '准备中...',
          processed_count: 0,
          total_count: result.estimated_total,
          generated_samples: 0,
          error_count: 0,
          start_time: result.created_at,
          logs: []
        });
        setModalVisible(true);
        
      } else {
        const error = await response.json();
        message.error(`启动失败: ${error.detail}`);
      }
    } catch (error) {
      message.error('启动任务失败');
    } finally {
      setLoading(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await fetch(`/api/sample-generation/tasks/${taskId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      message.success('任务已取消');
      loadTasks();
      if (currentTask?.task_id === taskId) {
        setCurrentTask(null);
        setModalVisible(false);
      }
    } catch (error) {
      message.error('取消任务失败');
    }
  };

  const getStatusColor = (status: string) => {
    const colors = {
      'pending': 'orange',
      'running': 'blue',
      'completed': 'green',
      'failed': 'red',
      'cancelled': 'gray'
    };
    return colors[status as keyof typeof colors] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts = {
      'pending': '等待中',
      'running': '运行中',
      'completed': '已完成',
      'failed': '失败',
      'cancelled': '已取消'
    };
    return texts[status as keyof typeof texts] || status;
  };

  const taskColumns = [
    {
      title: '任务ID',
      dataIndex: 'task_id',
      key: 'task_id',
      width: 120,
      render: (text: string) => text.substring(0, 8) + '...'
    },
    {
      title: '数据集',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      render: (id: number) => {
        const dataset = datasets.find(d => d.id === id);
        return dataset?.filename || `数据集 ${id}`;
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      )
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number) => (
        <Progress percent={Math.round(progress)} size="small" />
      )
    },
    {
      title: '生成样本数',
      dataIndex: 'generated_samples',
      key: 'generated_samples'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: GenerationTask) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              loadTaskStatus(record.task_id);
              setModalVisible(true);
            }}
          >
            查看
          </Button>
          {['running', 'pending'].includes(record.status) && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => cancelTask(record.task_id)}
            >
              取消
            </Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <div className="glass-container">
      <div className="f-pattern-header">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">样本数据生成</h1>
        <p className="text-gray-600">配置生成策略，自动生成高质量的训练样本数据</p>
      </div>

      <Row gutter={24}>
        <Col span={16}>
          <Card title="生成配置" className="glass-card mb-6">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                record_count_strategy: 'all',
                selection_strategy: 'all',
                questions_per_record: 3,
                temperature: 0.7,
                max_tokens: 512,
                model_type: 'local'
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="dataset_id"
                    label="选择数据集"
                    rules={[{ required: true, message: '请选择数据集' }]}
                  >
                    <Select placeholder="选择要生成样本的数据集">
                      {datasets.map(dataset => (
                        <Option key={dataset.id} value={dataset.id}>
                          {dataset.filename} ({dataset.valid_records} 条记录)
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="task_name"
                    label="任务名称"
                    rules={[{ required: true, message: '请输入任务名称' }]}
                  >
                    <Input placeholder="为此次生成任务命名" />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">样本挑选策略</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="selection_strategy"
                    label="挑选策略"
                    rules={[{ required: true, message: '请选择挑选策略' }]}
                  >
                    <Select 
                      placeholder="选择样本挑选策略"
                      onChange={setSelectionStrategy}
                    >
                      {strategies.selection_strategies.map(strategy => (
                        <Option key={strategy.value} value={strategy.value}>
                          <div>
                            <div>{strategy.label}</div>
                            <div className="text-xs text-gray-500">{strategy.description}</div>
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="record_count_strategy"
                    label="记录数策略"
                    rules={[{ required: true, message: '请选择记录数策略' }]}
                  >
                    <Select 
                      placeholder="选择记录数策略"
                      onChange={setRecordCountStrategy}
                    >
                      {strategies.record_count_strategies.map(strategy => (
                        <Option key={strategy.value} value={strategy.value}>
                          <div>
                            <div>{strategy.label}</div>
                            <div className="text-xs text-gray-500">{strategy.description}</div>
                          </div>
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              {recordCountStrategy === 'custom' && (
                <Form.Item
                  name="custom_count"
                  label="自定义记录数"
                  rules={[{ required: true, message: '请输入记录数' }]}
                >
                  <InputNumber min={1} placeholder="输入要处理的记录数" style={{ width: '100%' }} />
                </Form.Item>
              )}

              {recordCountStrategy === 'percentage' && (
                <Form.Item
                  name="percentage"
                  label="百分比"
                  rules={[{ required: true, message: '请输入百分比' }]}
                >
                  <InputNumber min={1} max={100} placeholder="输入百分比 (1-100)" style={{ width: '100%' }} />
                </Form.Item>
              )}

              <Divider orientation="left">LLM生成策略</Divider>

              <Form.Item
                name="llm_strategies"
                label="生成策略"
                rules={[{ required: true, message: '请选择至少一种生成策略' }]}
              >
                <Checkbox.Group onChange={setSelectedStrategies}>
                  <Row gutter={[16, 16]}>
                    {strategies.llm_strategies.map(strategy => (
                      <Col span={12} key={strategy.value}>
                        <Checkbox value={strategy.value}>
                          <div>
                            <div className="font-medium">{strategy.label}</div>
                            <div className="text-xs text-gray-500">{strategy.description}</div>
                          </div>
                        </Checkbox>
                      </Col>
                    ))}
                  </Row>
                </Checkbox.Group>
              </Form.Item>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="questions_per_record"
                    label="每条记录生成问题数"
                  >
                    <InputNumber min={1} max={10} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="temperature"
                    label="生成温度"
                  >
                    <InputNumber min={0} max={2} step={0.1} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="max_tokens"
                    label="最大Token数"
                  >
                    <InputNumber min={100} max={2048} />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="description"
                label="任务描述"
              >
                <TextArea rows={3} placeholder="描述此次生成任务的目的和要求（可选）" />
              </Form.Item>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={loading}
                  size="large"
                  icon={<PlayCircleOutlined />}
                >
                  开始生成样本
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col span={8}>
          <Card title="策略说明" className="glass-card mb-6">
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900">挑选策略</h4>
                <ul className="text-sm text-gray-600 mt-1 space-y-1">
                  <li>• <strong>按银行</strong>：根据银行名称分组</li>
                  <li>• <strong>按省行</strong>：根据省份分组</li>
                  <li>• <strong>按支行</strong>：根据支行关键词</li>
                  <li>• <strong>随机挑选</strong>：随机选择样本</li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900">生成策略</h4>
                <ul className="text-sm text-gray-600 mt-1 space-y-1">
                  <li>• <strong>自然语言</strong>：流畅的日常问答</li>
                  <li>• <strong>结构化</strong>：格式规范的问答</li>
                  <li>• <strong>多轮对话</strong>：连续对话样本</li>
                  <li>• <strong>场景化</strong>：业务场景问答</li>
                </ul>
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="任务列表" className="glass-card" extra={
        <Button icon={<ReloadOutlined />} onClick={loadTasks}>
          刷新
        </Button>
      }>
        <Table
          columns={taskColumns}
          dataSource={tasks}
          rowKey="task_id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 任务进度监控弹窗 */}
      <Modal
        title="任务执行监控"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="logs" onClick={() => setLogModalVisible(true)}>
            查看日志
          </Button>,
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {currentTask && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span>任务状态：</span>
              <Tag color={getStatusColor(currentTask.status)}>
                {getStatusText(currentTask.status)}
              </Tag>
            </div>
            
            <div>
              <div className="flex justify-between mb-2">
                <span>总体进度：</span>
                <span>{Math.round(currentTask.progress)}%</span>
              </div>
              <Progress 
                percent={Math.round(currentTask.progress)} 
                status={currentTask.status === 'failed' ? 'exception' : 'active'}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-600">当前步骤：</span>
                <div className="font-medium">{currentTask.current_step}</div>
              </div>
              <div>
                <span className="text-gray-600">处理进度：</span>
                <div className="font-medium">
                  {currentTask.processed_count} / {currentTask.total_count}
                </div>
              </div>
              <div>
                <span className="text-gray-600">生成样本：</span>
                <div className="font-medium text-green-600">
                  {currentTask.generated_samples}
                </div>
              </div>
              <div>
                <span className="text-gray-600">错误数量：</span>
                <div className="font-medium text-red-600">
                  {currentTask.error_count}
                </div>
              </div>
            </div>
            
            {currentTask.estimated_completion && (
              <div>
                <span className="text-gray-600">预计完成：</span>
                <span className="font-medium">
                  {new Date(currentTask.estimated_completion).toLocaleString()}
                </span>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 日志查看弹窗 */}
      <Modal
        title="执行日志"
        open={logModalVisible}
        onCancel={() => setLogModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setLogModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        <div className="bg-gray-900 text-green-400 p-4 rounded font-mono text-sm max-h-96 overflow-y-auto">
          {currentTask?.logs.map((log, index) => (
            <div key={index} className="mb-1">
              {log}
            </div>
          ))}
        </div>
      </Modal>
    </div>
  );
};

export default SampleGeneration;