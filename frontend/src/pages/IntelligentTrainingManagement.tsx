/**
 * 智能训练管理页面
 * 
 * 功能：
 * - 智能参数优化
 * - 训练任务列表
 * - 创建训练任务
 * - 查看训练详情
 * - 停止训练任务
 * - 实时进度显示
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  InputNumber,
  Select,
  Drawer,
  message,
  Space,
  Tag,
  Progress,
  Descriptions,
  Timeline,
  Switch,
  Alert,
  Divider,
  Spin,
  Tooltip,
  List,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  StopOutlined,
  ReloadOutlined,
  BulbOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { trainingAPI, dataAPI } from '../services/api';

interface TrainingJob {
  id: number;
  dataset_id: number;
  model_name: string;
  status: string;
  progress_percentage: number;
  lora_r: number;
  learning_rate: number;
  epochs: number;
  batch_size: number;
  current_epoch: number;
  train_loss: number;
  val_loss: number;
  created_at: string;
  started_at: string;
  completed_at: string;
  error_message: string;
}

interface Dataset {
  id: number;
  filename: string;
  record_count: number;
}

interface OptimizedParams {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  lora_r: number;
  lora_alpha: number;
  lora_dropout: number;
  gradient_accumulation_steps: number;
  warmup_steps: number;
  weight_decay: number;
  max_grad_norm: number;
  estimated_training_time_hours: number;
  estimated_memory_usage_gb: number;
  optimization_notes: string[];
}

const IntelligentTrainingManagement: React.FC = () => {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [optimizeLoading, setOptimizeLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);
  const [useOptimizedParams, setUseOptimizedParams] = useState(true);
  const [optimizedParams, setOptimizedParams] = useState<OptimizedParams | null>(null);
  const [form] = Form.useForm();

  // 获取训练任务列表
  const fetchJobs = async () => {
    setLoading(true);
    try {
      const response = await trainingAPI.getTrainingJobs();
      setJobs(response.data?.jobs || []);
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '获取训练任务失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取数据集列表
  const fetchDatasets = async () => {
    try {
      const response = await dataAPI.getDatasets();
      setDatasets(response.data || []);
    } catch (error) {
      console.error('获取数据集失败', error);
    }
  };

  // 获取优化参数
  const getOptimizedParams = async (datasetId: number, modelName: string, targetHours: number) => {
    setOptimizeLoading(true);
    try {
      const response = await trainingAPI.optimizeTrainingParams({
        dataset_id: datasetId,
        model_name: modelName,
        target_training_time_hours: targetHours,
      });
      setOptimizedParams(response.data);
      
      // 自动填充表单
      form.setFieldsValue({
        epochs: response.data.epochs,
        batch_size: response.data.batch_size,
        learning_rate: response.data.learning_rate,
        lora_r: response.data.lora_r,
        lora_alpha: response.data.lora_alpha,
        lora_dropout: response.data.lora_dropout,
      });
      
      message.success('参数优化完成！');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '参数优化失败');
      setOptimizedParams(null);
    } finally {
      setOptimizeLoading(false);
    }
  };

  // 当数据集或模型改变时，自动获取优化参数
  const handleDatasetOrModelChange = () => {
    if (useOptimizedParams) {
      const datasetId = form.getFieldValue('dataset_id');
      const modelName = form.getFieldValue('model_name');
      const targetHours = form.getFieldValue('target_training_time_hours') || 24;
      
      if (datasetId && modelName) {
        getOptimizedParams(datasetId, modelName, targetHours);
      }
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchDatasets();
    
    // 每10秒自动刷新一次
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  // 创建训练任务
  const handleCreateJob = async (values: any) => {
    setCreateLoading(true);
    try {
      const payload = {
        ...values,
        use_optimized_params: useOptimizedParams,
      };
      
      await trainingAPI.startTraining(payload);
      message.success('训练任务创建成功！');
      setCreateModalVisible(false);
      form.resetFields();
      setOptimizedParams(null);
      fetchJobs();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建训练任务失败');
    } finally {
      setCreateLoading(false);
    }
  };

  // 停止训练任务
  const handleStopJob = async (jobId: number) => {
    try {
      await trainingAPI.stopTraining(jobId);
      message.success('训练任务已停止');
      fetchJobs();
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '停止训练任务失败');
    }
  };

  // 查看训练详情
  const handleViewDetail = (job: TrainingJob) => {
    setSelectedJob(job);
    setDetailDrawerVisible(true);
  };

  // 状态标签颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'processing';
      case 'completed': return 'success';
      case 'failed': return 'error';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  // 状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '运行中';
      case 'completed': return '已完成';
      case 'failed': return '失败';
      case 'pending': return '等待中';
      default: return status;
    }
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '数据集',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 80,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 150,
      render: (text: string) => text.split('/').pop(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress_percentage',
      key: 'progress_percentage',
      width: 120,
      render: (progress: number, record: TrainingJob) => (
        <Progress 
          percent={Math.round(progress || 0)} 
          size="small"
          status={record.status === 'failed' ? 'exception' : undefined}
        />
      ),
    },
    {
      title: '配置',
      key: 'config',
      width: 150,
      render: (record: TrainingJob) => (
        <div>
          <div>Epochs: {record.epochs}</div>
          <div>Batch: {record.batch_size}</div>
          <div>LoRA R: {record.lora_r}</div>
        </div>
      ),
    },
    {
      title: '损失',
      dataIndex: 'train_loss',
      key: 'train_loss',
      width: 100,
      render: (loss: number) => loss ? loss.toFixed(4) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (record: TrainingJob) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status === 'running' && (
            <Button
              type="link"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStopJob(record.id)}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={
          <Space>
            <ThunderboltOutlined />
            智能训练管理
          </Space>
        }
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              创建训练任务
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchJobs}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={jobs}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个任务`,
          }}
        />
      </Card>

      {/* 创建训练任务模态框 */}
      <Modal
        title={
          <Space>
            <BulbOutlined />
            创建智能训练任务
          </Space>
        }
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
          setOptimizedParams(null);
        }}
        onOk={() => form.submit()}
        confirmLoading={createLoading}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateJob}
          initialValues={{
            model_name: 'Qwen/Qwen2.5-0.5B',
            target_training_time_hours: 24,
            epochs: 3,
            batch_size: 8,
            learning_rate: 0.0002,
            lora_r: 16,
            lora_alpha: 32,
            lora_dropout: 0.05,
          }}
        >
          <Alert
            message="智能参数优化"
            description="系统将根据数据集大小、模型类型和硬件限制自动计算最优训练参数，提高训练效率并避免内存溢出。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />

          <Form.Item
            name="dataset_id"
            label="数据集"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select
              placeholder="选择数据集"
              onChange={handleDatasetOrModelChange}
            >
              {datasets.map((dataset) => (
                <Select.Option key={dataset.id} value={dataset.id}>
                  {dataset.filename} ({dataset.record_count} 条记录)
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="model_name"
            label="基础模型"
            rules={[{ required: true, message: '请选择基础模型' }]}
          >
            <Select
              placeholder="选择基础模型"
              onChange={handleDatasetOrModelChange}
            >
              <Select.Option value="Qwen/Qwen2.5-0.5B">
                Qwen2.5-0.5B (推荐，快速训练，中文优化)
              </Select.Option>
              <Select.Option value="Qwen/Qwen2.5-1.5B">
                Qwen2.5-1.5B (更强性能，需要更多内存)
              </Select.Option>
              <Select.Option value="Qwen/Qwen2.5-3B">
                Qwen2.5-3B (最强性能，需要大量内存)
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="智能参数优化">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Switch
                checked={useOptimizedParams}
                onChange={(checked) => {
                  setUseOptimizedParams(checked);
                  if (checked) {
                    handleDatasetOrModelChange();
                  } else {
                    setOptimizedParams(null);
                  }
                }}
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
              <span style={{ color: '#666' }}>
                开启后系统将自动计算最优参数，关闭后可手动设置参数
              </span>
            </Space>
          </Form.Item>

          {useOptimizedParams && (
            <Form.Item
              name="target_training_time_hours"
              label="目标训练时间（小时）"
              rules={[{ required: true, message: '请输入目标训练时间' }]}
            >
              <InputNumber
                min={1}
                max={168}
                style={{ width: '100%' }}
                onChange={handleDatasetOrModelChange}
                addonAfter="小时"
              />
            </Form.Item>
          )}

          {optimizeLoading && (
            <div style={{ textAlign: 'center', margin: '20px 0' }}>
              <Spin size="large" />
              <div style={{ marginTop: 8 }}>正在分析数据集并优化参数...</div>
            </div>
          )}

          {optimizedParams && (
            <Card
              title={
                <Space>
                  <BulbOutlined style={{ color: '#52c41a' }} />
                  智能优化结果
                </Space>
              }
              size="small"
              style={{ marginBottom: 16 }}
            >
              <Descriptions column={2} size="small">
                <Descriptions.Item label="预计训练时间">
                  {optimizedParams.estimated_training_time_hours.toFixed(1)} 小时
                </Descriptions.Item>
                <Descriptions.Item label="预计内存使用">
                  {optimizedParams.estimated_memory_usage_gb.toFixed(1)} GB
                </Descriptions.Item>
              </Descriptions>
              
              <Divider style={{ margin: '12px 0' }} />
              
              <div>
                <strong>优化建议：</strong>
                <List
                  size="small"
                  dataSource={optimizedParams.optimization_notes}
                  renderItem={(note) => (
                    <List.Item style={{ padding: '4px 0' }}>
                      • {note}
                    </List.Item>
                  )}
                />
              </div>
            </Card>
          )}

          <Divider>训练参数</Divider>

          <div style={{ display: 'flex', gap: '16px' }}>
            <Form.Item
              name="epochs"
              label="训练轮数"
              rules={[{ required: true, message: '请输入训练轮数' }]}
              style={{ flex: 1 }}
            >
              <InputNumber
                min={1}
                max={20}
                style={{ width: '100%' }}
                disabled={useOptimizedParams && optimizeLoading}
              />
            </Form.Item>

            <Form.Item
              name="batch_size"
              label="批次大小"
              rules={[{ required: true, message: '请输入批次大小' }]}
              style={{ flex: 1 }}
            >
              <InputNumber
                min={1}
                max={64}
                style={{ width: '100%' }}
                disabled={useOptimizedParams && optimizeLoading}
              />
            </Form.Item>
          </div>

          <Form.Item
            name="learning_rate"
            label="学习率"
            rules={[{ required: true, message: '请输入学习率' }]}
          >
            <InputNumber
              min={0.00001}
              max={0.01}
              step={0.00001}
              style={{ width: '100%' }}
              disabled={useOptimizedParams && optimizeLoading}
            />
          </Form.Item>

          <Divider>LoRA 参数</Divider>

          <div style={{ display: 'flex', gap: '16px' }}>
            <Form.Item
              name="lora_r"
              label="LoRA Rank"
              rules={[{ required: true, message: '请输入LoRA Rank' }]}
              style={{ flex: 1 }}
            >
              <InputNumber
                min={1}
                max={128}
                style={{ width: '100%' }}
                disabled={useOptimizedParams && optimizeLoading}
              />
            </Form.Item>

            <Form.Item
              name="lora_alpha"
              label="LoRA Alpha"
              rules={[{ required: true, message: '请输入LoRA Alpha' }]}
              style={{ flex: 1 }}
            >
              <InputNumber
                min={1}
                max={256}
                style={{ width: '100%' }}
                disabled={useOptimizedParams && optimizeLoading}
              />
            </Form.Item>
          </div>

          <Form.Item
            name="lora_dropout"
            label="LoRA Dropout"
            rules={[{ required: true, message: '请输入LoRA Dropout' }]}
          >
            <InputNumber
              min={0}
              max={0.5}
              step={0.01}
              style={{ width: '100%' }}
              disabled={useOptimizedParams && optimizeLoading}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 训练详情抽屉 */}
      <Drawer
        title="训练任务详情"
        placement="right"
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
        width={600}
      >
        {selectedJob && (
          <div>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="任务ID">{selectedJob.id}</Descriptions.Item>
              <Descriptions.Item label="数据集ID">{selectedJob.dataset_id}</Descriptions.Item>
              <Descriptions.Item label="模型">{selectedJob.model_name}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedJob.status)}>
                  {getStatusText(selectedJob.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={Math.round(selectedJob.progress_percentage || 0)} />
              </Descriptions.Item>
              <Descriptions.Item label="当前轮次">{selectedJob.current_epoch || 0}</Descriptions.Item>
              <Descriptions.Item label="训练损失">{selectedJob.train_loss?.toFixed(4) || '-'}</Descriptions.Item>
              <Descriptions.Item label="验证损失">{selectedJob.val_loss?.toFixed(4) || '-'}</Descriptions.Item>
              <Descriptions.Item label="学习率">{selectedJob.learning_rate}</Descriptions.Item>
              <Descriptions.Item label="批次大小">{selectedJob.batch_size}</Descriptions.Item>
              <Descriptions.Item label="训练轮数">{selectedJob.epochs}</Descriptions.Item>
              <Descriptions.Item label="LoRA Rank">{selectedJob.lora_r}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{new Date(selectedJob.created_at).toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="开始时间">{selectedJob.started_at ? new Date(selectedJob.started_at).toLocaleString() : '-'}</Descriptions.Item>
              <Descriptions.Item label="完成时间">{selectedJob.completed_at ? new Date(selectedJob.completed_at).toLocaleString() : '-'}</Descriptions.Item>
              {selectedJob.error_message && (
                <Descriptions.Item label="错误信息">
                  <Alert message={selectedJob.error_message} type="error" />
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default IntelligentTrainingManagement;