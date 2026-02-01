/**
 * 数据管理页面
 * 
 * 功能：
 * - 数据集列表展示
 * - 上传新数据集
 * - 查看数据集详情
 * - 预览数据内容
 * - 验证数据格式
 * - 查看统计信息
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Button,
  Upload,
  Modal,
  Drawer,
  message,
  Space,
  Tag,
  Descriptions,
  Spin,
  Statistic,
  Row,
  Col,
  Progress,
  InputNumber,
  Form,
  Alert,
  Divider,
  Radio,
  Input,
} from 'antd';
import {
  UploadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  ReloadOutlined,
  DeleteOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { dataAPI } from '../services/api';

interface Dataset {
  id: number;
  filename: string;
  file_path: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface DatasetStats {
  total_records: number;
  unique_bank_codes: number;
  unique_bank_names: number;
  data_quality_score: number;
}

interface LLMPrompt {
  id: number;
  llm_name: string;
  display_name: string;
  prompt_template: string;
  is_active: boolean;
  description?: string;
  created_at: string;
  updated_at: string;
}

const DataManagement: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [previewDrawerVisible, setPreviewDrawerVisible] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [datasetStats, setDatasetStats] = useState<DatasetStats | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  
  // 智能生成相关状态
  const [useSmartGeneration, setUseSmartGeneration] = useState(false);
  const [samplesPerBank, setSamplesPerBank] = useState(7);
  const [useLLM, setUseLLM] = useState(false);
  const [selectedLLMForGeneration, setSelectedLLMForGeneration] = useState('qwen'); // 用于生成的LLM选择
  const [sampleCount, setSampleCount] = useState(1000); // 指定条数
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState('');
  const [generating, setGenerating] = useState(false);

  // 并行生成相关状态
  const [parallelGenerating, setParallelGenerating] = useState(false);
  const [parallelProgress, setParallelProgress] = useState(0);
  const [parallelStatus, setParallelStatus] = useState('');
  const [parallelStats, setParallelStats] = useState<any>(null);

  // LLM提示词维护相关状态
  const [promptModalVisible, setPromptModalVisible] = useState(false);
  const [llmPrompts, setLlmPrompts] = useState<LLMPrompt[]>([]);
  const [selectedLLM, setSelectedLLM] = useState<string>('qwen');
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [promptLoading, setPromptLoading] = useState(false);

  // 获取数据集列表
  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const response = await dataAPI.getDatasets();
      setDatasets(response.data || []);
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '获取数据集列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  // 获取LLM提示词列表
  const fetchLLMPrompts = async () => {
    setPromptLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/llm-prompts', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const result = await response.json();
        setLlmPrompts(result.data || []);
        
        // 如果有提示词，设置第一个为默认选中
        if (result.data && result.data.length > 0) {
          const firstPrompt = result.data[0];
          setSelectedLLM(firstPrompt.llm_name);
          setCurrentPrompt(firstPrompt.prompt_template);
        }
      } else {
        message.error('获取LLM提示词失败');
      }
    } catch (error) {
      message.error('获取LLM提示词失败');
    } finally {
      setPromptLoading(false);
    }
  };

  // 初始化默认提示词
  const initDefaultPrompts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/llm-prompts/init-defaults', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const result = await response.json();
        message.success(result.message);
        fetchLLMPrompts(); // 重新获取列表
      } else {
        message.error('初始化默认提示词失败');
      }
    } catch (error) {
      message.error('初始化默认提示词失败');
    }
  };

  // 更新LLM提示词
  const updateLLMPrompt = async () => {
    if (!selectedLLM || !currentPrompt.trim()) {
      message.warning('请选择LLM并输入提示词');
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/api/v1/llm-prompts/${selectedLLM}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt_template: currentPrompt,
        }),
      });
      
      if (response.ok) {
        message.success('提示词更新成功');
        fetchLLMPrompts(); // 重新获取列表
      } else {
        message.error('提示词更新失败');
      }
    } catch (error) {
      message.error('提示词更新失败');
    }
  };

  // 处理LLM选择变化
  const handleLLMChange = (llmName: string) => {
    setSelectedLLM(llmName);
    const prompt = llmPrompts.find(p => p.llm_name === llmName);
    if (prompt) {
      setCurrentPrompt(prompt.prompt_template);
    }
  };

  // 打开提示词维护对话框
  const handleOpenPromptModal = () => {
    setPromptModalVisible(true);
    fetchLLMPrompts();
  };

  // 上传数据集
  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    // 获取文件对象
    const fileItem = fileList[0];
    const file = (fileItem.originFileObj || fileItem) as File;
    
    if (!file) {
      message.error('无法获取文件对象');
      return;
    }

    // 检查是否使用智能生成
    if (useSmartGeneration) {
      // 使用智能生成
      await handleSmartGeneration(file);
    } else {
      // 普通上传
      setUploading(true);
      try {
        await dataAPI.uploadDataset(file);
        message.success('数据集上传成功');
        setUploadModalVisible(false);
        setFileList([]);
        fetchDatasets();
      } catch (error: any) {
        message.error(error.response?.data?.error_message || '上传失败');
      } finally {
        setUploading(false);
      }
    }
  };

  // 并行生成训练数据
  const handleParallelGeneration = async (limit?: number) => {
    setParallelGenerating(true);
    setParallelProgress(0);
    setParallelStatus('启动并行生成任务...');

    try {
      // 调用并行生成 API
      const response = await fetch('http://localhost:8000/api/v1/training-data/generate-parallel', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ limit }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '启动并行生成失败');
      }

      const result = await response.json();
      // Task ID is stored in result.task_id for tracking
      setParallelStatus('任务已启动，正在初始化...');

      // 开始轮询进度
      pollParallelProgress(result.task_id);

    } catch (error: any) {
      message.error(error.message || '启动并行生成失败');
      setParallelGenerating(false);
      setParallelStatus('');
    }
  };

  // 轮询并行生成进度
  const pollParallelProgress = (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/training-data/progress/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });

        if (!response.ok) {
          clearInterval(pollInterval);
          setParallelGenerating(false);
          setParallelStatus('获取进度失败');
          return;
        }

        const result = await response.json();
        const progress = result.progress;

        setParallelProgress(progress.progress_percentage || 0);
        setParallelStats(progress);

        // 更新状态文本
        if (progress.status === 'running') {
          const eta = progress.eta_minutes ? ` (预计剩余 ${Math.ceil(progress.eta_minutes)} 分钟)` : '';
          setParallelStatus(
            `处理中: ${progress.processed_banks?.toLocaleString() || 0} / ${progress.total_banks?.toLocaleString() || 0} 银行${eta}`
          );
        } else if (progress.status === 'completed') {
          clearInterval(pollInterval);
          setParallelProgress(100);
          setParallelStatus('生成完成！');
          
          // 显示完成对话框
          Modal.success({
            title: '并行生成完成！',
            content: (
              <div>
                <p>✅ 成功处理 <strong>{progress.processed_banks?.toLocaleString()}</strong> 个银行</p>
                <p>✅ 生成 <strong>{progress.generated_samples?.toLocaleString()}</strong> 个训练样本</p>
                <p>✅ 失败 <strong>{progress.failed_banks?.toLocaleString() || 0}</strong> 个银行</p>
                <p>✅ 数据集 ID: <strong>{progress.dataset_id}</strong></p>
                <Divider />
                <p>现在可以使用这个数据集训练模型了！</p>
              </div>
            ),
            okText: '去训练',
            onOk: () => {
              // 使用React Router导航而不是window.location.href
              navigate('/training');
            },
          });

          setParallelGenerating(false);
          fetchDatasets();
        } else if (progress.status === 'failed') {
          clearInterval(pollInterval);
          setParallelGenerating(false);
          setParallelStatus(`生成失败: ${progress.error || '未知错误'}`);
          message.error('并行生成失败');
        }

      } catch (error) {
        // 继续轮询，不中断
      }
    }, 3000); // 每3秒轮询一次

    // 设置最大轮询时间（30分钟）
    setTimeout(() => {
      clearInterval(pollInterval);
      if (parallelGenerating) {
        setParallelGenerating(false);
        setParallelStatus('轮询超时');
        message.warning('进度轮询超时，请手动刷新查看结果');
      }
    }, 30 * 60 * 1000);
  };
  const handleSmartGeneration = async (file: File) => {
    setGenerating(true);
    setGenerationProgress(0);
    setGenerationStatus('开始上传文件...');

    try {
      // 创建 FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('generation_method', useLLM ? 'llm' : 'rule');
      formData.append('llm_name', selectedLLMForGeneration);
      formData.append('data_amount', useSmartGeneration ? 'limited' : 'full');
      formData.append('sample_count', sampleCount.toString());
      formData.append('samples_per_bank', samplesPerBank.toString());

      setGenerationStatus('启动智能生成任务...');
      setGenerationProgress(5);

      // 调用智能生成 API（现在返回任务ID）
      const response = await fetch('http://localhost:8000/api/v1/bank-data/upload-and-generate', {
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
      pollGenerationProgress(taskId);

    } catch (error: any) {
      message.error(error.message || '智能生成失败');
      setGenerationStatus('生成失败');
      setGenerating(false);
      setGenerationProgress(0);
      setGenerationStatus('');
    }
  };

  // 轮询智能生成进度
  const pollGenerationProgress = (taskId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/bank-data/generation-progress/${taskId}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });

        if (!response.ok) {
          throw new Error('获取进度失败');
        }

        const result = await response.json();
        const progress = result.data;

        setGenerationProgress(progress.progress_percentage || 0);

        // 更新状态文本
        if (progress.status === 'parsing') {
          setGenerationStatus('正在解析文件...');
        } else if (progress.status === 'creating_dataset') {
          setGenerationStatus('正在创建数据集...');
        } else if (progress.status === 'saving_banks') {
          setGenerationStatus('正在保存银行记录...');
        } else if (progress.status === 'generating') {
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
            title: '智能生成成功！',
            content: (
              <div>
                <p>✅ 成功处理 <strong>{progress.total_banks?.toLocaleString()}</strong> 个银行</p>
                <p>✅ 生成 <strong>{progress.generated_samples?.toLocaleString()}</strong> 个训练样本</p>
                <p>✅ 每个银行平均 <strong>{samplesPerBank}</strong> 个问法</p>
                <p>✅ 数据集 ID: <strong>{progress.dataset_id}</strong></p>
                <Divider />
                <p>现在可以使用这个数据集训练模型了！</p>
              </div>
            ),
            okText: '去训练',
            onOk: () => {
              // 使用React Router导航而不是window.location.href
              navigate('/training');
            },
          });

          setUploadModalVisible(false);
          setFileList([]);
          setUseSmartGeneration(false);
          setGenerating(false);
          setGenerationProgress(0);
          setGenerationStatus('');
          fetchDatasets();
        } else if (progress.status === 'failed') {
          clearInterval(pollInterval);
          setGenerating(false);
          setGenerationStatus(`生成失败: ${progress.error || '未知错误'}`);
          message.error('智能生成失败');
          setGenerationProgress(0);
          setGenerationStatus('');
        }

      } catch (error: any) {
        console.error('轮询进度失败:', error);
        // 继续轮询，不中断
      }
    }, 2000); // 每2秒轮询一次

    // 设置超时，30分钟后停止轮询
    setTimeout(() => {
      clearInterval(pollInterval);
      if (generating) {
        setGenerating(false);
        setGenerationProgress(0);
        setGenerationStatus('');
        message.warning('任务超时，请检查后台日志');
      }
    }, 30 * 60 * 1000);
  };

  // 查看数据集详情
  const handleViewDetail = async (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setDetailDrawerVisible(true);
    
    try {
      const response = await dataAPI.getDatasetStats(dataset.id);
      setDatasetStats(response.data);
    } catch (error: any) {
      message.error('获取统计信息失败');
    }
  };

  // 预览数据
  const handlePreview = async (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setPreviewDrawerVisible(true);
    
    try {
      const response = await dataAPI.previewDataset(dataset.id, 20);
      setPreviewData(response.data || []);
    } catch (error: any) {
      message.error('获取预览数据失败');
    }
  };

  // 验证数据集（带进度显示）
  const [validating, setValidating] = useState(false);
  const [validationProgress, setValidationProgress] = useState(0);
  const [validationStatus, setValidationStatus] = useState('');

  const handleValidate = async (dataset: Dataset) => {
    setValidating(true);
    setValidationProgress(0);
    setValidationStatus('开始验证数据集...');

    try {
      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setValidationProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 500);

      setValidationStatus('正在验证数据格式...');
      const response = await dataAPI.validateDataset(dataset.id);
      
      clearInterval(progressInterval);
      setValidationProgress(100);
      
      if (response.data.status === 'validated') {
        setValidationStatus('验证完成，正在生成问答对...');
        message.success(`数据集验证通过！有效记录: ${response.data.valid_records}/${response.data.total_records}`);
        
        // 等待QA生成完成（轮询检查）
        await pollQAGenerationStatus(dataset.id);
      } else {
        message.warning(`数据集验证失败: ${response.data.errors?.join(', ')}`);
      }
      
      fetchDatasets();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '验证失败');
    } finally {
      setValidating(false);
      setValidationProgress(0);
      setValidationStatus('');
    }
  };

  // 轮询QA生成状态
  const pollQAGenerationStatus = async (datasetId: number) => {
    return new Promise<void>((resolve) => {
      let attempts = 0;
      const maxAttempts = 60; // 最多轮询60次（约5分钟）
      
      const checkStatus = setInterval(async () => {
        attempts++;
        
        try {
          const response = await dataAPI.getDatasetStats(datasetId);
          const qaCount = response.data?.qa_pair_count || 0;
          
          if (qaCount > 0) {
            clearInterval(checkStatus);
            setValidationStatus('问答对生成完成！');
            message.success(`问答对生成完成！共生成 ${qaCount} 条问答对`);
            resolve();
          } else if (attempts >= maxAttempts) {
            clearInterval(checkStatus);
            setValidationStatus('问答对生成超时');
            message.warning('问答对生成可能需要更长时间，请稍后刷新查看');
            resolve();
          } else {
            setValidationStatus(`正在生成问答对... (${attempts * 5}秒)`);
          }
        } catch (error) {
          // 继续轮询
        }
      }, 5000); // 每5秒检查一次
    });
  };

  // 删除数据集
  const handleDelete = (dataset: Dataset) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除数据集 "${dataset.filename}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await dataAPI.deleteDataset(dataset.id);
          message.success('数据集已删除');
          fetchDatasets();
        } catch (error: any) {
          message.error(error.response?.data?.error_message || '删除失败');
        }
      },
    });
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
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '记录数',
      dataIndex: 'total_records',
      key: 'total_records',
      width: 120,
      render: (count: number, record: Dataset) => {
        if (record.status === 'validated' && record.valid_records > 0) {
          return `${record.valid_records.toLocaleString()} / ${count.toLocaleString()}`;
        }
        return count?.toLocaleString() || '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          uploaded: 'blue',
          validated: 'green',
          processing: 'orange',
          error: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '已验证',
      dataIndex: 'status',
      key: 'validated',
      width: 100,
      render: (status: string) =>
        status === 'validated' || status === 'indexed' ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            是
          </Tag>
        ) : (
          <Tag>否</Tag>
        ),
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => {
        if (!time) return '-';
        try {
          const date = new Date(time);
          if (isNaN(date.getTime())) return '-';
          return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          });
        } catch (error) {
          return '-';
        }
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: any, record: Dataset) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          {record.status === 'uploaded' && (
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleValidate(record)}
              loading={validating}
            >
              验证
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 预览数据的列定义
  const previewColumns = previewData.length > 0
    ? Object.keys(previewData[0]).map((key) => ({
        title: key,
        dataIndex: key,
        key: key,
        ellipsis: true,
      }))
    : [];

  return (
    <div>
      <Card
        title="数据管理"
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
              icon={<SettingOutlined />}
              onClick={handleOpenPromptModal}
              style={{ backgroundColor: '#1890ff', borderColor: '#1890ff' }}
            >
              LLM提示词维护
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchDatasets}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={datasets}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      {/* 验证进度对话框 */}
      <Modal
        title="数据验证进度"
        open={validating}
        footer={null}
        closable={false}
        width={500}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 20, marginBottom: 20 }}>
            <Progress
              percent={validationProgress}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          <p style={{ fontSize: 16, color: '#666' }}>{validationStatus}</p>
        </div>
      </Modal>

      {/* LLM提示词维护对话框 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>LLM提示词维护</span>
            <Tag color="blue">配置管理</Tag>
          </Space>
        }
        open={promptModalVisible}
        onOk={updateLLMPrompt}
        onCancel={() => {
          setPromptModalVisible(false);
          setCurrentPrompt('');
        }}
        width={800}
        okText="保存提示词"
        cancelText="取消"
        confirmLoading={promptLoading}
      >
        <div style={{ marginBottom: 16 }}>
          <Space>
            <span>选择LLM模型：</span>
            <Radio.Group 
              value={selectedLLM} 
              onChange={(e) => handleLLMChange(e.target.value)}
            >
              {llmPrompts.map(prompt => (
                <Radio.Button key={prompt.llm_name} value={prompt.llm_name}>
                  {prompt.display_name}
                </Radio.Button>
              ))}
            </Radio.Group>
            <Button 
              type="link" 
              onClick={initDefaultPrompts}
              loading={promptLoading}
            >
              初始化默认提示词
            </Button>
          </Space>
        </div>

        {selectedLLM && (
          <div>
            <div style={{ marginBottom: 8 }}>
              <strong>当前模型：</strong>
              {llmPrompts.find(p => p.llm_name === selectedLLM)?.display_name}
            </div>
            
            {llmPrompts.find(p => p.llm_name === selectedLLM)?.description && (
              <div style={{ marginBottom: 16, color: '#666', fontSize: 12 }}>
                {llmPrompts.find(p => p.llm_name === selectedLLM)?.description}
              </div>
            )}

            <div style={{ marginBottom: 8 }}>
              <strong>提示词模板：</strong>
              <span style={{ color: '#666', fontSize: 12, marginLeft: 8 }}>
                支持变量：{'{bank_name}'}, {'{bank_code}'}, {'{num_samples}'}
              </span>
            </div>
            
            <Input.TextArea
              value={currentPrompt}
              onChange={(e) => setCurrentPrompt(e.target.value)}
              rows={15}
              placeholder="请输入LLM提示词模板..."
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />

            <Alert
              message="提示词说明"
              description={
                <div>
                  <p><strong>变量说明：</strong></p>
                  <ul style={{ marginLeft: 20, marginTop: 8 }}>
                    <li><code>{'{bank_name}'}</code> - 银行完整名称</li>
                    <li><code>{'{bank_code}'}</code> - 银行联行号</li>
                    <li><code>{'{num_samples}'}</code> - 需要生成的样本数量</li>
                  </ul>
                  <p style={{ marginTop: 8 }}><strong>注意：</strong>提示词应该引导LLM返回JSON格式的结果，包含questions数组。</p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
        )}
      </Modal>

      {/* 上传对话框 */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            {useSmartGeneration ? '智能生成训练数据' : '上传数据集'}
            {useSmartGeneration && <Tag color="blue" icon={<RobotOutlined />}>AI 增强</Tag>}
          </Space>
        }
        open={uploadModalVisible}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
          setUseSmartGeneration(false);
        }}
        confirmLoading={uploading || generating}
        okText={useSmartGeneration ? '开始生成' : '上传'}
        cancelText="取消"
        width={600}
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
            
            // .unl 文件自动启用智能生成
            if (isUNL) {
              setUseSmartGeneration(true);
              message.info('检测到 .unl 文件，已自动启用智能生成模式');
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
          {useSmartGeneration ? (
            <span style={{ color: '#1890ff' }}>
              <ThunderboltOutlined /> .unl 文件将自动生成多样化训练样本
            </span>
          ) : (
            '文件应包含银行代码相关数据'
          )}
        </p>

        <Divider />

        {/* 训练数据生成选项 */}
        <Form layout="vertical">
          {/* 生成方式选择 */}
          <Form.Item 
            label={
              <Space>
                <RobotOutlined />
                <span>训练数据生成方式</span>
              </Space>
            }
          >
            <Radio.Group 
              value={useLLM ? 'llm' : 'rule'} 
              onChange={(e) => setUseLLM(e.target.value === 'llm')}
            >
              <Radio.Button value="llm">
                <Space>
                  <span>使用大模型生成训练数据</span>
                  <Tag color="orange">高质量</Tag>
                </Space>
              </Radio.Button>
              <Radio.Button value="rule">
                <Space>
                  <span>使用规则生成训练数据</span>
                  <Tag color="green">快速</Tag>
                </Space>
              </Radio.Button>
            </Radio.Group>
            
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              {useLLM ? (
                <div>
                  <p>🤖 使用大模型生成多样化训练样本</p>
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

          {/* LLM模型选择（仅在使用大模型时显示） */}
          {useLLM && (
            <Form.Item 
              label={
                <Space>
                  <RobotOutlined />
                  <span>选择LLM模型</span>
                </Space>
              }
            >
              <Radio.Group 
                value={selectedLLMForGeneration} 
                onChange={(e) => setSelectedLLMForGeneration(e.target.value)}
              >
                <Radio.Button value="qwen">
                  <Space>
                    <span>阿里通义千问</span>
                    <Tag color="blue">推荐</Tag>
                  </Space>
                </Radio.Button>
                <Radio.Button value="deepseek">
                  <Space>
                    <span>DeepSeek</span>
                    <Tag color="green">高质量</Tag>
                  </Space>
                </Radio.Button>
                <Radio.Button value="chatglm">
                  <Space>
                    <span>智谱ChatGLM</span>
                    <Tag color="orange">对话优化</Tag>
                  </Space>
                </Radio.Button>
              </Radio.Group>
              
              <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                {selectedLLMForGeneration === 'qwen' && (
                  <p>🎯 阿里巴巴开发，擅长中文理解和生成，推荐使用</p>
                )}
                {selectedLLMForGeneration === 'deepseek' && (
                  <p>🧠 DeepSeek开发，具有强大的推理能力，生成质量高</p>
                )}
                {selectedLLMForGeneration === 'chatglm' && (
                  <p>💬 智谱AI开发，适合中文对话场景，表达自然</p>
                )}
              </div>
            </Form.Item>
          )}

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
              value={useSmartGeneration ? 'limited' : 'full'} 
              onChange={(e) => setUseSmartGeneration(e.target.value === 'limited')}
            >
              <Radio.Button value="full">全量数据生成训练数据</Radio.Button>
              <Radio.Button value="limited">指定条数生成训练数据</Radio.Button>
            </Radio.Group>
            
            {useSmartGeneration && (
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
                    数据量：{useSmartGeneration ? `${sampleCount} 条记录（指定条数）` : '全量数据'}
                  </li>
                  <li>
                    预计生成样本：约 {useSmartGeneration ? `${Math.ceil(sampleCount / 10) * samplesPerBank}` : '根据文件大小确定'} 个
                  </li>
                  <li>
                    处理时间：{useLLM ? '约 30-60 分钟' : '约 2-5 分钟'}
                  </li>
                  <li>
                    生成方式：{useLLM ? `大模型生成（${selectedLLMForGeneration}）` : '规则生成（快速）'}
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

      {/* 并行生成进度对话框 */}
      <Modal
        title={
          <Space>
            <RobotOutlined />
            <span>并行训练数据生成进度</span>
            <Tag color="blue">多LLM并行</Tag>
          </Space>
        }
        open={parallelGenerating}
        footer={null}
        closable={false}
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <Spin size="large" tip="正在并行生成训练数据..." />
          </div>
          
          <div style={{ marginBottom: 20 }}>
            <Progress
              percent={Math.round(parallelProgress)}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          
          <p style={{ fontSize: 16, color: '#666', textAlign: 'center', marginBottom: 20 }}>
            {parallelStatus}
          </p>

          {parallelStats && (
            <div style={{ background: '#f5f5f5', padding: 16, borderRadius: 8 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic
                    title="已处理银行"
                    value={parallelStats.processed_banks || 0}
                    suffix={`/ ${parallelStats.total_banks || 0}`}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="生成样本数"
                    value={parallelStats.generated_samples || 0}
                  />
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Statistic
                    title="失败银行"
                    value={parallelStats.failed_banks || 0}
                    valueStyle={{ color: parallelStats.failed_banks > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Statistic
                    title="预计剩余"
                    value={parallelStats.eta_minutes ? Math.ceil(parallelStats.eta_minutes) : 0}
                    suffix="分钟"
                  />
                </Col>
              </Row>
            </div>
          )}

          <div style={{ marginTop: 16, fontSize: 12, color: '#999', textAlign: 'center' }}>
            <p>🚀 使用阿里通义千问 + DeepSeek 双LLM并行处理</p>
            <p>💡 每个银行生成7种不同问法，提升模型泛化能力</p>
          </div>
        </div>
      </Modal>

      {/* 生成进度对话框 */}
      <Modal
        title="智能生成进度"
        open={generating}
        footer={null}
        closable={false}
        width={500}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="large" tip="正在生成训练样本..." />
          <div style={{ marginTop: 20, marginBottom: 20 }}>
            <Progress
              percent={generationProgress}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          <p style={{ fontSize: 16, color: '#666' }}>{generationStatus}</p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 16 }}>
            {useLLM ? '使用大模型生成中，请耐心等待...' : '使用规则生成，速度较快...'}
          </p>
        </div>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="数据集详情"
        placement="right"
        width={600}
        onClose={() => {
          setDetailDrawerVisible(false);
          setDatasetStats(null);
        }}
        open={detailDrawerVisible}
      >
        {selectedDataset && (
          <>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="ID">{selectedDataset.id}</Descriptions.Item>
              <Descriptions.Item label="文件名">
                {selectedDataset.filename}
              </Descriptions.Item>
              <Descriptions.Item label="文件路径">
                {selectedDataset.file_path}
              </Descriptions.Item>
              <Descriptions.Item label="总记录数">
                {selectedDataset.total_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="有效记录">
                {selectedDataset.valid_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="无效记录">
                {selectedDataset.invalid_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color="blue">{selectedDataset.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="已验证">
                {selectedDataset.status === 'validated' || selectedDataset.status === 'indexed' ? '是' : '否'}
              </Descriptions.Item>
              <Descriptions.Item label="上传时间">
                {new Date(selectedDataset.created_at).toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </Descriptions.Item>
            </Descriptions>

            {datasetStats && (
              <>
                <h3 style={{ marginTop: 24, marginBottom: 16 }}>统计信息</h3>
                <Row gutter={16}>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="总记录数"
                        value={datasetStats.total_records}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="唯一银行代码"
                        value={datasetStats.unique_bank_codes}
                      />
                    </Card>
                  </Col>
                  <Col span={12} style={{ marginTop: 16 }}>
                    <Card>
                      <Statistic
                        title="唯一银行名称"
                        value={datasetStats.unique_bank_names}
                      />
                    </Card>
                  </Col>
                  <Col span={12} style={{ marginTop: 16 }}>
                    <Card>
                      <Statistic
                        title="数据质量分数"
                        value={datasetStats.data_quality_score}
                        precision={2}
                        suffix="/ 100"
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            )}
          </>
        )}
      </Drawer>

      {/* 预览抽屉 */}
      <Drawer
        title="数据预览"
        placement="right"
        width={800}
        onClose={() => {
          setPreviewDrawerVisible(false);
          setPreviewData([]);
        }}
        open={previewDrawerVisible}
      >
        {selectedDataset && (
          <>
            <p style={{ marginBottom: 16 }}>
              <strong>文件名：</strong>
              {selectedDataset.filename}
            </p>
            <Table
              columns={previewColumns}
              dataSource={previewData}
              rowKey={(record, index) => index?.toString() || '0'}
              pagination={false}
              scroll={{ x: 'max-content' }}
              size="small"
            />
            <p style={{ marginTop: 16, color: '#666' }}>
              显示前 {previewData.length} 条记录
            </p>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default DataManagement;
