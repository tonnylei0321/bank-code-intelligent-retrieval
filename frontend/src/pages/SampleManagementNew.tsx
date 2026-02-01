/**
 * 样本管理页面（新版 - 三层结构）
 * 
 * 结构：
 * 1. 选择数据集
 * 2. 查看该数据集的样本集列表
 * 3. 点击样本集，查看具体样本
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  message,
  Space,
  Tag,
  Modal,
  Select,
  Empty,
  Popconfirm,
  Breadcrumb,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  EyeOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  ArrowLeftOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import SampleGenerationTab from '../components/SampleGenerationTab';

const { Option } = Select;

interface Dataset {
  id: number;
  filename: string;
  total_records: number;
  valid_records: number;
}

interface SampleSet {
  id: number;
  name: string;
  dataset_id: number;
  description: string;
  total_samples: number;
  train_samples: number;
  val_samples: number;
  test_samples: number;
  status: string;
  created_at: string;
  completed_at: string;
}

interface Sample {
  id: number;
  dataset_id: number;
  sample_set_id: number;
  question: string;
  answer: string;
  question_type: string;
  split_type: string;
  source_record_id: number;
  generated_at: string;
}

type ViewMode = 'dataset' | 'sample-sets' | 'samples';

const SampleManagementNew: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [sampleSets, setSampleSets] = useState<SampleSet[]>([]);
  const [selectedSampleSet, setSelectedSampleSet] = useState<SampleSet | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('dataset');
  const [generationModalVisible, setGenerationModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);
  const [selectedSampleSetIds, setSelectedSampleSetIds] = useState<number[]>([]);
  const [selectedSampleIds, setSelectedSampleIds] = useState<number[]>([]);

  const token = localStorage.getItem('access_token');

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      const response = await fetch('/api/v1/datasets', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDatasets(data);
      }
    } catch (error) {
      message.error('加载数据集失败');
    }
  };

  const loadSampleSets = async (datasetId: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/sample-sets/dataset/${datasetId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSampleSets(data);
      }
    } catch (error) {
      message.error('加载样本集失败');
    } finally {
      setLoading(false);
    }
  };

  const loadSamples = async (sampleSetId: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/sample-sets/${sampleSetId}/samples?limit=1000`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSamples(data.samples || []);
      }
    } catch (error) {
      message.error('加载样本失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDataset = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setViewMode('sample-sets');
    loadSampleSets(dataset.id);
  };

  const handleSelectSampleSet = (sampleSet: SampleSet) => {
    setSelectedSampleSet(sampleSet);
    setViewMode('samples');
    loadSamples(sampleSet.id);
  };

  const handleBackToDatasets = () => {
    setSelectedDataset(null);
    setSelectedSampleSet(null);
    setViewMode('dataset');
    setSampleSets([]);
    setSamples([]);
    setSelectedSampleSetIds([]);
    setSelectedSampleIds([]);
  };

  const handleBackToSampleSets = () => {
    setSelectedSampleSet(null);
    setViewMode('sample-sets');
    setSamples([]);
    setSelectedSampleIds([]);
  };

  const handleDeleteSampleSet = async (id: number) => {
    try {
      const response = await fetch(`/api/v1/sample-sets/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        message.success('删除成功');
        if (selectedDataset) {
          loadSampleSets(selectedDataset.id);
        }
      } else {
        message.error('删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchDeleteSampleSets = async () => {
    if (selectedSampleSetIds.length === 0) {
      message.warning('请选择要删除的样本集');
      return;
    }

    try {
      const response = await fetch('/api/v1/sample-sets/batch-delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ sample_set_ids: selectedSampleSetIds })
      });
      
      if (response.ok) {
        const result = await response.json();
        message.success(result.message);
        setSelectedSampleSetIds([]);
        if (selectedDataset) {
          loadSampleSets(selectedDataset.id);
        }
      } else {
        message.error('批量删除失败');
      }
    } catch (error) {
      message.error('批量删除失败');
    }
  };

  const handleDeleteSample = async (id: number) => {
    try {
      const response = await fetch(`/api/v1/qa-pairs/single/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        message.success('删除成功');
        if (selectedSampleSet) {
          loadSamples(selectedSampleSet.id);
        }
      } else {
        message.error('删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchDeleteSamples = async () => {
    if (selectedSampleIds.length === 0) {
      message.warning('请选择要删除的样本');
      return;
    }

    try {
      await Promise.all(
        selectedSampleIds.map(id =>
          fetch(`/api/v1/qa-pairs/single/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
          })
        )
      );
      message.success(`成功删除 ${selectedSampleIds.length} 个样本`);
      setSelectedSampleIds([]);
      if (selectedSampleSet) {
        loadSamples(selectedSampleSet.id);
      }
    } catch (error) {
      message.error('批量删除失败');
    }
  };

  const handleViewSample = (sample: Sample) => {
    setSelectedSample(sample);
    setDetailModalVisible(true);
  };

  const getQuestionTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'exact': '精确查询',
      'fuzzy': '模糊查询',
      'reverse': '反向查询',
      'natural': '自然语言',
    };
    return labels[type] || type;
  };

  const getSplitTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'train': 'blue',
      'val': 'orange',
      'test': 'green',
    };
    return colors[type] || 'default';
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'generating': 'blue',
      'completed': 'green',
      'failed': 'red',
    };
    return colors[status] || 'default';
  };

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      'generating': '生成中',
      'completed': '已完成',
      'failed': '失败',
    };
    return texts[status] || status;
  };

  // 样本集表格列
  const sampleSetColumns = [
    {
      title: '样本集名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: SampleSet) => (
        <div>
          <div className="font-medium">{text}</div>
          {record.description && (
            <div className="text-xs text-gray-500 mt-1">{record.description}</div>
          )}
        </div>
      ),
    },
    {
      title: '总样本数',
      dataIndex: 'total_samples',
      key: 'total_samples',
      width: 100,
      render: (count: number) => (
        <Tag color="blue">{count.toLocaleString()}</Tag>
      ),
    },
    {
      title: '训练集',
      dataIndex: 'train_samples',
      key: 'train_samples',
      width: 80,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '验证集',
      dataIndex: 'val_samples',
      key: 'val_samples',
      width: 80,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: '测试集',
      dataIndex: 'test_samples',
      key: 'test_samples',
      width: 80,
      render: (count: number) => count.toLocaleString(),
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
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: SampleSet) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleSelectSampleSet(record)}
          >
            查看样本
          </Button>
          <Popconfirm
            title="确定要删除这个样本集吗？"
            description="删除样本集将同时删除其包含的所有样本"
            onConfirm={() => handleDeleteSampleSet(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 样本表格列
  const sampleColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
      render: (text: string) => (
        <div className="max-w-md truncate" title={text}>
          {text}
        </div>
      ),
    },
    {
      title: '问题类型',
      dataIndex: 'question_type',
      key: 'question_type',
      width: 120,
      render: (type: string) => (
        <Tag color="blue">{getQuestionTypeLabel(type)}</Tag>
      ),
    },
    {
      title: '数据集划分',
      dataIndex: 'split_type',
      key: 'split_type',
      width: 120,
      render: (type: string) => (
        <Tag color={getSplitTypeColor(type)}>
          {type === 'train' ? '训练集' : type === 'val' ? '验证集' : '测试集'}
        </Tag>
      ),
    },
    {
      title: '生成时间',
      dataIndex: 'generated_at',
      key: 'generated_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: Sample) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewSample(record)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定要删除这个样本吗？"
            onConfirm={() => handleDeleteSample(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const rowSelection = {
    selectedRowKeys: viewMode === 'sample-sets' ? selectedSampleSetIds : selectedSampleIds,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      if (viewMode === 'sample-sets') {
        setSelectedSampleSetIds(newSelectedRowKeys as number[]);
      } else {
        setSelectedSampleIds(newSelectedRowKeys as number[]);
      }
    },
  };

  return (
    <div className="p-6">
      {/* 页面标题和面包屑 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="title-primary">样本管理</h1>
            <Breadcrumb className="mt-2">
              <Breadcrumb.Item>
                <a onClick={handleBackToDatasets}>数据集</a>
              </Breadcrumb.Item>
              {selectedDataset && (
                <Breadcrumb.Item>
                  <a onClick={handleBackToSampleSets}>{selectedDataset.filename}</a>
                </Breadcrumb.Item>
              )}
              {selectedSampleSet && (
                <Breadcrumb.Item>{selectedSampleSet.name}</Breadcrumb.Item>
              )}
            </Breadcrumb>
          </div>
          {viewMode === 'sample-sets' && (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => setGenerationModalVisible(true)}
              className="btn-primary-glass"
            >
              生成样本
            </Button>
          )}
        </div>
      </div>

      {/* 数据集选择视图 */}
      {viewMode === 'dataset' && (
        <Card className="glass-card">
          <div className="mb-4">
            <h3 className="text-lg font-semibold mb-2">选择数据集</h3>
            <p className="text-gray-600">请选择一个数据集以查看其样本集</p>
          </div>
          <Select
            style={{ width: '100%' }}
            placeholder="请选择数据集"
            size="large"
            onChange={(value) => {
              const dataset = datasets.find(d => d.id === value);
              if (dataset) {
                handleSelectDataset(dataset);
              }
            }}
            suffixIcon={<DatabaseOutlined />}
          >
            {datasets.map(dataset => (
              <Option key={dataset.id} value={dataset.id}>
                <div className="flex items-center justify-between">
                  <span>{dataset.filename}</span>
                  <span className="text-gray-500 text-sm">
                    ({dataset.total_records} 条记录)
                  </span>
                </div>
              </Option>
            ))}
          </Select>
        </Card>
      )}

      {/* 样本集列表视图 */}
      {viewMode === 'sample-sets' && (
        <>
          {/* 统计卡片 */}
          <Row gutter={16} className="mb-6">
            <Col span={6}>
              <Card className="glass-card">
                <Statistic
                  title="样本集数量"
                  value={sampleSets.length}
                  prefix={<FolderOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="glass-card">
                <Statistic
                  title="总样本数"
                  value={sampleSets.reduce((sum, set) => sum + set.total_samples, 0)}
                  prefix={<FileTextOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="glass-card">
                <Statistic
                  title="已完成"
                  value={sampleSets.filter(s => s.status === 'completed').length}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="glass-card">
                <Statistic
                  title="生成中"
                  value={sampleSets.filter(s => s.status === 'generating').length}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 批量操作栏 */}
          {selectedSampleSetIds.length > 0 && (
            <div className="mb-4 p-4 bg-blue-50 rounded-lg flex items-center justify-between">
              <span className="text-blue-900">
                已选择 <strong>{selectedSampleSetIds.length}</strong> 个样本集
              </span>
              <Popconfirm
                title={`确定要删除选中的 ${selectedSampleSetIds.length} 个样本集吗？`}
                description="删除样本集将同时删除其包含的所有样本"
                onConfirm={handleBatchDeleteSampleSets}
                okText="确定"
                cancelText="取消"
              >
                <Button danger icon={<DeleteOutlined />}>
                  批量删除
                </Button>
              </Popconfirm>
            </div>
          )}

          {/* 样本集列表 */}
          <Card 
            className="glass-card"
            title={
              <div className="flex items-center justify-between">
                <span>样本集列表</span>
                <Space>
                  <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={handleBackToDatasets}
                  >
                    返回
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => selectedDataset && loadSampleSets(selectedDataset.id)}
                    loading={loading}
                  >
                    刷新
                  </Button>
                </Space>
              </div>
            }
          >
            <Table
              rowSelection={rowSelection}
              columns={sampleSetColumns}
              dataSource={sampleSets}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 个样本集`,
              }}
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无样本集，请先生成样本"
                  />
                )
              }}
            />
          </Card>
        </>
      )}

      {/* 样本列表视图 */}
      {viewMode === 'samples' && selectedSampleSet && (
        <>
          {/* 样本集信息卡片 */}
          <Card className="glass-card mb-6">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="总样本数"
                  value={selectedSampleSet.total_samples}
                  prefix={<FileTextOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="训练集"
                  value={selectedSampleSet.train_samples}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="验证集"
                  value={selectedSampleSet.val_samples}
                  valueStyle={{ color: '#faad14' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="测试集"
                  value={selectedSampleSet.test_samples}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
            </Row>
          </Card>

          {/* 批量操作栏 */}
          {selectedSampleIds.length > 0 && (
            <div className="mb-4 p-4 bg-purple-50 rounded-lg flex items-center justify-between">
              <span className="text-purple-900">
                已选择 <strong>{selectedSampleIds.length}</strong> 个样本
              </span>
              <Popconfirm
                title={`确定要删除选中的 ${selectedSampleIds.length} 个样本吗？`}
                onConfirm={handleBatchDeleteSamples}
                okText="确定"
                cancelText="取消"
              >
                <Button danger icon={<DeleteOutlined />}>
                  批量删除
                </Button>
              </Popconfirm>
            </div>
          )}

          {/* 样本列表 */}
          <Card 
            className="glass-card"
            title={
              <div className="flex items-center justify-between">
                <span>样本列表</span>
                <Space>
                  <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={handleBackToSampleSets}
                  >
                    返回样本集
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={() => loadSamples(selectedSampleSet.id)}
                    loading={loading}
                  >
                    刷新
                  </Button>
                </Space>
              </div>
            }
          >
            <Table
              rowSelection={rowSelection}
              columns={sampleColumns}
              dataSource={samples}
              rowKey="id"
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 个样本`,
              }}
            />
          </Card>
        </>
      )}

      {/* 样本生成弹窗 */}
      <Modal
        title="生成样本"
        open={generationModalVisible}
        onCancel={() => setGenerationModalVisible(false)}
        footer={null}
        width={1200}
        destroyOnClose
      >
        {selectedDataset && (
          <SampleGenerationTab
            datasets={datasets}
            onRefresh={() => {
              loadDatasets();
              if (selectedDataset) {
                loadSampleSets(selectedDataset.id);
              }
            }}
          />
        )}
      </Modal>

      {/* 样本详情弹窗 */}
      <Modal
        title="样本详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedSample && (
          <div className="space-y-4">
            <div>
              <div className="text-gray-600 mb-1">样本ID</div>
              <div className="font-medium">{selectedSample.id}</div>
            </div>
            <div>
              <div className="text-gray-600 mb-1">问题类型</div>
              <Tag color="blue">{getQuestionTypeLabel(selectedSample.question_type)}</Tag>
            </div>
            <div>
              <div className="text-gray-600 mb-1">数据集划分</div>
              <Tag color={getSplitTypeColor(selectedSample.split_type)}>
                {selectedSample.split_type === 'train' ? '训练集' : 
                 selectedSample.split_type === 'val' ? '验证集' : '测试集'}
              </Tag>
            </div>
            <div>
              <div className="text-gray-600 mb-1">问题内容</div>
              <div className="p-3 bg-gray-50 rounded-lg">
                {selectedSample.question}
              </div>
            </div>
            <div>
              <div className="text-gray-600 mb-1">答案内容</div>
              <div className="p-3 bg-gray-50 rounded-lg whitespace-pre-wrap">
                {selectedSample.answer}
              </div>
            </div>
            <div>
              <div className="text-gray-600 mb-1">源记录ID</div>
              <div className="font-medium">{selectedSample.source_record_id}</div>
            </div>
            <div>
              <div className="text-gray-600 mb-1">生成时间</div>
              <div className="font-medium">
                {new Date(selectedSample.generated_at).toLocaleString()}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SampleManagementNew;
