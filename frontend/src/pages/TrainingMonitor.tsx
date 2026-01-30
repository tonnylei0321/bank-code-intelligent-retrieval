import React, { useState, useEffect, useCallback } from 'react';
import { Card, Table, Progress, Tag, Button, Space, message, Modal, Tooltip } from 'antd';
import { 
  StopOutlined, 
  ReloadOutlined, 
  DeleteOutlined,
  ExclamationCircleOutlined 
} from '@ant-design/icons';
import { trainingAPI } from '../services/api';

interface TrainingJob {
  id: number;
  dataset_id: number;
  created_by: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stopped';
  model_name: string;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  lora_r: number;
  lora_alpha: number;
  lora_dropout: number;
  current_epoch: number;
  total_steps: number;
  current_step: number;
  progress_percentage: number;
  train_loss: number | null;
  val_loss: number | null;
  val_accuracy: number | null;
  model_path: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

interface TrainingJobListResponse {
  jobs: TrainingJob[];
  total: number;
}

const { confirm } = Modal;

const TrainingMonitor: React.FC = () => {
  const [trainingJobs, setTrainingJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // 获取训练任务列表
  const fetchTrainingJobs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await trainingAPI.getTrainingJobs();
      const data = response.data as TrainingJobListResponse;
      setTrainingJobs(data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch training jobs:', error);
      message.error('获取训练任务列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始加载
  useEffect(() => {
    fetchTrainingJobs();
  }, [fetchTrainingJobs]);

  // 刷新数据
  const handleRefresh = useCallback(async () => {
    try {
      setRefreshing(true);
      await fetchTrainingJobs();
      message.success('刷新成功');
    } catch (error) {
      message.error('刷新失败');
    } finally {
      setRefreshing(false);
    }
  }, [fetchTrainingJobs]);

  // 停止训练任务
  // 停止训练任务
  const handleStopTraining = useCallback(async (jobId: number) => {
    try {
      await trainingAPI.stopTrainingJob(jobId);
      message.success('训练任务已停止');
      await fetchTrainingJobs(); // 刷新列表
    } catch (error) {
      console.error('Failed to stop training job:', error);
      message.error('停止训练任务失败');
    }
  }, [fetchTrainingJobs]);

  // 批量删除训练任务（临时解决方案）
  const handleBatchDelete = useCallback(() => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的训练任务');
      return;
    }

    const selectedJobs = trainingJobs.filter(job => selectedRowKeys.includes(job.id));
    const runningJobs = selectedJobs.filter(job => job.status === 'running' || job.status === 'pending');
    
    if (runningJobs.length > 0) {
      message.warning(`无法删除正在运行或等待中的训练任务：${runningJobs.map(j => `#${j.id}`).join(', ')}`);
      return;
    }

    confirm({
      title: '批量删除确认',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>确定要删除选中的 <strong>{selectedRowKeys.length}</strong> 个训练任务吗？</p>
          <p>任务ID：{selectedRowKeys.map(id => `#${id}`).join(', ')}</p>
          <p style={{ color: '#ff4d4f', marginTop: 8 }}>
            此操作将永久删除这些训练任务及其相关文件，无法恢复！
          </p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await trainingAPI.batchDeleteTrainingJobs(selectedRowKeys as number[]);
          message.success(`成功删除 ${selectedRowKeys.length} 个训练任务`);
          setSelectedRowKeys([]); // 清空选择
          await fetchTrainingJobs(); // 刷新列表
        } catch (error) {
          console.error('Failed to batch delete training jobs:', error);
          message.error('批量删除训练任务失败');
        }
      },
    });
  }, [selectedRowKeys, trainingJobs, fetchTrainingJobs]);

  // 删除训练任务（临时解决方案）
  const handleDeleteTraining = useCallback((job: TrainingJob) => {
    // 获取状态文本和颜色
    const getStatusConfig = (status: string) => {
      const statusMap = {
        pending: { color: 'default', text: '等待中' },
        running: { color: 'processing', text: '运行中' },
        completed: { color: 'success', text: '已完成' },
        failed: { color: 'error', text: '失败' },
        stopped: { color: 'warning', text: '已停止' }
      };
      return statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
    };

    const getStatusText = (status: string) => {
      return getStatusConfig(status).text;
    };

    // 检查是否可以删除
    if (job.status === 'running' || job.status === 'pending') {
      message.warning('无法删除正在运行或等待中的训练任务，请先停止任务');
      return;
    }

    confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <p>确定要删除训练任务 <strong>#{job.id}</strong> 吗？</p>
          <p>模型：{job.model_name}</p>
          <p>状态：{getStatusText(job.status)}</p>
          <p style={{ color: '#ff4d4f', marginTop: 8 }}>
            此操作将永久删除训练任务及其相关文件，无法恢复！
          </p>
        </div>
      ),
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await trainingAPI.deleteTrainingJob(job.id);
          message.success('训练任务已删除');
          await fetchTrainingJobs(); // 刷新列表
        } catch (error) {
          console.error('Failed to delete training job:', error);
          message.error('删除训练任务失败');
        }
      },
    });
  }, [fetchTrainingJobs]);

  // 获取状态文本和颜色
  const getStatusConfig = (status: string) => {
    const statusMap = {
      pending: { color: 'default', text: '等待中' },
      running: { color: 'processing', text: '运行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
      stopped: { color: 'warning', text: '已停止' }
    };
    return statusMap[status as keyof typeof statusMap] || { color: 'default', text: status };
  };

  const getStatusText = (status: string) => {
    return getStatusConfig(status).text;
  };

  // 格式化时间
  const formatTime = (timeStr: string | null) => {
    if (!timeStr) return '-';
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  // 计算进度百分比
  const getProgress = (job: TrainingJob) => {
    if (job.status === 'completed') return 100;
    if (job.status === 'failed' || job.status === 'stopped') return 0;
    if (job.total_steps === 0) return 0;
    return Math.round((job.current_step / job.total_steps) * 100);
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      render: (id: number) => `#${id}`,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 200,
      render: (modelName: string) => (
        <Tooltip title={modelName}>
          <div style={{ 
            maxWidth: 180, 
            overflow: 'hidden', 
            textOverflow: 'ellipsis', 
            whiteSpace: 'nowrap' 
          }}>
            {modelName}
          </div>
        </Tooltip>
      ),
    },
    {
      title: '数据集ID',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = getStatusConfig(status);
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '进度',
      key: 'progress',
      width: 120,
      render: (record: TrainingJob) => {
        const progress = getProgress(record);
        const status = record.status === 'failed' ? 'exception' : 
                      record.status === 'completed' ? 'success' : 'active';
        return (
          <Progress 
            percent={progress} 
            size="small" 
            status={status}
            format={(percent) => `${percent}%`}
          />
        );
      }
    },
    {
      title: '轮次',
      key: 'epoch',
      width: 80,
      render: (record: TrainingJob) => (
        record.status === 'pending' ? '-' : `${record.current_epoch}/${record.epochs}`
      )
    },
    {
      title: 'Loss',
      dataIndex: 'train_loss',
      key: 'train_loss',
      width: 100,
      render: (loss: number | null) => 
        loss !== null ? loss.toFixed(4) : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: formatTime,
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (record: TrainingJob) => (
        <Space size="small">
          {record.status === 'running' && (
            <Tooltip title="停止训练">
              <Button 
                size="small" 
                danger
                icon={<StopOutlined />}
                onClick={() => handleStopTraining(record.id)}
              >
                停止
              </Button>
            </Tooltip>
          )}
          {(record.status === 'completed' || record.status === 'failed' || record.status === 'stopped') && (
            <Tooltip title="删除任务">
              <Button 
                size="small" 
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteTraining(record)}
              >
                删除
              </Button>
            </Tooltip>
          )}
          {record.error_message && (
            <Tooltip title={record.error_message}>
              <Button size="small" type="link" danger>
                查看错误
              </Button>
            </Tooltip>
          )}
        </Space>
      )
    }
  ];

  return (
    <div>
      <Card 
        title="训练监控" 
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <Button 
                danger
                icon={<DeleteOutlined />}
                onClick={handleBatchDelete}
              >
                批量删除 ({selectedRowKeys.length})
              </Button>
            )}
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh}
              loading={refreshing}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={trainingJobs}
          rowKey="id"
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: (selectedKeys) => setSelectedRowKeys(selectedKeys),
            getCheckboxProps: (record) => ({
              disabled: record.status === 'running' || record.status === 'pending',
              name: record.id.toString(),
            }),
          }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default TrainingMonitor;