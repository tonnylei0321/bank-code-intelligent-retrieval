/**
 * 训练中心页面 - 极简主义设计，毛玻璃效果
 * 
 * 设计原则：
 * - 极简主义：大片留白，移除多余装饰
 * - 毛玻璃效果：backdrop-filter 和半透明背景
 * - 视觉层级：大号数据，小号辅助信息
 * - Bento Grid：便当格布局风格
 * - 现代字体：Inter 字体系统
 * 
 * 功能：
 * - 训练任务管理
 * - 智能训练参数优化
 * - 实时训练监控
 * - 训练历史和统计
 * - 模型评估和对比
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Progress,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  Tabs,
  List,
  Typography,
  Tooltip,
  Badge,
  Timeline,
  message,
  Empty,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  BarChartOutlined,
  RocketOutlined,
  MonitorOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { trainingAPI } from '../services/api';

const { Text } = Typography;

interface TrainingJob {
  id: number;
  model_name: string;
  status: string;
  progress: number;
  current_epoch: number;
  total_epochs: number;
  train_loss: number;
  val_loss: number;
  learning_rate: number;
  batch_size: number;
  created_at: string;
  started_at: string;
  completed_at: string;
  model_path: string;
  config: any;
  logs: string[];
}

interface TrainingConfig {
  model_name: string;
  dataset_id: number;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  optimizer: string;
  scheduler: string;
  early_stopping: boolean;
  patience: number;
  intelligent_optimization: boolean;
}

const TrainingCenter: React.FC = () => {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [monitorModalVisible, setMonitorModalVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);
  const [createForm] = Form.useForm();
  const [activeTab, setActiveTab] = useState('jobs');

  // 获取训练任务列表
  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await trainingAPI.getTrainingJobs();
      if (response.data?.success) {
        setJobs(response.data.jobs || []);
      }
    } catch (error) {
      console.error('获取训练任务失败:', error);
      message.error('获取训练任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 创建训练任务
  const handleCreateJob = async (values: TrainingConfig) => {
    try {
      // 模拟API调用
      console.log('Creating training job:', values);
      message.success('训练任务创建成功');
      setCreateModalVisible(false);
      createForm.resetFields();
      fetchJobs();
    } catch (error: any) {
      console.error('创建训练任务失败:', error);
      message.error('创建失败');
    }
  };

  // 控制训练任务
  const handleJobControl = async (jobId: number, action: 'start' | 'pause' | 'stop') => {
    try {
      // 模拟API调用
      console.log(`${action} training job:`, jobId);
      message.success(`任务${action === 'start' ? '启动' : action === 'pause' ? '暂停' : '停止'}成功`);
      fetchJobs();
    } catch (error) {
      console.error('控制训练任务失败:', error);
      message.error('操作失败');
    }
  };

  // 删除训练任务
  const handleDeleteJob = async (jobId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个训练任务吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          // 模拟API调用
          console.log('Deleting training job:', jobId);
          message.success('删除成功');
          fetchJobs();
        } catch (error) {
          console.error('删除训练任务失败:', error);
          message.error('删除失败');
        }
      },
    });
  };

  // 监控训练任务
  const handleMonitorJob = async (job: TrainingJob) => {
    setSelectedJob(job);
    setMonitorModalVisible(true);
  };

  // 键盘快捷键处理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.altKey) {
        switch (event.key.toLowerCase()) {
          case 'c':
            event.preventDefault();
            setCreateModalVisible(true);
            break;
          case 'i':
            event.preventDefault();
            setCreateModalVisible(true);
            createForm.setFieldsValue({ intelligent_optimization: true });
            break;
          case 't':
            event.preventDefault();
            const tabs = ['jobs', 'monitor', 'history'];
            const currentIndex = tabs.indexOf(activeTab);
            const nextIndex = (currentIndex + 1) % tabs.length;
            setActiveTab(tabs[nextIndex]);
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [activeTab, createForm]);

  useEffect(() => {
    fetchJobs();
    
    // 设置定时刷新
    const interval = setInterval(fetchJobs, 10000); // 每10秒刷新一次
    return () => clearInterval(interval);
  }, []);

  // 训练任务表格列
  const jobColumns = [
    {
      title: '任务信息',
      key: 'info',
      render: (_: any, record: TrainingJob) => (
        <div>
          <Text strong>{record.model_name}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            ID: {record.id}
          </Text>
          {record.config?.intelligent_optimization && (
            <div>
              <Tag color="gold" icon={<ThunderboltOutlined />}>
                智能优化
              </Tag>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const statusConfig = {
          'pending': { color: 'default', text: '等待中', icon: <ClockCircleOutlined /> },
          'running': { color: 'processing', text: '训练中', icon: <PlayCircleOutlined /> },
          'paused': { color: 'warning', text: '已暂停', icon: <PauseCircleOutlined /> },
          'completed': { color: 'success', text: '已完成', icon: <CheckCircleOutlined /> },
          'failed': { color: 'error', text: '失败', icon: <ExclamationCircleOutlined /> },
          'stopped': { color: 'default', text: '已停止', icon: <StopOutlined /> },
        };
        const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending;
        return (
          <Badge status={config.color as any} text={
            <Space>
              {config.icon}
              {config.text}
            </Space>
          } />
        );
      },
    },
    {
      title: '进度',
      key: 'progress',
      width: 200,
      render: (_: any, record: TrainingJob) => (
        <div>
          <Progress
            percent={record.progress}
            size="small"
            status={record.status === 'failed' ? 'exception' : 'active'}
          />
          <Text style={{ fontSize: 12 }}>
            Epoch {record.current_epoch}/{record.total_epochs}
          </Text>
        </div>
      ),
    },
    {
      title: '损失值',
      key: 'loss',
      width: 150,
      render: (_: any, record: TrainingJob) => (
        <div>
          {record.train_loss && (
            <div>
              <Text style={{ fontSize: 12 }}>训练: {record.train_loss.toFixed(4)}</Text>
            </div>
          )}
          {record.val_loss && (
            <div>
              <Text style={{ fontSize: 12 }}>验证: {record.val_loss.toFixed(4)}</Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '参数',
      key: 'params',
      width: 150,
      render: (_: any, record: TrainingJob) => (
        <div>
          <Text style={{ fontSize: 12 }}>LR: {record.learning_rate}</Text>
          <br />
          <Text style={{ fontSize: 12 }}>Batch: {record.batch_size}</Text>
        </div>
      ),
    },
    {
      title: '时间',
      key: 'time',
      width: 160,
      render: (_: any, record: TrainingJob) => (
        <div>
          <Text style={{ fontSize: 12 }}>
            创建: {new Date(record.created_at).toLocaleDateString('zh-CN')}
          </Text>
          {record.started_at && (
            <div>
              <Text style={{ fontSize: 12 }}>
                开始: {new Date(record.started_at).toLocaleTimeString('zh-CN')}
              </Text>
            </div>
          )}
          {record.completed_at && (
            <div>
              <Text style={{ fontSize: 12 }}>
                完成: {new Date(record.completed_at).toLocaleTimeString('zh-CN')}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: TrainingJob) => (
        <Space>
          {record.status === 'pending' && (
            <Tooltip title="开始训练">
              <Button
                type="link"
                icon={<PlayCircleOutlined />}
                onClick={() => handleJobControl(record.id, 'start')}
              />
            </Tooltip>
          )}
          {record.status === 'running' && (
            <>
              <Tooltip title="暂停训练">
                <Button
                  type="link"
                  icon={<PauseCircleOutlined />}
                  onClick={() => handleJobControl(record.id, 'pause')}
                />
              </Tooltip>
              <Tooltip title="停止训练">
                <Button
                  type="link"
                  icon={<StopOutlined />}
                  onClick={() => handleJobControl(record.id, 'stop')}
                />
              </Tooltip>
            </>
          )}
          {record.status === 'paused' && (
            <Tooltip title="继续训练">
              <Button
                type="link"
                icon={<PlayCircleOutlined />}
                onClick={() => handleJobControl(record.id, 'start')}
              />
            </Tooltip>
          )}
          <Tooltip title="监控详情">
            <Button
              type="link"
              icon={<MonitorOutlined />}
              onClick={() => handleMonitorJob(record)}
            />
          </Tooltip>
          <Tooltip title="删除任务">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteJob(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 统计信息
  const totalJobs = jobs.length;
  const runningJobs = jobs.filter(j => j.status === 'running').length;
  const completedJobs = jobs.filter(j => j.status === 'completed').length;
  const failedJobs = jobs.filter(j => j.status === 'failed').length;

  return (
    <div className="minimalist-container">
      <div className="content-area">
        {/* 页面标题 - 极简设计 */}
        <div className="section-spacing">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="title-primary">训练中心</h1>
              <p className="subtitle">管理模型训练任务，支持智能参数优化和实时监控</p>
            </div>
            <div className="flex items-center space-x-4">
              <Button
                type="primary"
                icon={<RocketOutlined />}
                onClick={() => setCreateModalVisible(true)}
                className="btn-primary-glass"
              >
                创建训练任务
              </Button>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={() => {
                  setCreateModalVisible(true);
                  createForm.setFieldsValue({ intelligent_optimization: true });
                }}
                className="btn-secondary-glass"
              >
                智能训练
              </Button>
              <div className="flex space-x-2">
                <div className="tag-primary">Alt+C</div>
                <div className="tag-warning">Alt+I</div>
              </div>
            </div>
          </div>
        </div>

        {/* 核心指标 - Bento Grid 布局 */}
        <div className="bento-grid-4 section-spacing">
          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">总任务数</p>
                <p className="metric-primary">{totalJobs}</p>
                <div className="flex items-center mt-3">
                  <ExperimentOutlined className="text-blue-500 text-sm mr-2" />
                  <span className="text-sm text-gray-600 font-medium">已创建任务</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <ExperimentOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">运行中</p>
                <p className="metric-primary">{runningJobs}</p>
                <div className="flex items-center mt-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                  <span className="text-sm text-green-600 font-medium">正在训练</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <PlayCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">已完成</p>
                <p className="metric-primary">{completedJobs}</p>
                <div className="mt-3">
                  <div className="progress-glass">
                    <div 
                      className="progress-bar" 
                      style={{ 
                        width: `${totalJobs > 0 ? Math.round((completedJobs / totalJobs) * 100) : 0}%` 
                      }}
                    />
                  </div>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">失败任务</p>
                <p className="metric-primary">{failedJobs}</p>
                <div className="flex items-center mt-3">
                  <span className="text-sm text-red-600 font-medium">
                    {totalJobs > 0 ? `${Math.round((failedJobs / totalJobs) * 100)}%` : '0%'} 失败率
                  </span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-red-500 to-red-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <ExclamationCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>
        </div>

        {/* 主要内容区域 */}
        <Card className="glass-card section-spacing">
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            tabBarExtraContent={
              <div className="tag-primary">Alt+T 切换</div>
            }
          >
            <Tabs.TabPane tab={
              <div className="flex items-center space-x-2">
                <ExperimentOutlined />
                <span>训练任务</span>
                <Badge count={runningJobs} size="small" />
              </div>
            } key="jobs">
              <div className="mb-6">
                <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      <ExperimentOutlined className="text-white text-sm" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-blue-900 mb-1">训练任务管理</h4>
                      <p className="text-sm text-blue-800">
                        管理所有训练任务，支持创建、启动、暂停、停止和监控训练过程。智能训练模式会自动优化超参数。
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="table-glass">
                <Table
                  columns={jobColumns}
                  dataSource={jobs}
                  loading={loading}
                  rowKey="id"
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 个训练任务`,
                  }}
                  locale={{ 
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="暂无训练任务"
                      />
                    )
                  }}
                />
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab={
              <div className="flex items-center space-x-2">
                <MonitorOutlined />
                <span>训练监控</span>
                <Badge count={runningJobs} size="small" />
              </div>
            } key="monitor">
              <div className="bento-grid-2 gap-8">
                <Card className="glass-card">
                  <div className="flex items-center space-x-3 mb-6">
                    <div className="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center">
                      <PlayCircleOutlined className="text-white text-lg" />
                    </div>
                    <h3 className="title-secondary mb-0">运行中的任务</h3>
                  </div>

                  <List
                    dataSource={jobs.filter(j => j.status === 'running')}
                    renderItem={(job) => (
                      <List.Item
                        className="border-none py-4 hover:bg-gray-50 hover:bg-opacity-50 rounded-xl transition-colors"
                        actions={[
                          <Button
                            type="text"
                            onClick={() => handleMonitorJob(job)}
                            className="btn-secondary-glass"
                          >
                            详情
                          </Button>
                        ]}
                      >
                        <List.Item.Meta
                          title={<span className="font-semibold text-gray-900">{job.model_name}</span>}
                          description={
                            <div className="space-y-3">
                              <div className="progress-glass">
                                <div 
                                  className="progress-bar" 
                                  style={{ width: `${job.progress}%` }}
                                />
                              </div>
                              <div className="flex items-center space-x-4 text-sm text-gray-600">
                                <span>Epoch {job.current_epoch}/{job.total_epochs}</span>
                                {job.train_loss && (
                                  <span>Loss: {job.train_loss.toFixed(4)}</span>
                                )}
                              </div>
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: '暂无运行中的任务' }}
                  />
                </Card>

                <Card className="glass-card">
                  <div className="flex items-center space-x-3 mb-6">
                    <div className="w-10 h-10 bg-purple-500 rounded-xl flex items-center justify-center">
                      <CheckCircleOutlined className="text-white text-lg" />
                    </div>
                    <h3 className="title-secondary mb-0">最近完成</h3>
                  </div>

                  <List
                    dataSource={jobs
                      .filter(j => j.status === 'completed')
                      .sort((a, b) => new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime())
                      .slice(0, 5)
                    }
                    renderItem={(job) => (
                      <List.Item className="border-none py-4 hover:bg-gray-50 hover:bg-opacity-50 rounded-xl transition-colors">
                        <List.Item.Meta
                          title={<span className="font-semibold text-gray-900">{job.model_name}</span>}
                          description={
                            <div className="space-y-2">
                              <div className="flex items-center space-x-2">
                                <div className="tag-success">已完成</div>
                                {job.config?.intelligent_optimization && (
                                  <div className="tag-warning">
                                    <ThunderboltOutlined className="mr-1" />
                                    智能优化
                                  </div>
                                )}
                              </div>
                              <div className="text-sm text-gray-500">
                                {new Date(job.completed_at).toLocaleString('zh-CN')}
                              </div>
                              {job.train_loss && (
                                <div className="text-sm text-gray-600">
                                  最终损失: {job.train_loss.toFixed(4)}
                                </div>
                              )}
                            </div>
                          }
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: '暂无完成的任务' }}
                  />
                </Card>
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab={
              <div className="flex items-center space-x-2">
                <HistoryOutlined />
                <span>训练历史</span>
              </div>
            } key="history">
              <Card className="glass-card">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center">
                    <BarChartOutlined className="text-white text-lg" />
                  </div>
                  <h3 className="title-secondary mb-0">训练历史统计</h3>
                </div>

                <Timeline className="mt-6">
                  {jobs
                    .filter(j => j.status === 'completed' || j.status === 'failed')
                    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                    .slice(0, 10)
                    .map((job) => (
                      <Timeline.Item
                        key={job.id}
                        color={job.status === 'completed' ? 'green' : 'red'}
                        dot={
                          <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                            job.status === 'completed' ? 'bg-green-500' : 'bg-red-500'
                          }`}>
                            {job.status === 'completed' ? (
                              <CheckCircleOutlined className="text-white text-xs" />
                            ) : (
                              <ExclamationCircleOutlined className="text-white text-xs" />
                            )}
                          </div>
                        }
                      >
                        <div className="pb-6">
                          <div className="flex items-center space-x-3 mb-3">
                            <span className="font-semibold text-gray-900">{job.model_name}</span>
                            <div className={`tag-${job.status === 'completed' ? 'success' : 'error'}`}>
                              {job.status === 'completed' ? '成功' : '失败'}
                            </div>
                            {job.config?.intelligent_optimization && (
                              <div className="tag-warning">
                                <ThunderboltOutlined className="mr-1" />
                                智能优化
                              </div>
                            )}
                          </div>
                          <div className="text-sm text-gray-500 mb-2">
                            {new Date(job.created_at).toLocaleString('zh-CN')}
                          </div>
                          {job.train_loss && (
                            <div className="text-sm text-gray-700 mb-2">
                              最终损失: {job.train_loss.toFixed(4)}
                            </div>
                          )}
                          <div className="text-xs text-gray-400">
                            ID: {job.id} | Epochs: {job.total_epochs} | Batch Size: {job.batch_size}
                          </div>
                        </div>
                      </Timeline.Item>
                    ))}
                </Timeline>
              </Card>
            </Tabs.TabPane>
          </Tabs>
        </Card>

        {/* 创建训练任务模态框 */}
        <Modal
          title={
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <RocketOutlined className="text-white text-sm" />
              </div>
              <span className="font-semibold">创建训练任务</span>
            </div>
          }
          visible={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          footer={null}
          width={600}
          className="modal-glass"
        >
          <Form
            form={createForm}
            layout="vertical"
            onFinish={handleCreateJob}
            initialValues={{
              epochs: 10,
              batch_size: 8,
              learning_rate: 0.0001,
              optimizer: 'adamw',
              scheduler: 'linear',
              early_stopping: true,
              patience: 3,
              intelligent_optimization: false,
            }}
            className="space-y-6"
          >
            <Form.Item
              name="model_name"
              label={<span className="font-semibold text-gray-900">模型名称</span>}
              rules={[{ required: true, message: '请输入模型名称' }]}
            >
              <Input 
                placeholder="输入模型名称" 
                className="input-glass"
              />
            </Form.Item>

            <Form.Item
              name="dataset_id"
              label={<span className="font-semibold text-gray-900">数据集</span>}
              rules={[{ required: true, message: '请选择数据集' }]}
            >
              <Select 
                placeholder="选择训练数据集"
                className="w-full"
              >
                <Select.Option value={1}>银行问答数据集</Select.Option>
                <Select.Option value={2}>通用问答数据集</Select.Option>
              </Select>
            </Form.Item>

            <div className="bento-grid-2 gap-4">
              <Form.Item
                name="epochs"
                label={<span className="font-semibold text-gray-900">训练轮数</span>}
                rules={[{ required: true, message: '请输入训练轮数' }]}
              >
                <InputNumber 
                  min={1} 
                  max={100} 
                  className="w-full input-glass" 
                />
              </Form.Item>

              <Form.Item
                name="batch_size"
                label={<span className="font-semibold text-gray-900">批次大小</span>}
                rules={[{ required: true, message: '请输入批次大小' }]}
              >
                <InputNumber 
                  min={1} 
                  max={64} 
                  className="w-full input-glass" 
                />
              </Form.Item>
            </div>

            <Form.Item
              name="learning_rate"
              label={<span className="font-semibold text-gray-900">学习率</span>}
              rules={[{ required: true, message: '请输入学习率' }]}
            >
              <InputNumber
                min={0.00001}
                max={0.01}
                step={0.00001}
                className="w-full input-glass"
                formatter={(value) => `${value}`}
              />
            </Form.Item>

            <div className="bento-grid-2 gap-4">
              <Form.Item
                name="optimizer"
                label={<span className="font-semibold text-gray-900">优化器</span>}
                rules={[{ required: true, message: '请选择优化器' }]}
              >
                <Select className="w-full">
                  <Select.Option value="adamw">AdamW</Select.Option>
                  <Select.Option value="adam">Adam</Select.Option>
                  <Select.Option value="sgd">SGD</Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="scheduler"
                label={<span className="font-semibold text-gray-900">学习率调度器</span>}
                rules={[{ required: true, message: '请选择调度器' }]}
              >
                <Select className="w-full">
                  <Select.Option value="linear">Linear</Select.Option>
                  <Select.Option value="cosine">Cosine</Select.Option>
                  <Select.Option value="constant">Constant</Select.Option>
                </Select>
              </Form.Item>
            </div>

            <div className="p-4 bg-gray-50 bg-opacity-50 rounded-2xl border border-gray-200 border-opacity-50 space-y-4">
              <Form.Item name="early_stopping" valuePropName="checked" className="mb-2">
                <div className="flex items-center space-x-3">
                  <Switch />
                  <span className="font-semibold text-gray-900">启用早停</span>
                </div>
              </Form.Item>

              <Form.Item
                name="patience"
                label={<span className="font-medium text-gray-700">早停耐心值</span>}
                dependencies={['early_stopping']}
              >
                <InputNumber 
                  min={1} 
                  max={10} 
                  className="w-full input-glass" 
                />
              </Form.Item>

              <Form.Item name="intelligent_optimization" valuePropName="checked" className="mb-0">
                <div className="flex items-center space-x-3">
                  <Switch />
                  <span className="font-semibold text-gray-900">启用智能参数优化</span>
                  <ThunderboltOutlined className="text-yellow-500" />
                </div>
              </Form.Item>
            </div>

            <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
              <div className="flex items-start space-x-3">
                <div className="w-6 h-6 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <ThunderboltOutlined className="text-white text-xs" />
                </div>
                <div>
                  <h4 className="font-semibold text-blue-900 mb-1">智能优化说明</h4>
                  <p className="text-sm text-blue-800">
                    启用后系统会自动调整学习率、批次大小等超参数，以获得更好的训练效果。
                  </p>
                </div>
              </div>
            </div>

            <Form.Item className="mb-0">
              <div className="flex justify-end space-x-3">
                <Button onClick={() => setCreateModalVisible(false)} className="btn-secondary-glass">
                  取消
                </Button>
                <Button type="primary" htmlType="submit" className="btn-primary-glass">
                  创建任务
                </Button>
              </div>
            </Form.Item>
          </Form>
        </Modal>

        {/* 训练监控模态框 */}
        <Modal
          title={
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                <MonitorOutlined className="text-white text-sm" />
              </div>
              <span className="font-semibold">训练监控: {selectedJob?.model_name}</span>
            </div>
          }
          visible={monitorModalVisible}
          onCancel={() => setMonitorModalVisible(false)}
          width={800}
          footer={[
            <Button key="close" onClick={() => setMonitorModalVisible(false)} className="btn-secondary-glass">
              关闭
            </Button>,
          ]}
          className="modal-glass"
        >
          {selectedJob && (
            <div className="space-y-6">
              <div className="bento-grid-3 gap-4">
                <div className="text-center p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
                  <p className="metric-secondary mb-2">当前轮数</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {selectedJob.current_epoch}
                  </p>
                  <p className="text-sm text-gray-500">/ {selectedJob.total_epochs}</p>
                </div>
                <div className="text-center p-4 bg-green-50 bg-opacity-50 rounded-2xl border border-green-200 border-opacity-50">
                  <p className="metric-secondary mb-2">训练进度</p>
                  <p className="text-2xl font-bold text-green-600">
                    {selectedJob.progress}%
                  </p>
                </div>
                <div className="text-center p-4 bg-purple-50 bg-opacity-50 rounded-2xl border border-purple-200 border-opacity-50">
                  <p className="metric-secondary mb-2">当前损失</p>
                  <p className="text-2xl font-bold text-purple-600">
                    {selectedJob.train_loss?.toFixed(4) || 'N/A'}
                  </p>
                </div>
              </div>

              <div className="progress-glass">
                <div 
                  className="progress-bar" 
                  style={{ width: `${selectedJob.progress}%` }}
                />
              </div>

              <Card className="glass-card">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-8 h-8 bg-gray-500 rounded-lg flex items-center justify-center">
                    <FileTextOutlined className="text-white text-sm" />
                  </div>
                  <h4 className="font-semibold text-gray-900">训练日志</h4>
                </div>
                
                <div className="max-h-64 overflow-auto">
                  {selectedJob.logs && selectedJob.logs.length > 0 ? (
                    <List
                      size="small"
                      dataSource={selectedJob.logs.slice(-10)}
                      renderItem={(log) => (
                        <List.Item className="border-none py-2">
                          <div className="w-full p-2 bg-gray-100 bg-opacity-50 rounded-lg font-mono text-xs text-gray-700">
                            {log}
                          </div>
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty 
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="暂无日志信息"
                    />
                  )}
                </div>
              </Card>
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
};

export default TrainingCenter;