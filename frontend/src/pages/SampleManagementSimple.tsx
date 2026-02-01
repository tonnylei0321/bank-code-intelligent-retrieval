/**
 * 样本管理页面（简化版）
 * 
 * 功能：
 * - 选择数据集
 * - 查看样本列表
 * - 样本详情查看
 * - 样本删除
 * - 样本生成
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
} from 'antd';
import {
  EyeOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  DatabaseOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import SampleGenerationTab from '../components/SampleGenerationTab';

const { Option } = Select;

interface Dataset {
  id: number;
  filename: string;
  total_records: number;
  valid_records: number;
}

interface SampleData {
  id: number;
  dataset_id: number;
  question: string;
  answer: string;
  question_type: string;
  split_type: string;
  source_record_id: number;
  generated_at: string;
}

const SampleManagementSimple: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [samples, setSamples] = useState<SampleData[]>([]);
  const [loading, setLoading] = useState(false);
  const [generationModalVisible, setGenerationModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedSample, setSelectedSample] = useState<SampleData | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const token = localStorage.getItem('access_token');

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    if (selectedDataset) {
      loadSamples(selectedDataset.id);
    }
  }, [selectedDataset]);

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

  const loadSamples = async (datasetId: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/qa-pairs/${datasetId}?limit=1000`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSamples(data);
      }
    } catch (error) {
      message.error('加载样本失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewSample = (sample: SampleData) => {
    setSelectedSample(sample);
    setDetailModalVisible(true);
  };

  const handleDeleteSample = async (id: number) => {
    try {
      const response = await fetch(`/api/v1/qa-pairs/single/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        message.success('删除成功');
        if (selectedDataset) {
          loadSamples(selectedDataset.id);
        }
      } else {
        message.error('删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的样本');
      return;
    }

    try {
      await Promise.all(
        selectedRowKeys.map(id =>
          fetch(`/api/v1/qa-pairs/single/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
          })
        )
      );
      message.success(`成功删除 ${selectedRowKeys.length} 个样本`);
      setSelectedRowKeys([]);
      if (selectedDataset) {
        loadSamples(selectedDataset.id);
      }
    } catch (error) {
      message.error('批量删除失败');
    }
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

  const columns = [
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
      render: (_: any, record: SampleData) => (
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
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys);
    },
  };

  return (
    <div className="p-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="title-primary">样本管理</h1>
            <p className="subtitle">查看和管理训练样本，支持样本生成和质量评估</p>
          </div>
        </div>
      </div>

      {/* 样本管理说明卡片 */}
      <div className="mb-6">
        <div className="p-4 bg-gradient-to-r from-purple-50 to-pink-50 bg-opacity-50 rounded-2xl border border-purple-200 border-opacity-50">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <FileTextOutlined className="text-white text-sm" />
            </div>
            <div>
              <h4 className="font-semibold text-purple-900 mb-1">样本管理</h4>
              <p className="text-sm text-purple-800">
                查看和管理具体的训练样本数据，包括问题、答案、类别和质量评估。支持样本生成功能。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 数据集选择和操作栏 */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-gray-700 font-medium">选择数据集：</span>
          <Select
            style={{ width: 300 }}
            placeholder="请选择数据集"
            value={selectedDataset?.id}
            onChange={(value) => {
              const dataset = datasets.find(d => d.id === value);
              setSelectedDataset(dataset || null);
            }}
            suffixIcon={<DatabaseOutlined />}
          >
            {datasets.map(dataset => (
              <Option key={dataset.id} value={dataset.id}>
                {dataset.filename} ({dataset.total_records} 条记录)
              </Option>
            ))}
          </Select>
          {selectedDataset && (
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadSamples(selectedDataset.id)}
              loading={loading}
            >
              刷新
            </Button>
          )}
        </div>
        {selectedDataset && (
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

      {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <div className="mb-4 p-4 bg-purple-50 rounded-lg flex items-center justify-between">
          <span className="text-purple-900">
            已选择 <strong>{selectedRowKeys.length}</strong> 个样本
          </span>
          <Popconfirm
            title={`确定要删除选中的 ${selectedRowKeys.length} 个样本吗？`}
            onConfirm={handleBatchDelete}
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
      <Card className="glass-card">
        {selectedDataset ? (
          <Table
            rowSelection={rowSelection}
            columns={columns}
            dataSource={samples}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 个样本`,
            }}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="请先选择一个数据集"
          />
        )}
      </Card>

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
                loadSamples(selectedDataset.id);
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

export default SampleManagementSimple;
