/**
 * 样本管理页面 - 极简主义设计，毛玻璃效果
 * 
 * 设计原则：
 * - 极简主义：大片留白，移除多余装饰
 * - 毛玻璃效果：backdrop-filter 和半透明背景
 * - 视觉层级：大号数据，小号辅助信息
 * - Bento Grid：便当格布局风格
 * - 现代字体：Inter 字体系统
 * 
 * 功能：
 * - 数据集管理：上传、查看、预览、删除（支持批量）
 * - 样本管理：查看、预览、删除（支持批量）、样本生成
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Upload,
  message,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Progress,
  Statistic,
  Tabs,
  Typography,
  Tooltip,
  Empty,
  Checkbox,
} from 'antd';
import {
  UploadOutlined,
  EyeOutlined,
  DeleteOutlined,
  DownloadOutlined,
  FileTextOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import SampleGenerationTab from '../components/SampleGenerationTab';

const { Text } = Typography;
const { TextArea } = Input;

interface Dataset {
  id: number;
  filename: string;
  description?: string;
  file_path: string;
  record_count: number;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  status: string;
  created_at: string;
  updated_at: string;
  file_size: number;
  quality_score?: number;
  uploaded_by: number;
}

interface SampleData {
  id: number;
  question: string;
  answer: string;
  question_type: string;
  split_type: string;
  dataset_id: number;
  source_record_id?: number;
  generated_at: string;
}

const SampleManagement: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [samples, setSamples] = useState<SampleData[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [uploadForm] = Form.useForm();
  const [activeTab, setActiveTab] = useState('datasets');
  
  // 批量选择状态
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<number[]>([]);
  const [selectedSampleIds, setSelectedSampleIds] = useState<number[]>([]);
  
  // 样本详情查看状态
  const [sampleDetailVisible, setSampleDetailVisible] = useState(false);
  const [selectedSample, setSelectedSample] = useState<SampleData | null>(null);
  
  // 样本管理的数据集选择状态
  const [selectedDatasetForSamples, setSelectedDatasetForSamples] = useState<Dataset | null>(null);

  // 获取数据集列表
  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/datasets', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setDatasets(data || []);
      } else {
        message.error('获取数据集失败');
      }
    } catch (error) {
      console.error('获取数据集失败:', error);
      message.error('获取数据集失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取样本数据 - 现在必须指定数据集ID
  const fetchSamples = async (datasetId: number) => {
    if (!datasetId) {
      setSamples([]);
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/qa-pairs/${datasetId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (response.ok) {
        setSamples(data || []);
      } else {
        message.error('获取样本数据失败');
        setSamples([]);
      }
    } catch (error) {
      console.error('获取样本数据失败:', error);
      message.error('获取样本数据失败');
      setSamples([]);
    } finally {
      setLoading(false);
    }
  };

  // 上传数据集
  const handleUpload = async (values: any) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', values.file.file);
      formData.append('name', values.name);
      formData.append('description', values.description || '');

      const response = await fetch('/api/v1/datasets/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });
      
      if (response.ok) {
        message.success('数据集上传成功');
        uploadForm.resetFields();
        fetchDatasets();
      } else {
        const errorData = await response.json();
        message.error('上传失败: ' + (errorData.detail || errorData.error_message || '未知错误'));
      }
    } catch (error) {
      console.error('上传失败:', error);
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
  };

  // 预览数据集
  const handlePreview = async (dataset: Dataset) => {
    try {
      const response = await fetch(`/api/v1/datasets/${dataset.id}/preview`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setPreviewData(data || []);
        setSelectedDataset(dataset);
        setPreviewVisible(true);
      } else {
        message.error('预览失败');
      }
    } catch (error) {
      console.error('预览失败:', error);
      message.error('预览失败');
    }
  };

  // 删除单个数据集
  const handleDeleteDataset = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个数据集吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/datasets/${id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
          });
          
          if (response.ok) {
            message.success('删除成功');
            fetchDatasets();
            setSelectedDatasetIds(selectedDatasetIds.filter(selectedId => selectedId !== id));
          } else {
            message.error('删除失败');
          }
        } catch (error) {
          console.error('删除失败:', error);
          message.error('删除失败');
        }
      },
    });
  };

  // 批量删除数据集
  const handleBatchDeleteDatasets = async () => {
    if (selectedDatasetIds.length === 0) {
      message.warning('请选择要删除的数据集');
      return;
    }

    Modal.confirm({
      title: '批量删除确认',
      content: `确定要删除选中的 ${selectedDatasetIds.length} 个数据集吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const promises = selectedDatasetIds.map(id =>
            fetch(`/api/v1/datasets/${id}`, {
              method: 'DELETE',
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              },
            })
          );

          await Promise.all(promises);
          message.success(`成功删除 ${selectedDatasetIds.length} 个数据集`);
          fetchDatasets();
          setSelectedDatasetIds([]);
        } catch (error) {
          console.error('批量删除失败:', error);
          message.error('批量删除失败');
        }
      },
    });
  };

  // 批量删除样本 - 使用单个删除API逐个删除
  const handleBatchDeleteSamples = async () => {
    if (selectedSampleIds.length === 0) {
      message.warning('请选择要删除的样本');
      return;
    }

    Modal.confirm({
      title: '批量删除确认',
      content: `确定要删除选中的 ${selectedSampleIds.length} 个样本吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          let successCount = 0;
          let failCount = 0;
          
          // 逐个删除选中的样本
          for (const sampleId of selectedSampleIds) {
            try {
              const response = await fetch(`/api/v1/qa-pairs/single/${sampleId}`, {
                method: 'DELETE',
                headers: {
                  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                },
              });
              
              if (response.ok) {
                successCount++;
              } else {
                failCount++;
              }
            } catch (error) {
              failCount++;
            }
          }
          
          if (successCount > 0) {
            message.success(`成功删除 ${successCount} 个样本`);
            // 重新加载当前数据集的样本
            if (selectedDatasetForSamples) {
              fetchSamples(selectedDatasetForSamples.id);
            }
            setSelectedSampleIds([]);
          }
          
          if (failCount > 0) {
            message.warning(`${failCount} 个样本删除失败`);
          }
        } catch (error) {
          console.error('批量删除失败:', error);
          message.error('批量删除失败');
        }
      },
    });
  };

  // 删除单个样本 - 使用新的单个QA对删除API
  const handleDeleteSample = async (sampleId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个样本吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/qa-pairs/single/${sampleId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
          });
          
          if (response.ok) {
            message.success('样本删除成功');
            // 重新加载当前数据集的样本
            if (selectedDatasetForSamples) {
              fetchSamples(selectedDatasetForSamples.id);
            }
            setSelectedSampleIds(selectedSampleIds.filter(id => id !== sampleId));
          } else {
            const errorData = await response.json();
            message.error('删除失败: ' + (errorData.detail || '未知错误'));
          }
        } catch (error) {
          console.error('删除失败:', error);
          message.error('删除失败');
        }
      },
    });
  };

  // 查看样本详情
  const handleViewSample = (sample: SampleData) => {
    setSelectedSample(sample);
    setSampleDetailVisible(true);
  };

  // 选择数据集用于样本管理
  const handleSelectDatasetForSamples = (dataset: Dataset) => {
    setSelectedDatasetForSamples(dataset);
    setSelectedSampleIds([]); // 清空之前的选择
    fetchSamples(dataset.id);
  };

  // 清空数据集选择
  const handleClearDatasetSelection = () => {
    setSelectedDatasetForSamples(null);
    setSamples([]);
    setSelectedSampleIds([]);
  };

  // 键盘快捷键处理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.altKey) {
        switch (event.key.toLowerCase()) {
          case 'u':
            event.preventDefault();
            setActiveTab('datasets');
            break;
          case 't':
            event.preventDefault();
            const tabs = ['datasets', 'samples'];
            const currentIndex = tabs.indexOf(activeTab);
            const nextIndex = (currentIndex + 1) % tabs.length;
            setActiveTab(tabs[nextIndex]);
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [activeTab]);

  useEffect(() => {
    fetchDatasets();
    // 不再自动加载所有样本，需要用户先选择数据集
  }, []);

  // 数据集表格列
  const datasetColumns = [
    {
      title: (
        <Checkbox
          indeterminate={selectedDatasetIds.length > 0 && selectedDatasetIds.length < datasets.length}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedDatasetIds(datasets.map(d => d.id));
            } else {
              setSelectedDatasetIds([]);
            }
          }}
          checked={datasets.length > 0 && selectedDatasetIds.length === datasets.length}
        />
      ),
      dataIndex: 'selection',
      key: 'selection',
      width: 50,
      render: (_: any, record: Dataset) => (
        <Checkbox
          checked={selectedDatasetIds.includes(record.id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedDatasetIds([...selectedDatasetIds, record.id]);
            } else {
              setSelectedDatasetIds(selectedDatasetIds.filter(id => id !== record.id));
            }
          }}
        />
      ),
    },
    {
      title: '名称',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string, record: Dataset) => (
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description || '无描述'}
          </Text>
        </div>
      ),
    },
    {
      title: '记录数',
      dataIndex: 'total_records',
      key: 'total_records',
      width: 100,
      render: (count: number) => (
        <Statistic
          value={count || 0}
          valueStyle={{ fontSize: 14 }}
          prefix={<FileTextOutlined />}
        />
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => {
        const sizeInMB = (size / (1024 * 1024)).toFixed(2);
        return `${sizeInMB} MB`;
      },
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 120,
      render: (score: number) => (
        <Progress
          percent={Math.round((score || 0) * 100)}
          size="small"
          status={(score || 0) > 0.8 ? 'success' : (score || 0) > 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          'active': { color: 'green', text: '活跃' },
          'processing': { color: 'blue', text: '处理中' },
          'error': { color: 'red', text: '错误' },
          'inactive': { color: 'default', text: '未激活' },
        };
        const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.inactive;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Dataset) => (
        <Space>
          <Tooltip title="预览数据">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record)}
            />
          </Tooltip>
          <Tooltip title="查看样本">
            <Button
              type="link"
              icon={<DatabaseOutlined />}
              onClick={() => {
                handleSelectDatasetForSamples(record);
                setActiveTab('samples');
              }}
            />
          </Tooltip>
          <Tooltip title="下载">
            <Button
              type="link"
              icon={<DownloadOutlined />}
              href={`/api/v1/datasets/${record.id}/download`}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteDataset(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 样本数据表格列
  const sampleColumns = [
    {
      title: (
        <Checkbox
          indeterminate={selectedSampleIds.length > 0 && selectedSampleIds.length < samples.length}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedSampleIds(samples.map(s => s.id));
            } else {
              setSelectedSampleIds([]);
            }
          }}
          checked={samples.length > 0 && selectedSampleIds.length === samples.length}
        />
      ),
      dataIndex: 'selection',
      key: 'selection',
      width: 50,
      render: (_: any, record: SampleData) => (
        <Checkbox
          checked={selectedSampleIds.includes(record.id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedSampleIds([...selectedSampleIds, record.id]);
            } else {
              setSelectedSampleIds(selectedSampleIds.filter(id => id !== record.id));
            }
          }}
        />
      ),
    },
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
      width: '25%',
      render: (text: string) => (
        <Tooltip title={text}>
          <div className="text-sm text-gray-700">{text}</div>
        </Tooltip>
      ),
    },
    {
      title: '答案',
      dataIndex: 'answer',
      key: 'answer',
      ellipsis: true,
      width: '25%',
      render: (text: string) => (
        <Tooltip title={text}>
          <div className="text-sm text-gray-700">{text}</div>
        </Tooltip>
      ),
    },
    {
      title: '问题类型',
      dataIndex: 'question_type',
      key: 'question_type',
      width: 120,
      render: (type: string) => {
        const typeConfig = {
          'exact': { color: 'blue', text: '精确匹配' },
          'fuzzy': { color: 'green', text: '模糊匹配' },
          'reverse': { color: 'orange', text: '反向查询' },
          'natural': { color: 'purple', text: '自然语言' },
        };
        const config = typeConfig[type as keyof typeof typeConfig];
        return config ? <Tag color={config.color}>{config.text}</Tag> : <Tag>{type}</Tag>;
      },
    },
    {
      title: '数据集',
      dataIndex: 'split_type',
      key: 'split_type',
      width: 100,
      render: (split: string) => {
        const splitConfig = {
          'train': { color: 'green', text: '训练集' },
          'val': { color: 'orange', text: '验证集' },
          'test': { color: 'red', text: '测试集' },
        };
        const config = splitConfig[split as keyof typeof splitConfig];
        return config ? <Tag color={config.color}>{config.text}</Tag> : <Tag>{split}</Tag>;
      },
    },
    {
      title: '数据集ID',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 100,
      render: (id: number) => <Tag color="cyan">#{id}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'generated_at',
      key: 'generated_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: SampleData) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => handleViewSample(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteSample(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 统计信息
  const totalSamples = samples.length;
  const trainSamples = samples.filter(s => s.split_type === 'train').length;
  const totalDatasets = datasets.length;
  const activeDatasets = datasets.filter(d => d.status === 'active').length;

  return (
    <div className="minimalist-container">
      <div className="content-area">
        {/* 页面标题 - 极简设计 */}
        <div className="section-spacing">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="title-primary">样本管理</h1>
              <p className="subtitle">管理训练样本数据集，支持上传、预览、质量评估和数据预处理</p>
            </div>
            <div className="flex items-center space-x-4">
              <Button 
                type="primary" 
                icon={<UploadOutlined />}
                onClick={() => setActiveTab('upload')}
                className="btn-primary-glass"
              >
                上传新数据集
              </Button>
              <div className="tag-primary">Alt+U</div>
            </div>
          </div>
        </div>

        {/* 核心指标 - Bento Grid 布局 */}
        <div className="bento-grid-4 section-spacing">
          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">总数据集</p>
                <p className="metric-primary">{totalDatasets}</p>
                <div className="flex items-center mt-3">
                  <DatabaseOutlined className="text-blue-500 text-sm mr-2" />
                  <span className="text-sm text-gray-600 font-medium">已创建数据集</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <DatabaseOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">活跃数据集</p>
                <p className="metric-primary">{activeDatasets}</p>
                <div className="mt-3">
                  <div className="progress-glass">
                    <div 
                      className="progress-bar" 
                      style={{ 
                        width: `${totalDatasets > 0 ? Math.round((activeDatasets / totalDatasets) * 100) : 0}%` 
                      }}
                    />
                  </div>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">总样本数</p>
                <p className="metric-primary">{totalSamples.toLocaleString()}</p>
                <div className="flex items-center mt-3">
                  <FileTextOutlined className="text-purple-500 text-sm mr-2" />
                  <span className="text-sm text-gray-600 font-medium">训练样本</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <FileTextOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">训练样本</p>
                <p className="metric-primary">{trainSamples}</p>
                <div className="flex items-center mt-3">
                  <span className="text-sm text-green-600 font-medium">
                    {totalSamples > 0 ? `${Math.round((trainSamples / totalSamples) * 100)}%` : '0%'} 占比
                  </span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <BarChartOutlined className="text-white text-2xl" />
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
                <DatabaseOutlined />
                <span>数据集管理</span>
              </div>
            } key="datasets">
              <div className="mb-6">
                <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      <DatabaseOutlined className="text-white text-sm" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-blue-900 mb-1">数据集管理</h4>
                      <p className="text-sm text-blue-800">
                        管理训练样本数据集，支持上传、预览、下载和删除操作。数据集用于模型训练和评估。
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button 
                        type="primary" 
                        icon={<UploadOutlined />}
                        onClick={() => {
                          Modal.info({
                            title: '上传数据集',
                            width: 600,
                            content: (
                              <div className="mt-4">
                                <Form
                                  form={uploadForm}
                                  layout="vertical"
                                  onFinish={handleUpload}
                                  className="space-y-4"
                                >
                                  <Form.Item
                                    name="name"
                                    label="数据集名称"
                                    rules={[{ required: true, message: '请输入数据集名称' }]}
                                  >
                                    <Input placeholder="输入数据集名称" />
                                  </Form.Item>

                                  <Form.Item
                                    name="description"
                                    label="描述"
                                  >
                                    <TextArea
                                      rows={3}
                                      placeholder="输入数据集描述（可选）"
                                    />
                                  </Form.Item>

                                  <Form.Item
                                    name="file"
                                    label="数据文件"
                                    rules={[{ required: true, message: '请选择数据文件' }]}
                                  >
                                    <Upload
                                      beforeUpload={() => false}
                                      accept=".csv,.json,.txt,.unl"
                                      maxCount={1}
                                    >
                                      <Button icon={<UploadOutlined />}>选择文件</Button>
                                    </Upload>
                                  </Form.Item>

                                  <Form.Item>
                                    <Button
                                      type="primary"
                                      htmlType="submit"
                                      loading={uploading}
                                      className="btn-primary-glass"
                                    >
                                      {uploading ? '上传中...' : '上传数据集'}
                                    </Button>
                                  </Form.Item>
                                </Form>
                              </div>
                            ),
                            onOk() {},
                          });
                        }}
                        className="btn-primary-glass"
                      >
                        上传数据集
                      </Button>
                      {selectedDatasetIds.length > 0 && (
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          onClick={handleBatchDeleteDatasets}
                        >
                          批量删除 ({selectedDatasetIds.length})
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="table-glass">
                <Table
                  columns={datasetColumns}
                  dataSource={datasets}
                  loading={loading}
                  rowKey="id"
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 个数据集`,
                  }}
                  locale={{ 
                    emptyText: (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="暂无数据集"
                      />
                    )
                  }}
                />
              </div>
            </Tabs.TabPane>

            <Tabs.TabPane tab={
              <div className="flex items-center space-x-2">
                <FileTextOutlined />
                <span>样本管理</span>
              </div>
            } key="samples">
              <div className="mb-6">
                <div className="p-4 bg-purple-50 bg-opacity-50 rounded-2xl border border-purple-200 border-opacity-50">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileTextOutlined className="text-white text-sm" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-purple-900 mb-1">样本管理</h4>
                      <p className="text-sm text-purple-800">
                        查看和管理具体的训练样本数据，包括问题、答案、类别和质量评估。支持样本生成功能。
                      </p>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button 
                        type="primary" 
                        icon={<PlayCircleOutlined />}
                        onClick={() => {
                          Modal.info({
                            title: '样本生成',
                            width: 1000,
                            content: (
                              <div className="mt-4">
                                <SampleGenerationTab datasets={datasets} onRefresh={fetchDatasets} />
                              </div>
                            ),
                            onOk() {},
                          });
                        }}
                        className="btn-primary-glass"
                      >
                        生成样本
                      </Button>
                      {selectedSampleIds.length > 0 && (
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          onClick={handleBatchDeleteSamples}
                        >
                          批量删除 ({selectedSampleIds.length})
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* 数据集选择器 */}
              <div className="mb-6">
                <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                        <DatabaseOutlined className="text-white text-sm" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-blue-900 mb-1">选择数据集</h4>
                        <p className="text-sm text-blue-800">
                          {selectedDatasetForSamples 
                            ? `当前数据集: ${selectedDatasetForSamples.filename} (${samples.length} 个样本)`
                            : '请选择一个数据集来查看和管理其样本'
                          }
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {selectedDatasetForSamples ? (
                        <Button
                          icon={<DeleteOutlined />}
                          onClick={handleClearDatasetSelection}
                          className="btn-secondary-glass"
                        >
                          清空选择
                        </Button>
                      ) : (
                        <div className="text-sm text-blue-600">
                          从上方数据集列表中点击"查看样本"按钮选择数据集
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="table-glass">
                {selectedDatasetForSamples ? (
                  <Table
                    columns={sampleColumns}
                    dataSource={samples}
                    loading={loading}
                    rowKey="id"
                    pagination={{
                      pageSize: 10,
                      showSizeChanger: true,
                      showQuickJumper: true,
                      showTotal: (total) => `共 ${total} 个样本`,
                    }}
                    locale={{ 
                      emptyText: (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="该数据集暂无样本数据"
                        />
                      )
                    }}
                  />
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="请先选择一个数据集"
                    style={{ padding: '60px 0' }}
                  />
                )}
              </div>
            </Tabs.TabPane>
          </Tabs>
        </Card>

        {/* 预览模态框 */}
        <Modal
          title={
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <EyeOutlined className="text-white text-sm" />
              </div>
              <span className="font-semibold">预览数据集: {selectedDataset?.filename}</span>
            </div>
          }
          visible={previewVisible}
          onCancel={() => setPreviewVisible(false)}
          width={1000}
          footer={[
            <Button key="close" onClick={() => setPreviewVisible(false)} className="btn-secondary-glass">
              关闭
            </Button>,
          ]}
          className="modal-glass"
        >
          <div className="mb-4">
            <div className="p-3 bg-blue-50 bg-opacity-50 rounded-xl border border-blue-200 border-opacity-50">
              <div className="text-sm text-blue-800">
                显示前100条记录，共 {selectedDataset?.total_records || 0} 条记录
              </div>
            </div>
          </div>
          
          <div className="table-glass">
            <Table
              columns={[
                { 
                  title: '银行名称', 
                  dataIndex: 'bank_name', 
                  key: 'bank_name', 
                  ellipsis: true,
                  width: '50%',
                  render: (text: string) => (
                    <div className="text-sm text-gray-700 font-medium">{text}</div>
                  )
                },
                { 
                  title: '银行联行号', 
                  dataIndex: 'bank_code', 
                  key: 'bank_code', 
                  width: '25%',
                  render: (text: string) => (
                    <div className="text-sm text-blue-600 font-mono">{text}</div>
                  )
                },
                { 
                  title: '清算行行号', 
                  dataIndex: 'clearing_code', 
                  key: 'clearing_code', 
                  width: '25%',
                  render: (text: string) => (
                    <div className="text-sm text-green-600 font-mono">{text}</div>
                  )
                },
              ]}
              dataSource={previewData}
              pagination={{ 
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
              size="small"
              scroll={{ y: 400 }}
            />
          </div>
        </Modal>

        {/* 样本详情模态框 */}
        <Modal
          title={
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
                <FileTextOutlined className="text-white text-sm" />
              </div>
              <span className="font-semibold">样本详情</span>
            </div>
          }
          visible={sampleDetailVisible}
          onCancel={() => setSampleDetailVisible(false)}
          width={800}
          footer={[
            <Button key="close" onClick={() => setSampleDetailVisible(false)} className="btn-secondary-glass">
              关闭
            </Button>,
          ]}
          className="modal-glass"
        >
          {selectedSample && (
            <div className="space-y-6">
              {/* 基本信息 */}
              <div className="p-4 bg-gray-50 bg-opacity-50 rounded-2xl border border-gray-200 border-opacity-50">
                <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <div className="w-6 h-6 bg-blue-500 rounded-lg flex items-center justify-center mr-2">
                    <span className="text-white text-xs font-bold">ID</span>
                  </div>
                  基本信息
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">样本ID</label>
                    <div className="text-sm text-gray-900 font-mono">#{selectedSample.id}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">数据集ID</label>
                    <div className="text-sm text-gray-900 font-mono">#{selectedSample.dataset_id}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">问题类型</label>
                    <div className="mt-1">
                      {(() => {
                        const typeConfig = {
                          'exact': { color: 'blue', text: '精确匹配' },
                          'fuzzy': { color: 'green', text: '模糊匹配' },
                          'reverse': { color: 'orange', text: '反向查询' },
                          'natural': { color: 'purple', text: '自然语言' },
                        };
                        const config = typeConfig[selectedSample.question_type as keyof typeof typeConfig];
                        return config ? <Tag color={config.color}>{config.text}</Tag> : <Tag>{selectedSample.question_type}</Tag>;
                      })()}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">数据集类型</label>
                    <div className="mt-1">
                      {(() => {
                        const splitConfig = {
                          'train': { color: 'green', text: '训练集' },
                          'val': { color: 'orange', text: '验证集' },
                          'test': { color: 'red', text: '测试集' },
                        };
                        const config = splitConfig[selectedSample.split_type as keyof typeof splitConfig];
                        return config ? <Tag color={config.color}>{config.text}</Tag> : <Tag>{selectedSample.split_type}</Tag>;
                      })()}
                    </div>
                  </div>
                </div>
                <div className="mt-4">
                  <label className="text-sm font-medium text-gray-600">创建时间</label>
                  <div className="text-sm text-gray-900">{new Date(selectedSample.generated_at).toLocaleString('zh-CN')}</div>
                </div>
              </div>

              {/* 问题内容 */}
              <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
                <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                  <div className="w-6 h-6 bg-blue-500 rounded-lg flex items-center justify-center mr-2">
                    <span className="text-white text-xs">Q</span>
                  </div>
                  问题内容
                </h4>
                <div className="p-3 bg-white bg-opacity-70 rounded-xl border border-blue-200 border-opacity-30">
                  <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                    {selectedSample.question}
                  </div>
                </div>
              </div>

              {/* 答案内容 */}
              <div className="p-4 bg-green-50 bg-opacity-50 rounded-2xl border border-green-200 border-opacity-50">
                <h4 className="font-semibold text-green-900 mb-3 flex items-center">
                  <div className="w-6 h-6 bg-green-500 rounded-lg flex items-center justify-center mr-2">
                    <span className="text-white text-xs">A</span>
                  </div>
                  答案内容
                </h4>
                <div className="p-3 bg-white bg-opacity-70 rounded-xl border border-green-200 border-opacity-30">
                  <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                    {selectedSample.answer}
                  </div>
                </div>
              </div>

              {/* 源记录信息 */}
              {selectedSample.source_record_id && (
                <div className="p-4 bg-yellow-50 bg-opacity-50 rounded-2xl border border-yellow-200 border-opacity-50">
                  <h4 className="font-semibold text-yellow-900 mb-3 flex items-center">
                    <div className="w-6 h-6 bg-yellow-500 rounded-lg flex items-center justify-center mr-2">
                      <span className="text-white text-xs">🔗</span>
                    </div>
                    源记录信息
                  </h4>
                  <div className="text-sm text-yellow-800">
                    源记录ID: #{selectedSample.source_record_id}
                  </div>
                </div>
              )}
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
};

export default SampleManagement;