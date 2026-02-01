import React, { useState, useEffect } from 'react';
import { Card, Form, Select, InputNumber, Button, Progress, Table, message, Modal, Space, Tag, Divider, Row, Col, Input, Checkbox, Tabs, Radio } from 'antd';
import { PlayCircleOutlined, EyeOutlined, ReloadOutlined, BarChartOutlined, SettingOutlined, UnorderedListOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

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
  start_time: string;  // 改为start_time
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

interface SampleGenerationTabProps {
  datasets: any[];
  onRefresh: () => void;
}

interface GenerationHistory {
  id: string;
  dataset_id: number;
  dataset_name: string;
  generated_count: number;
  train_count: number;
  val_count: number;
  test_count: number;
  llm_provider: string;
  question_types: string[];
  created_at: string;
  status: 'success' | 'failed';
  error_message?: string;
}

const SampleGenerationTab: React.FC<SampleGenerationTabProps> = ({ datasets, onRefresh }) => {
  const [form] = Form.useForm();
  const token = localStorage.getItem('access_token');
  
  // 状态管理
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
  const [generationHistory, setGenerationHistory] = useState<GenerationHistory[]>([]);
  const [currentTask, setCurrentTask] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [logModalVisible, setLogModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState<string>('config');
  
  // 表单状态
  const [recordCountStrategy, setRecordCountStrategy] = useState<string>('all');
  
  // 轮询定时器
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadStrategies();
    loadGenerationHistory();
    loadServerTasks();
    
    // 清理轮询
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, []);
  
  // 开始轮询任务状态
  const startPolling = (taskId: string) => {
    // 清除旧的轮询
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    // 每2秒轮询一次
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/sample-generation/status/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
          const status = await response.json();
          
          // 更新任务列表中的任务状态
          setTasks(prevTasks => 
            prevTasks.map(t => 
              t.task_id === taskId 
                ? {
                    ...t,
                    status: status.status,
                    progress: status.progress,
                    generated_samples: status.generated_samples
                  }
                : t
            )
          );
          
          // 如果任务完成或失败，停止轮询
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(interval);
            setPollingInterval(null);
            
            // 刷新任务列表
            loadServerTasks();
            
            // 如果成功，保存到历史记录
            if (status.status === 'completed' && status.result) {
              const dataset = datasets.find(d => d.id === status.result.dataset_id);
              const historyRecord: GenerationHistory = {
                id: taskId,
                dataset_id: status.result.dataset_id || 0,
                dataset_name: dataset?.filename || '未知数据集',
                generated_count: status.result.total_generated || 0,
                train_count: status.result.train_count || 0,
                val_count: status.result.val_count || 0,
                test_count: status.result.test_count || 0,
                llm_provider: 'qwen',
                question_types: [],
                created_at: status.start_time,
                status: 'success'
              };
              saveGenerationHistory(historyRecord);
              
              message.success(`样本生成完成！生成了 ${status.result.total_generated} 个样本`);
              onRefresh();
            } else if (status.status === 'failed') {
              message.error(`样本生成失败: ${status.error_message || '未知错误'}`);
            }
          }
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error);
      }
    }, 2000);
    
    setPollingInterval(interval);
  };

  const loadServerTasks = async () => {
    try {
      const response = await fetch('/api/v1/sample-generation/tasks', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setTasks(data.tasks || []);
      }
    } catch (error) {
      console.error('加载任务列表失败:', error);
    }
  };

  const loadGenerationHistory = () => {
    // 从localStorage加载生成历史
    const history = localStorage.getItem('sample_generation_history');
    if (history) {
      try {
        const parsed = JSON.parse(history);
        setGenerationHistory(parsed);
      } catch (e) {
        console.error('Failed to parse generation history:', e);
      }
    }
  };

  const saveGenerationHistory = (record: GenerationHistory) => {
    const history = [...generationHistory, record];
    // 只保留最近50条记录
    const trimmed = history.slice(-50);
    setGenerationHistory(trimmed);
    localStorage.setItem('sample_generation_history', JSON.stringify(trimmed));
  };

  const loadStrategies = async () => {
    try {
      const response = await fetch('/api/v1/qa-pairs/strategies', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setStrategies(data);
      } else {
        // 如果API不存在，使用默认策略
        setStrategies({
          selection_strategies: [
            { value: 'all', label: '全部数据', description: '使用所有可用数据' },
            { value: 'by_bank', label: '按银行挑选', description: '根据银行名称分组挑选样本' },
            { value: 'by_province', label: '按省行挑选', description: '根据省份分组挑选样本' },
            { value: 'by_branch', label: '按支行挑选', description: '根据支行分组挑选样本' },
            { value: 'by_region', label: '按地区挑选', description: '根据地区分组挑选样本' },
            { value: 'random', label: '随机挑选', description: '随机选择样本数据' }
          ],
          record_count_strategies: [
            { value: 'all', label: '全部记录', description: '使用所有符合条件的记录' },
            { value: 'custom', label: '自定义数量', description: '指定具体的记录数量' },
            { value: 'percentage', label: '按百分比', description: '按百分比选择记录' }
          ],
          llm_strategies: [
            { value: 'exact', label: '精确查询', description: '使用完整银行名称查询联行号' },
            { value: 'fuzzy', label: '模糊查询', description: '使用简称或不完整名称查询' },
            { value: 'reverse', label: '反向查询', description: '根据联行号查询银行名称' },
            { value: 'natural', label: '自然语言', description: '口语化的自然语言表达' }
          ]
        });
      }
    } catch (error) {
      // 使用默认策略
      setStrategies({
        selection_strategies: [
          { value: 'all', label: '全部数据', description: '使用所有可用数据' },
          { value: 'by_bank', label: '按银行挑选', description: '根据银行名称分组挑选样本' },
          { value: 'by_province', label: '按省行挑选', description: '根据省份分组挑选样本' },
          { value: 'by_branch', label: '按支行挑选', description: '根据支行分组挑选样本' },
          { value: 'by_region', label: '按地区挑选', description: '根据地区分组挑选样本' },
          { value: 'random', label: '随机挑选', description: '随机选择样本数据' }
        ],
        record_count_strategies: [
          { value: 'all', label: '全部记录', description: '使用所有符合条件的记录' },
          { value: 'custom', label: '自定义数量', description: '指定具体的记录数量' },
          { value: 'percentage', label: '按百分比', description: '按百分比选择记录' }
        ],
        llm_strategies: [
          { value: 'exact', label: '精确查询', description: '使用完整银行名称查询联行号' },
          { value: 'fuzzy', label: '模糊查询', description: '使用简称或不完整名称查询' },
          { value: 'reverse', label: '反向查询', description: '根据联行号查询银行名称' },
          { value: 'natural', label: '自然语言', description: '口语化的自然语言表达' }
        ]
      });
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
      const response = await fetch(`/api/v1/sample-generation/status/${taskId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setCurrentTask(data);
      setModalVisible(true);
    } catch (error) {
      console.error('加载任务状态失败:', error);
      message.error('加载任务状态失败');
    }
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    
    try {
      const requestData = {
        dataset_id: values.dataset_id,
        generation_type: values.generation_type || 'llm',
        question_types: values.question_types || [],
        sample_count: values.sample_count || 10,
        selection_strategy: values.selection_strategy || 'all',
        record_count_strategy: values.record_count_strategy || 'all',
        custom_count: values.custom_count,
        percentage: values.percentage,
        llm_provider: values.llm_provider || 'qwen',
        temperature: values.temperature || 0.7,
        max_tokens: values.max_tokens || 512,
        train_ratio: 0.8,
        val_ratio: 0.1,
        test_ratio: 0.1
      };

      // 调用异步API
      const response = await fetch('/api/v1/sample-generation/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestData)
      });

      if (response.ok) {
        const result = await response.json();
        const taskId = result.task_id;
        
        // 创建任务记录
        const newTask: GenerationTask = {
          task_id: taskId,
          dataset_id: values.dataset_id,
          status: 'pending',
          progress: 0,
          start_time: new Date().toISOString(),
          generated_samples: 0
        };
        
        setTasks(prevTasks => [newTask, ...prevTasks]);
        
        message.success('样本生成任务已启动！');
        
        // 切换到任务Tab
        setActiveTab('tasks');
        
        // 开始轮询任务状态
        startPolling(taskId);
        
        form.resetFields();
        
      } else {
        const error = await response.json();
        message.error(`启动任务失败: ${error.detail || '未知错误'}`);
      }
    } catch (error) {
      message.error('启动任务失败');
      console.error('Sample generation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await fetch(`/api/v1/sample-generation/tasks/${taskId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      message.success('任务已取消');
      loadServerTasks();
      if (currentTask?.task_id === taskId) {
        setCurrentTask(null);
        setModalVisible(false);
      }
      // 停止轮询
      if (pollingInterval) {
        clearInterval(pollingInterval);
        setPollingInterval(null);
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
      dataIndex: 'start_time',
      key: 'start_time',
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }) : '-'
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: GenerationTask) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => loadTaskStatus(record.task_id)}
          >
            查看
          </Button>
          {(record.status === 'pending' || record.status === 'running') && (
            <Button
              size="small"
              danger
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
    <div>
      <Tabs activeKey={activeTab} onChange={setActiveTab} className="sample-generation-tabs" type="card">
        <TabPane 
          tab={
            <span>
              <SettingOutlined />
              生成配置
            </span>
          } 
          key="config"
        >
          {/* 生成配置Tab内容 */}
          <div className="mb-6">
            <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 bg-opacity-50 rounded-2xl border border-purple-200 border-opacity-50">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <BarChartOutlined className="text-white text-sm" />
                </div>
                <div>
                  <h4 className="font-semibold text-purple-900 mb-1">智能样本生成</h4>
                  <p className="text-sm text-purple-800">
                    基于已上传的数据集，使用多种策略自动生成高质量的训练样本。支持按银行、省行、支行等维度挑选，使用不同的LLM生成策略。
                  </p>
                </div>
              </div>
            </div>
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
                    generation_type: 'llm',
                    llm_provider: 'qwen'
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
                              {dataset.filename} ({dataset.total_records || 0} 条记录)
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name="task_name"
                        label="任务名称"
                      >
                        <Input placeholder="为此次生成任务命名（可选）" />
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
                        <Select placeholder="选择样本挑选策略">
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

                  <Divider orientation="left">生成方式</Divider>

                  <Form.Item
                    name="generation_type"
                    label="生成类型"
                    rules={[{ required: true, message: '请选择生成类型' }]}
                  >
                    <Radio.Group>
                      <Radio value="llm">LLM生成</Radio>
                      <Radio value="rule">规则生成</Radio>
                    </Radio.Group>
                  </Form.Item>

                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) => prevValues.generation_type !== currentValues.generation_type}
                  >
                    {({ getFieldValue }) =>
                      getFieldValue('generation_type') === 'llm' ? (
                        <>
                          <Form.Item
                            name="llm_provider"
                            label="选择LLM提供商"
                            rules={[{ required: true, message: '请选择LLM提供商' }]}
                          >
                            <Select placeholder="选择要使用的LLM">
                              <Option value="qwen">
                                <div>
                                  <div className="font-medium">通义千问 (Qwen)</div>
                                  <div className="text-xs text-gray-500">阿里云大模型，响应快速</div>
                                </div>
                              </Option>
                              <Option value="deepseek">
                                <div>
                                  <div className="font-medium">DeepSeek</div>
                                  <div className="text-xs text-gray-500">高性价比，质量优秀</div>
                                </div>
                              </Option>
                              <Option value="volces">
                                <div>
                                  <div className="font-medium">火山引擎 (豆包)</div>
                                  <div className="text-xs text-gray-500">字节跳动大模型</div>
                                </div>
                              </Option>
                              <Option value="local">
                                <div>
                                  <div className="font-medium">本地模板</div>
                                  <div className="text-xs text-gray-500">使用本地模板生成，无需API</div>
                                </div>
                              </Option>
                            </Select>
                          </Form.Item>

                          <Form.Item
                            name="question_types"
                            label="问题类型"
                            rules={[{ required: true, message: '请选择至少一种问题类型' }]}
                          >
                            <Checkbox.Group>
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
                                name="sample_count"
                                label="每种类型生成数量"
                              >
                                <InputNumber min={1} max={100} placeholder="默认10" style={{ width: '100%' }} />
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
                        </>
                      ) : (
                        <Form.Item
                          name="question_types"
                          label="问题类型"
                          rules={[{ required: true, message: '请选择至少一种问题类型' }]}
                        >
                          <Checkbox.Group>
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
                      )
                    }
                  </Form.Item>

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
                      className="btn-primary-glass"
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
                      <li>• <strong>全部数据</strong>：使用所有数据</li>
                      <li>• <strong>按银行</strong>：根据银行名称分组</li>
                      <li>• <strong>按省行</strong>：根据省份分组</li>
                      <li>• <strong>按支行</strong>：根据支行关键词</li>
                      <li>• <strong>按地区</strong>：根据地区分组</li>
                      <li>• <strong>随机挑选</strong>：随机选择样本</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h4 className="font-medium text-gray-900">问题类型</h4>
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      <li>• <strong>精确查询</strong>：完整银行名称查询</li>
                      <li>• <strong>模糊查询</strong>：简称或不完整名称</li>
                      <li>• <strong>反向查询</strong>：联行号查银行名称</li>
                      <li>• <strong>自然语言</strong>：口语化表达</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium text-gray-900">记录数策略</h4>
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      <li>• <strong>全部记录</strong>：使用所有数据</li>
                      <li>• <strong>自定义数量</strong>：指定具体数量</li>
                      <li>• <strong>按百分比</strong>：按比例选择</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-medium text-gray-900">LLM提供商</h4>
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      <li>• <strong>通义千问</strong>：阿里云，响应快</li>
                      <li>• <strong>DeepSeek</strong>：高性价比</li>
                      <li>• <strong>火山引擎</strong>：字节跳动</li>
                      <li>• <strong>本地模板</strong>：无需API</li>
                    </ul>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 生成历史记录 */}
          {generationHistory.length > 0 && (
            <Card title="最近生成记录" className="glass-card mt-6">
              <div className="space-y-3">
                {generationHistory.slice(-5).reverse().map((record) => (
                  <div 
                    key={record.id} 
                    className="p-4 bg-white bg-opacity-50 rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <Tag color={record.status === 'success' ? 'green' : 'red'}>
                            {record.status === 'success' ? '✅ 成功' : '❌ 失败'}
                          </Tag>
                          <span className="font-medium text-gray-900">{record.dataset_name}</span>
                        </div>
                        
                        {record.status === 'success' ? (
                          <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">总计:</span>
                              <span className="ml-2 font-medium text-blue-600">{record.generated_count}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">训练集:</span>
                              <span className="ml-2 font-medium">{record.train_count}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">验证集:</span>
                              <span className="ml-2 font-medium">{record.val_count}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">测试集:</span>
                              <span className="ml-2 font-medium">{record.test_count}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="text-sm text-red-600">
                            错误: {record.error_message}
                          </div>
                        )}
                        
                        <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                          <span>LLM: {record.llm_provider}</span>
                          <span>类型: {record.question_types.join(', ')}</span>
                          <span>{new Date(record.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {generationHistory.length > 5 && (
                <div className="mt-4 text-center">
                  <Button 
                    type="link" 
                    onClick={() => {
                      Modal.info({
                        title: '完整生成历史',
                        width: 800,
                        content: (
                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {generationHistory.slice().reverse().map((record) => (
                              <div key={record.id} className="p-3 bg-gray-50 rounded">
                                <div className="flex justify-between items-center">
                                  <div>
                                    <Tag color={record.status === 'success' ? 'green' : 'red'}>
                                      {record.status === 'success' ? '成功' : '失败'}
                                    </Tag>
                                    <span className="font-medium">{record.dataset_name}</span>
                                    {record.status === 'success' && (
                                      <span className="ml-2 text-gray-600">
                                        ({record.generated_count} 个样本)
                                      </span>
                                    )}
                                  </div>
                                  <span className="text-xs text-gray-500">
                                    {new Date(record.created_at).toLocaleString()}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )
                      });
                    }}
                  >
                    查看全部 {generationHistory.length} 条记录
                  </Button>
                </div>
              )}
            </Card>
          )}
        </TabPane>

        <TabPane 
          tab={
            <span>
              <UnorderedListOutlined />
              生成任务
            </span>
          } 
          key="tasks"
        >
          {/* 生成任务Tab内容 */}
          <Card title="生成任务" className="glass-card" extra={
            <Button icon={<ReloadOutlined />} onClick={loadServerTasks}>
              刷新
            </Button>
          }>
            <Table
              columns={taskColumns}
              dataSource={tasks}
              rowKey="task_id"
              pagination={{ pageSize: 10 }}
              locale={{
                emptyText: '暂无生成任务'
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 任务进度监控弹窗 */}
      <Modal
        title="任务执行监控"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          currentTask && (currentTask.status === 'pending' || currentTask.status === 'running') && (
            <Button key="cancel" danger onClick={() => {
              if (currentTask) {
                cancelTask(currentTask.task_id);
              }
            }}>
              取消任务
            </Button>
          ),
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

export default SampleGenerationTab;