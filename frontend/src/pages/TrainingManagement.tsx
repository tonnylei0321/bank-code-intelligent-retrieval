/**
 * 训练管理页面
 * 
 * 功能：
 * - 训练任务列表
 * - 创建训练任务
 * - 上传数据集并生成训练数据
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
  Upload,
  Radio,
  Switch,
  Alert,
  Divider,
  Spin,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EyeOutlined,
  StopOutlined,
  ReloadOutlined,
  UploadOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
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

  // 数据上传相关状态
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  
  // 训练数据生成选项
  const [generationMethod, setGenerationMethod] = useState<'llm' | 'rule'>('rule'); // 生成方式
  const [dataAmount, setDataAmount] = useState<'full' | 'limited'>('limited'); // 数据量
  const [sampleCount, setSampleCount] = useState(1000); // 指定条数
  const [samplesPerBank, setSamplesPerBank] = useState(7); // 每个银行生成样本数
  
  // 生成进度相关状态
  const [generating, setGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState('');
  const [generationStats, setGenerationStats] = useState<any>(null);

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

  // 上传数据集并生成训练数据
  const handleUploadAndGenerate = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    const fileItem = fileList[0];
    const file = (fileItem.originFileObj || fileItem) as File;
    
    if (!file) {
      message.error('无法获取文件对象');
      return;
    }

    setUploading(true);
    setGenerating(true);
    setGenerationProgress(0);
    setGenerationStatus('开始上传文件...');

    try {
      // 创建 FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('generation_method', generationMethod);
      formData.append('data_amount', dataAmount);
      formData.append('sample_count', sampleCount.toString());
      formData.append('samples_per_bank', samplesPerBank.toString());

      setGenerationStatus('启动训练数据生成任务...');
      setGenerationProgress(5);

      // 根据生成方式选择API端点
      const apiEndpoint = generationMethod === 'llm' 
        ? '/api/v1/training-data/generate-parallel'  // 使用大模型生成（主页面的并行生成）
        : '/api/v1/bank-data/upload-and-generate';   // 使用规则生成

      const response = await fetch(`http://localhost:8000${apiEndpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '生成失败');
      }

      const result = await response.json();
      const taskId = result.task_id;
      
      if (!taskId) {
        throw new Error('未获取到任务ID');
      }

      setGenerationStatus('任务已启动，开始监控进度...');
      setGenerationProgress(10);

      // 开始轮询进度
      pollGenerationProgress(taskId, generationMethod);

    } catch (error: any) {
      message.error(error.message || '生成失败');
      setGenerationStatus('生成失败');
      setGenerating(false);
      setUploading(false);
      setGenerationProgress(0);
      setGenerationStatus('');
    }
  };

  // 轮询生成进度
  const pollGenerationProgress = (taskId: string, method: 'llm' | 'rule') => {
    const progressEndpoint = method === 'llm' 
      ? `/api/v1/training-data/progress/${taskId}`
      : `/api/v1/bank-data/generation-progress/${taskId}`;

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000${progressEndpoint}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });

        if (!response.ok) {
          throw new Error('获取进度失败');
        }

        const result = await response.json();
        const progress = method === 'llm' ? result.progress : result.data;

        setGenerationProgress(progress.progress_percentage || 0);
        setGenerationStats(progress);

        // 更新状态文本
        if (progress.status === 'parsing') {
          setGenerationStatus('正在解析文件...');
        } else if (progress.status === 'creating_dataset') {
          setGenerationStatus('正在创建数据集...');
        } else if (progress.status === 'saving_banks') {
          setGenerationStatus('正在保存银行记录...');
        } else if (progress.status === 'generating' || progress.status === 'running') {
          const eta = progress.eta_minutes ? ` (预计剩余 ${Math.ceil(progress.eta_minutes)} 分钟)` : '';
          setGenerationStatus(
            `正在生成训练样本: ${progress.processed_banks?.toLocaleString() || 0} / ${progress.total_banks?.toLocaleString() || 0} 银行${eta}`
          );
        } else if (progress.status === 'completed') {
          clearInterval(pollInterval);
          setGenerationProgress(100);
          setGenerationStatus('生成完成！');
          
          // 显示成功信息
          Modal.success({
            title: `${method === 'llm' ? '大模型' : '规则'}生成成功！`,
            content: (
              <div>
                <p>✅ 成功处理 <strong>{progress.processed_banks?.toLocaleString() || progress.total_banks?.toLocaleString()}</strong> 个银行</p>
                <p>✅ 生成 <strong>{progress.generated_samples?.toLocaleString()}</strong> 个训练样本</p>
                <p>✅ 每个银行平均 <strong>{samplesPerBank}</strong> 个问法</p>
                <p>✅ 数据集 ID: <strong>{progress.dataset_id}</strong></p>
                <Divider />
                <p>现在可以使用这个数据集训练模型了！</p>
              </div>
            ),
            okText: '开始训练',
            onOk: () => {
              setUploadModalVisible(false);
              setCreateModalVisible(true);
              // 预选择刚生成的数据集
              form.setFieldsValue({ dataset_id: progress.dataset_id });
            },
          });

          setUploading(false);
          setGenerating(false);
          setGenerationProgress(0);
          setGenerationStatus('');
          fetchDatasets();
        } else if (progress.status === 'failed') {
          clearInterval(pollInterval);
          setGenerating(false);
          setUploading(false);
          setGenerationStatus(`生成失败: ${progress.error || '未知错误'}`);
          message.error('训练数据生成失败');
          setGenerationProgress(0);
          setGenerationStatus('');
        }

      } catch (error: any) {
        console.error('轮询进度失败:', error);
        // 继续轮询，不中断
      }
    }, 3000); // 每3秒轮询一次

    // 设置超时，30分钟后停止轮询
    setTimeout(() => {
      clearInterval(pollInterval);
      if (generating) {
        setGenerating(false);
        setUploading(false);
        setGenerationProgress(0);
        setGenerationStatus('');
        message.warning('任务超时，请检查后台日志');
      }
    }, 30 * 60 * 1000);
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
              icon={<UploadOutlined />}
              onClick={() => setUploadModalVisible(true)}
            >
              上传数据集
            </Button>
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

      {/* 上传数据集对话框 */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            <span>上传数据集并生成训练数据</span>
            <Tag color="blue" icon={<RobotOutlined />}>智能生成</Tag>
          </Space>
        }
        open={uploadModalVisible}
        onOk={handleUploadAndGenerate}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
          setGenerationMethod('rule');
          setDataAmount('limited');
          setSampleCount(1000);
        }}
        confirmLoading={uploading || generating}
        okText="开始生成"
        cancelText="取消"
        width={700}
      >
        <Upload
          fileList={fileList}
          accept=".csv,.xlsx,.xls,.unl"
          beforeUpload={(file) => {
            // 检查文件类型
            const isCSV = file.name.endsWith('.csv');
            const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
            const isUNL = file.name.endsWith('.unl');
            
            if (!isCSV && !isExcel && !isUNL) {
              message.error('只支持 CSV、Excel 和 .unl 文件');
              return false;
            }
            
            // .unl 文件提示
            if (isUNL) {
              message.info('检测到 .unl 文件，建议使用大模型生成获得更好效果');
            }
            
            setFileList([file as any]);
            return false;
          }}
          onRemove={() => {
            setFileList([]);
          }}
          maxCount={1}
        >
          <Button icon={<UploadOutlined />}>选择文件</Button>
        </Upload>
        
        <p style={{ marginTop: 16, color: '#666' }}>
          支持的文件格式：CSV、Excel (.xlsx, .xls)、.unl
          <br />
          文件应包含银行代码相关数据
        </p>

        <Divider />

        {/* 生成方式选择 */}
        <Form layout="vertical">
          <Form.Item 
            label={
              <Space>
                <RobotOutlined />
                <span>训练数据生成方式</span>
              </Space>
            }
          >
            <Radio.Group 
              value={generationMethod} 
              onChange={(e) => setGenerationMethod(e.target.value)}
            >
              <Radio value="llm">
                <Space>
                  <span>使用大模型生成训练数据</span>
                  <Tag color="orange">高质量</Tag>
                </Space>
              </Radio>
              <Radio value="rule">
                <Space>
                  <span>使用规则生成训练数据</span>
                  <Tag color="green">快速</Tag>
                </Space>
              </Radio>
            </Radio.Group>
            
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              {generationMethod === 'llm' ? (
                <div>
                  <p>🤖 使用阿里通义千问 + DeepSeek 双LLM并行处理</p>
                  <p>✨ 生成更自然、多样化的问法，准确率更高</p>
                  <p>⏱️ 处理时间：约 30-60 分钟（取决于数据量）</p>
                </div>
              ) : (
                <div>
                  <p>⚡ 使用预定义规则快速生成训练样本</p>
                  <p>📝 生成标准化问法，稳定可靠</p>
                  <p>⏱️ 处理时间：约 2-5 分钟</p>
                </div>
              )}
            </div>
          </Form.Item>

          {/* 数据量选择 */}
          <Form.Item 
            label={
              <Space>
                <ThunderboltOutlined />
                <span>数据量选择</span>
              </Space>
            }
          >
            <Radio.Group 
              value={dataAmount} 
              onChange={(e) => setDataAmount(e.target.value)}
            >
              <Radio value="full">全量数据生成训练数据</Radio>
              <Radio value="limited">指定条数生成训练数据</Radio>
            </Radio.Group>
            
            {dataAmount === 'limited' && (
              <div style={{ marginTop: 12 }}>
                <InputNumber
                  min={100}
                  max={50000}
                  value={sampleCount}
                  onChange={(value) => setSampleCount(value || 1000)}
                  style={{ width: 200 }}
                  addonAfter="条"
                />
                <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  系统将按银行维度随机抽取 {sampleCount} 条记录生成训练数据
                </p>
              </div>
            )}
          </Form.Item>

          {/* 每个银行生成样本数 */}
          <Form.Item 
            label="每个银行生成样本数"
            tooltip="建议 5-10 个，数量越多训练数据越丰富"
          >
            <InputNumber
              min={3}
              max={15}
              value={samplesPerBank}
              onChange={(value) => setSamplesPerBank(value || 7)}
              style={{ width: 200 }}
              addonAfter="个样本"
            />
            <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              推荐值：7（平衡质量和数量）
            </p>
          </Form.Item>

          {/* 预估信息 */}
          <Alert
            message="预估信息"
            description={
              <div>
                <p>基于当前设置：</p>
                <ul style={{ marginLeft: 20, marginTop: 8 }}>
                  <li>
                    数据量：{dataAmount === 'full' ? '全量数据' : `${sampleCount.toLocaleString()} 条记录`}
                  </li>
                  <li>
                    预计生成样本：约 {dataAmount === 'full' ? '根据文件大小确定' : `${Math.ceil(sampleCount / 10) * samplesPerBank}`} 个
                  </li>
                  <li>
                    处理时间：{generationMethod === 'llm' ? '约 30-60 分钟' : '约 2-5 分钟'}
                  </li>
                  <li>
                    生成方式：{generationMethod === 'llm' ? '大模型生成（高质量）' : '规则生成（快速）'}
                  </li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>

      {/* 生成进度对话框 */}
      <Modal
        title={
          <Space>
            <RobotOutlined />
            <span>训练数据生成进度</span>
            <Tag color="blue">{generationMethod === 'llm' ? '大模型生成' : '规则生成'}</Tag>
          </Space>
        }
        open={generating}
        footer={null}
        closable={false}
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <Spin size="large" tip="正在生成训练数据..." />
          </div>
          
          <div style={{ marginBottom: 20 }}>
            <Progress
              percent={Math.round(generationProgress)}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          
          <p style={{ fontSize: 16, color: '#666', textAlign: 'center', marginBottom: 20 }}>
            {generationStatus}
          </p>

          {generationStats && (
            <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="已处理银行"
                    value={generationStats.processed_banks || 0}
                    suffix={`/ ${generationStats.total_banks || 0}`}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="生成样本数"
                    value={generationStats.generated_samples || 0}
                  />
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Statistic
                    title="失败银行"
                    value={generationStats.failed_banks || 0}
                    valueStyle={{ color: generationStats.failed_banks > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Statistic
                    title="预计剩余"
                    value={generationStats.eta_minutes ? Math.ceil(generationStats.eta_minutes) : 0}
                    suffix="分钟"
                  />
                </Col>
              </Row>
            </div>
          )}

          <div style={{ marginTop: 16, fontSize: 12, color: '#999', textAlign: 'center' }}>
            <p>
              {generationMethod === 'llm' 
                ? '🚀 使用阿里通义千问 + DeepSeek 双LLM并行处理' 
                : '⚡ 使用规则引擎快速生成'}
            </p>
            <p>💡 每个银行生成{samplesPerBank}种不同问法，提升模型泛化能力</p>
          </div>
        </div>
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
