/**
 * 训练管理页面
 * 
 * 功能：
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
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  StopOutlined,
  ReloadOutlined,
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

const TrainingManagement: React.FC = () => {
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);
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

  useEffect(() => {
    fetchJobs();
    fetchDatasets();
    
    // 每10秒自动刷新一次
    const interval = setInterval(fetchJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  // 创建训练任务
  const handleCreate = async (values: any) => {
    setCreateLoading(true);
    try {
      await trainingAPI.startTraining(values);
      message.success('训练任务创建成功');
      setCreateModalVisible(false);
      form.resetFields();
      fetchJobs();
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '创建失败');
    } finally {
      setCreateLoading(false);
    }
  };

  // 查看详情
  const handleViewDetail = async (job: TrainingJob) => {
    setSelectedJob(job);
    setDetailDrawerVisible(true);
  };

  // 停止训练
  const handleStop = async (job: TrainingJob) => {
    Modal.confirm({
      title: '确认停止训练',
      content: `确定要停止训练任务 #${job.id} 吗？`,
      onOk: async () => {
        try {
          await trainingAPI.stopTrainingJob(job.id);
          message.success('训练任务已停止');
          fetchJobs();
        } catch (error: any) {
          message.error(error.response?.data?.error_message || '停止失败');
        }
      },
    });
  };

  // 状态颜色映射
  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      pending: 'default',
      running: 'processing',
      completed: 'success',
      failed: 'error',
      stopped: 'warning',
    };
    return colorMap[status] || 'default';
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '数据集ID',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress_percentage',
      key: 'progress_percentage',
      width: 200,
      render: (progress: number, record: TrainingJob) => (
        <div>
          <Progress
            percent={Math.round(progress || 0)}
            size="small"
            status={
              record.status === 'failed' 
                ? 'exception' 
                : record.status === 'completed' 
                ? 'success' 
                : 'active'
            }
            strokeColor={
              record.status === 'running'
                ? { '0%': '#108ee9', '100%': '#87d068' }
                : undefined
            }
          />
          {record.current_epoch > 0 && (
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              Epoch: {record.current_epoch}/{record.epochs}
              {record.train_loss && ` | Loss: ${record.train_loss.toFixed(4)}`}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Loss',
      dataIndex: 'train_loss',
      key: 'train_loss',
      width: 100,
      render: (loss: number) => loss ? loss.toFixed(4) : '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: TrainingJob) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          {record.status === 'running' && (
            <Button
              type="link"
              size="small"
              danger
              icon={<StopOutlined />}
              onClick={() => handleStop(record)}
            >
              停止
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="训练管理"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              创建训练任务
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchJobs}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={jobs}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      {/* 创建训练任务对话框 */}
      <Modal
        title="创建训练任务"
        open={createModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setCreateModalVisible(false);
          form.resetFields();
        }}
        width={600}
        okText="创建"
        cancelText="取消"
        confirmLoading={createLoading}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{
            model_name: 'Qwen/Qwen2.5-1.5B',  // 使用1.5B模型，效果更好
            lora_r: 32,  // 增大LoRA秩，提升表达能力，减少幻觉
            lora_alpha: 64,  // 相应增大alpha
            lora_dropout: 0.05,
            learning_rate: 0.0002,
            epochs: 10,  // 增加训练轮数，让模型充分学习
            batch_size: 1,  // 保持为1以节省内存
          }}
        >
          <Form.Item
            name="dataset_id"
            label="数据集"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select
              placeholder="选择数据集"
              showSearch
              optionFilterProp="children"
            >
              {datasets.map((ds) => (
                <Select.Option key={ds.id} value={ds.id}>
                  {ds.filename} (ID: {ds.id}, 记录数: {ds.record_count})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="model_name"
            label="基础模型"
            rules={[{ required: true, message: '请选择基础模型' }]}
            tooltip="选择用于微调的Qwen基础模型"
            initialValue="Qwen/Qwen2.5-0.5B"
          >
            <Select placeholder="选择基础模型">
              <Select.Option value="Qwen/Qwen2.5-0.5B">
                Qwen2.5-0.5B (推荐，快速训练，中文优化)
              </Select.Option>
              <Select.Option value="Qwen/Qwen2.5-1.5B">
                Qwen2.5-1.5B (平衡性能)
              </Select.Option>
              <Select.Option value="Qwen/Qwen2.5-3B">
                Qwen2.5-3B (更好性能)
              </Select.Option>
              <Select.Option value="gpt2">
                GPT-2 (英文模型，兼容性好)
              </Select.Option>
              <Select.Option value="microsoft/DialoGPT-medium">
                DialoGPT-medium (对话模型)
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="lora_r"
            label="LoRA Rank"
            tooltip="LoRA适配器的秩，影响模型参数量"
            initialValue={8}
          >
            <InputNumber min={1} max={64} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="lora_alpha"
            label="LoRA Alpha"
            tooltip="LoRA缩放因子，通常设置为rank的2倍"
            initialValue={16}
          >
            <InputNumber min={1} max={128} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="lora_dropout"
            label="LoRA Dropout"
            tooltip="Dropout比例，用于防止过拟合"
            initialValue={0.05}
          >
            <InputNumber min={0} max={0.5} step={0.01} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="learning_rate"
            label="学习率"
            tooltip="控制模型训练的步长"
            initialValue={0.0002}
          >
            <InputNumber
              min={0.00001}
              max={0.01}
              step={0.00001}
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item
            name="epochs"
            label="训练轮数"
            tooltip="完整遍历训练数据的次数"
            initialValue={3}
          >
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="batch_size"
            label="批次大小"
            tooltip="每次训练使用的样本数量（建议使用1-2以节省内存）"
            initialValue={1}
          >
            <InputNumber min={1} max={32} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="训练任务详情"
        placement="right"
        width={600}
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
      >
        {selectedJob && (
          <>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="任务ID">{selectedJob.id}</Descriptions.Item>
              <Descriptions.Item label="模型名称">
                {selectedJob.model_name}
              </Descriptions.Item>
              <Descriptions.Item label="数据集ID">
                {selectedJob.dataset_id}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={getStatusColor(selectedJob.status)}>
                  {selectedJob.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress 
                  percent={Math.round(selectedJob.progress_percentage || 0)} 
                  status={
                    selectedJob.status === 'failed' 
                      ? 'exception' 
                      : selectedJob.status === 'completed' 
                      ? 'success' 
                      : 'active'
                  }
                  strokeColor={
                    selectedJob.status === 'running'
                      ? { '0%': '#108ee9', '100%': '#87d068' }
                      : undefined
                  }
                />
              </Descriptions.Item>
              <Descriptions.Item label="当前轮次">
                {selectedJob.current_epoch} / {selectedJob.epochs}
              </Descriptions.Item>
              <Descriptions.Item label="训练Loss">
                {selectedJob.train_loss ? selectedJob.train_loss.toFixed(4) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="验证Loss">
                {selectedJob.val_loss ? selectedJob.val_loss.toFixed(4) : '-'}
              </Descriptions.Item>
            </Descriptions>

            <h3 style={{ marginTop: 24, marginBottom: 16 }}>训练参数</h3>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="LoRA Rank">
                {selectedJob.lora_r}
              </Descriptions.Item>
              <Descriptions.Item label="学习率">
                {selectedJob.learning_rate}
              </Descriptions.Item>
              <Descriptions.Item label="训练轮数">
                {selectedJob.epochs}
              </Descriptions.Item>
              <Descriptions.Item label="批次大小">
                {selectedJob.batch_size}
              </Descriptions.Item>
            </Descriptions>

            <h3 style={{ marginTop: 24, marginBottom: 16 }}>时间线</h3>
            <Timeline>
              <Timeline.Item color="green">
                创建时间: {new Date(selectedJob.created_at).toLocaleString('zh-CN')}
              </Timeline.Item>
              {selectedJob.started_at && (
                <Timeline.Item color="blue">
                  开始时间: {new Date(selectedJob.started_at).toLocaleString('zh-CN')}
                </Timeline.Item>
              )}
              {selectedJob.completed_at && (
                <Timeline.Item color="green">
                  完成时间: {new Date(selectedJob.completed_at).toLocaleString('zh-CN')}
                </Timeline.Item>
              )}
              {selectedJob.error_message && (
                <Timeline.Item color="red">
                  错误信息: {selectedJob.error_message}
                </Timeline.Item>
              )}
            </Timeline>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default TrainingManagement;
