/**
 * 数据集管理页面
 * 
 * 功能：
 * - 数据集上传
 * - 数据集列表查看
 * - 数据集预览
 * - 数据集删除（支持批量）
 */

import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Upload, message, Modal, Space, Tag, Progress, Popconfirm } from 'antd';
import {
  UploadOutlined,
  EyeOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';

interface Dataset {
  id: number;
  filename: string;
  file_path: string;
  file_size: number;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  status: string;
  uploaded_at: string;
  uploaded_by: string;
}

interface PreviewData {
  columns: string[];
  data: any[];
  total: number;
}

const DatasetManagement: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const token = localStorage.getItem('access_token');

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    setLoading(true);
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
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async (dataset: Dataset) => {
    try {
      const response = await fetch(`/api/v1/datasets/${dataset.id}/preview?limit=10`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPreviewData(data);
        setSelectedDataset(dataset);
        setPreviewVisible(true);
      }
    } catch (error) {
      message.error('预览数据失败');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const response = await fetch(`/api/v1/datasets/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        message.success('删除成功');
        loadDatasets();
      } else {
        message.error('删除失败');
      }
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请选择要删除的数据集');
      return;
    }

    try {
      await Promise.all(
        selectedRowKeys.map(id =>
          fetch(`/api/v1/datasets/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
          })
        )
      );
      message.success(`成功删除 ${selectedRowKeys.length} 个数据集`);
      setSelectedRowKeys([]);
      loadDatasets();
    } catch (error) {
      message.error('批量删除失败');
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    action: '/api/v1/datasets/upload',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    onChange(info) {
      if (info.file.status === 'uploading') {
        setUploading(true);
      }
      if (info.file.status === 'done') {
        setUploading(false);
        message.success(`${info.file.name} 上传成功`);
        loadDatasets();
      } else if (info.file.status === 'error') {
        setUploading(false);
        message.error(`${info.file.name} 上传失败`);
      }
    },
  };

  const columns = [
    {
      title: '数据集名称',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string) => (
        <div className="flex items-center space-x-2">
          <FileTextOutlined className="text-blue-500" />
          <span className="font-medium">{text}</span>
        </div>
      ),
    },
    {
      title: '总记录数',
      dataIndex: 'total_records',
      key: 'total_records',
      render: (count: number) => (
        <Tag color="blue">{count.toLocaleString()}</Tag>
      ),
    },
    {
      title: '有效记录',
      dataIndex: 'valid_records',
      key: 'valid_records',
      render: (count: number) => (
        <Tag color="green" icon={<CheckCircleOutlined />}>
          {count.toLocaleString()}
        </Tag>
      ),
    },
    {
      title: '无效记录',
      dataIndex: 'invalid_records',
      key: 'invalid_records',
      render: (count: number) => (
        <Tag color="red" icon={<CloseCircleOutlined />}>
          {count.toLocaleString()}
        </Tag>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => {
        const mb = (size / 1024 / 1024).toFixed(2);
        return `${mb} MB`;
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          'completed': 'green',
          'processing': 'blue',
          'failed': 'red',
        };
        const labels: Record<string, string> = {
          'completed': '已完成',
          'processing': '处理中',
          'failed': '失败',
        };
        return <Tag color={colors[status]}>{labels[status] || status}</Tag>;
      },
    },
    {
      title: '上传时间',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Dataset) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          <Popconfirm
            title="确定要删除这个数据集吗？"
            onConfirm={() => handleDelete(record.id)}
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
            <h1 className="title-primary">数据集管理</h1>
            <p className="subtitle">管理训练数据集，支持上传、预览、下载和删除操作</p>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              icon={<ReloadOutlined />}
              onClick={loadDatasets}
              loading={loading}
            >
              刷新
            </Button>
            <Upload {...uploadProps} showUploadList={false}>
              <Button
                type="primary"
                icon={<UploadOutlined />}
                loading={uploading}
                className="btn-primary-glass"
              >
                上传数据集
              </Button>
            </Upload>
          </div>
        </div>
      </div>

      {/* 数据集说明卡片 */}
      <div className="mb-6">
        <div className="p-4 bg-gradient-to-r from-blue-50 to-cyan-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <DatabaseOutlined className="text-white text-sm" />
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 mb-1">数据集管理</h4>
              <p className="text-sm text-blue-800">
                管理训练样本数据集，支持上传、预览、下载和删除操作。数据集用于模型训练和评估。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <div className="mb-4 p-4 bg-blue-50 rounded-lg flex items-center justify-between">
          <span className="text-blue-900">
            已选择 <strong>{selectedRowKeys.length}</strong> 个数据集
          </span>
          <Popconfirm
            title={`确定要删除选中的 ${selectedRowKeys.length} 个数据集吗？`}
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

      {/* 数据集列表 */}
      <Card className="glass-card">
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={datasets}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个数据集`,
          }}
        />
      </Card>

      {/* 预览弹窗 */}
      <Modal
        title={`预览数据集: ${selectedDataset?.filename}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>
        ]}
        width={1000}
      >
        {previewData && (
          <div>
            <div className="mb-4">
              <Tag color="blue">总记录数: {previewData.total}</Tag>
              <Tag color="green">预览前 10 条</Tag>
            </div>
            <Table
              columns={previewData.columns.map(col => ({
                title: col,
                dataIndex: col,
                key: col,
              }))}
              dataSource={previewData.data}
              pagination={false}
              scroll={{ x: 'max-content' }}
              size="small"
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DatasetManagement;
