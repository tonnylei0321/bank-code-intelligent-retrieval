/**
 * Redis数据管理页面
 * 
 * 功能：
 * - Redis连接状态监控
 * - 银行数据加载管理
 * - 数据搜索和查询
 * - 缓存统计信息
 * - 数据同步操作
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Table,
  Input,
  Select,
  Tag,
  Statistic,
  Progress,
  Space,
  Alert,
  Modal,
  message,
  Descriptions,
  Tabs,
  Form,
  Spin,
  Divider,
  Upload,
  Typography,
  List,
} from 'antd';
import {
  DatabaseOutlined,
  ReloadOutlined,
  SearchOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SyncOutlined,
  BarChartOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  UploadOutlined,
  FileTextOutlined,
  EyeOutlined,
  InboxOutlined,
} from '@ant-design/icons';

const { Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { confirm } = Modal;
const { Dragger } = Upload;
const { Text, Title, Paragraph } = Typography;

interface RedisStats {
  total_banks: number;
  memory_usage: string;
  key_statistics: {
    total_keys: number;
    bank_keys: number;
    name_keys: number;
    code_keys: number;
    keyword_keys: number;
  };
  last_updated: string;
  version: string;
  redis_url: string;
  key_prefix: string;
}

interface BankData {
  id: number;
  bank_name: string;
  bank_code: string;
  clearing_code: string;
  dataset_id: number;
  created_at: string;
  updated_at: string;
}

interface FileUploadResult {
  filename: string;
  file_size: number;
  parsed_count: number;
  saved_count: number;
  redis_updated: boolean;
  processing_time: number;
  sample_data: BankData[];
}

interface FilePreviewData {
  filename: string;
  file_size: number;
  total_lines: number;
  parsed_count: number;
  preview_count: number;
  preview_data: Array<{
    bank_code: string;
    bank_name: string;
    clearing_code: string;
    line_number: number;
  }>;
  processing_time: number;
}

const RedisManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [redisStats, setRedisStats] = useState<RedisStats | null>(null);
  const [redisStatus, setRedisStatus] = useState<'healthy' | 'unhealthy' | 'unknown'>('unknown');
  const [searchResults, setSearchResults] = useState<BankData[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [syncingData, setSyncingData] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewData, setPreviewData] = useState<FilePreviewData | null>(null);
  const [uploadResult, setUploadResult] = useState<FileUploadResult | null>(null);
  const [searchForm] = Form.useForm();

  // 获取Redis健康状态
  const fetchRedisHealth = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/redis/health', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (data.success) {
        setRedisStatus(data.status);
        setRedisStats(data.stats);
      } else {
        setRedisStatus('unhealthy');
        message.error('Redis连接失败');
      }
    } catch (error) {
      console.error('获取Redis状态失败:', error);
      setRedisStatus('unhealthy');
      message.error('获取Redis状态失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载银行数据到Redis
  const handleLoadData = async (forceReload = false) => {
    setLoadingData(true);
    try {
      const response = await fetch(`/api/redis/load-data?force_reload=${forceReload}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (data.success) {
        message.success('银行数据加载成功');
        fetchRedisHealth(); // 刷新统计信息
      } else {
        message.error(data.message || '数据加载失败');
      }
    } catch (error) {
      console.error('加载数据失败:', error);
      message.error('加载数据失败');
    } finally {
      setLoadingData(false);
    }
  };

  // 搜索银行数据
  const handleSearch = async (values: any) => {
    if (!values.query?.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }

    setSearchLoading(true);
    try {
      const params = new URLSearchParams({
        query: values.query,
        search_type: values.search_type || 'auto',
        limit: '20',
      });

      const response = await fetch(`/api/redis/search?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (data.success) {
        setSearchResults(data.data.results || []);
        message.success(`找到 ${data.data.count} 条结果`);
      } else {
        message.error('搜索失败');
        setSearchResults([]);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      message.error('搜索失败');
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // 清空Redis数据
  const handleClearData = () => {
    confirm({
      title: '确认清空数据',
      icon: <ExclamationCircleOutlined />,
      content: '此操作将清空Redis中的所有银行数据，是否继续？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch('/api/redis/clear-data', {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
          });
          const data = await response.json();
          
          if (data.success) {
            message.success('数据清空成功');
            fetchRedisHealth();
            setSearchResults([]);
          } else {
            message.error('数据清空失败');
          }
        } catch (error) {
          console.error('清空数据失败:', error);
          message.error('清空数据失败');
        }
      },
    });
  };

  // 同步数据
  const handleSyncData = async () => {
    setSyncingData(true);
    try {
      const response = await fetch('/api/redis/sync-data', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (data.success) {
        message.success(data.message);
        fetchRedisHealth();
      } else {
        message.error('数据同步失败');
      }
    } catch (error) {
      console.error('同步数据失败:', error);
      message.error('同步数据失败');
    } finally {
      setSyncingData(false);
    }
  };

  // 文件上传处理
  const handleFileUpload = async (file: File) => {
    setUploadingFile(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('force_reload', 'false');

      const response = await fetch('/api/redis/upload-file', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setUploadResult(data.data);
        message.success(`文件上传成功！解析了 ${data.data.parsed_count} 条银行记录`);
        fetchRedisHealth(); // 刷新统计信息
      } else {
        message.error(data.message || '文件上传失败');
      }
    } catch (error) {
      console.error('文件上传失败:', error);
      message.error('文件上传失败');
    } finally {
      setUploadingFile(false);
    }
  };

  // 文件预览
  const handleFilePreview = async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/redis/parse-preview?lines=20', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        setPreviewData(data.data);
        setPreviewVisible(true);
      } else {
        message.error('文件预览失败');
      }
    } catch (error) {
      console.error('文件预览失败:', error);
      message.error('文件预览失败');
    }
  };

  // 上传组件配置
  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.unl,.txt,.csv',
    beforeUpload: (file: File) => {
      // 检查文件大小（50MB限制）
      const isLt50M = file.size / 1024 / 1024 < 50;
      if (!isLt50M) {
        message.error('文件大小不能超过50MB');
        return false;
      }

      // 检查文件类型
      const allowedTypes = ['unl', 'txt', 'csv'];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (!fileExtension || !allowedTypes.includes(fileExtension)) {
        message.error('只支持 .unl, .txt, .csv 格式的文件');
        return false;
      }

      // 直接处理上传
      handleFileUpload(file);
      return false; // 阻止默认上传行为
    },
    showUploadList: false,
  };

  useEffect(() => {
    fetchRedisHealth();
  }, []);

  // 搜索结果表格列
  const searchColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '银行名称',
      dataIndex: 'bank_name',
      key: 'bank_name',
      ellipsis: true,
    },
    {
      title: '联行号',
      dataIndex: 'bank_code',
      key: 'bank_code',
      width: 150,
      render: (code: string) => (
        <Tag color="blue" style={{ fontFamily: 'monospace' }}>
          {code}
        </Tag>
      ),
    },
    {
      title: '清算代码',
      dataIndex: 'clearing_code',
      key: 'clearing_code',
      width: 150,
      render: (code: string) => code || '-',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#52c41a';
      case 'unhealthy': return '#ff4d4f';
      default: return '#faad14';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'healthy': return '正常';
      case 'unhealthy': return '异常';
      default: return '未知';
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1>Redis数据管理</h1>
        <Space>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={fetchRedisHealth}
            loading={loading}
          >
            刷新状态
          </Button>
        </Space>
      </div>

      {/* Redis状态概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="连接状态"
              value={getStatusText(redisStatus)}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: getStatusColor(redisStatus) }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="银行数据总数"
              value={redisStats?.total_banks || 0}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="内存使用"
              value={redisStats?.memory_usage || 'N/A'}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="键总数"
              value={redisStats?.key_statistics?.total_keys || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="1">
        <TabPane tab="数据管理" key="1">
          <Card title="数据操作" style={{ marginBottom: 16 }}>
            <Space size="middle" wrap>
              <Button
                type="primary"
                icon={<DatabaseOutlined />}
                onClick={() => handleLoadData(false)}
                loading={loadingData}
              >
                加载数据
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => handleLoadData(true)}
                loading={loadingData}
              >
                强制重新加载
              </Button>
              <Button
                icon={<SyncOutlined />}
                onClick={handleSyncData}
                loading={syncingData}
              >
                同步数据
              </Button>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleClearData}
              >
                清空数据
              </Button>
            </Space>
          </Card>

          {/* 文件上传区域 */}
          <Card title="文件上传" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={16}>
                <Dragger {...uploadProps} style={{ padding: '20px' }}>
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                  <p className="ant-upload-hint">
                    支持 .unl, .txt, .csv 格式的银行数据文件
                    <br />
                    文件格式：联行编号|银行名称|清算行行号
                    <br />
                    文件大小限制：50MB
                    <br />
                    <Button 
                      type="link" 
                      size="small" 
                      onClick={() => {
                        const link = document.createElement('a');
                        link.href = '/api/static/test_banks_sample.unl';
                        link.download = 'test_banks_sample.unl';
                        link.click();
                      }}
                    >
                      下载示例文件
                    </Button>
                  </p>
                </Dragger>
                {uploadingFile && (
                  <div style={{ textAlign: 'center', marginTop: 16 }}>
                    <Spin size="large" />
                    <div style={{ marginTop: 8 }}>正在处理文件...</div>
                  </div>
                )}
              </Col>
              <Col span={8}>
                <Card size="small" title="上传说明">
                  <Paragraph style={{ fontSize: '12px' }}>
                    <Text strong>支持的文件格式：</Text>
                    <br />
                    • .unl 文件（管道符分隔）
                    <br />
                    • .txt 文件（制表符分隔）
                    <br />
                    • .csv 文件（逗号分隔）
                    <br />
                    <br />
                    <Text strong>数据格式要求：</Text>
                    <br />
                    • 第1列：联行编号（12位数字）
                    <br />
                    • 第2列：银行名称
                    <br />
                    • 第3列：清算行行号
                    <br />
                    <br />
                    <Text strong>示例：</Text>
                    <br />
                    <Text code style={{ fontSize: '10px' }}>
                      102290002916|中国工商银行股份有限公司上海市西虹桥支行|102290002916
                    </Text>
                  </Paragraph>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 上传结果显示 */}
          {uploadResult && (
            <Card title="上传结果" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Descriptions bordered size="small" column={1}>
                    <Descriptions.Item label="文件名">
                      {uploadResult.filename}
                    </Descriptions.Item>
                    <Descriptions.Item label="文件大小">
                      {(uploadResult.file_size / 1024 / 1024).toFixed(2)} MB
                    </Descriptions.Item>
                    <Descriptions.Item label="解析记录数">
                      <Tag color="blue">{uploadResult.parsed_count}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="保存记录数">
                      <Tag color="green">{uploadResult.saved_count}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Redis更新">
                      <Tag color={uploadResult.redis_updated ? 'success' : 'warning'}>
                        {uploadResult.redis_updated ? '成功' : '失败'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="处理时间">
                      {uploadResult.processing_time.toFixed(2)}秒
                    </Descriptions.Item>
                  </Descriptions>
                </Col>
                <Col span={12}>
                  <Card size="small" title="示例数据">
                    <List
                      size="small"
                      dataSource={uploadResult.sample_data}
                      renderItem={(item) => (
                        <List.Item>
                          <List.Item.Meta
                            title={<Text ellipsis style={{ maxWidth: 200 }}>{item.bank_name}</Text>}
                            description={
                              <Space>
                                <Tag color="blue">{item.bank_code}</Tag>
                                <Tag color="green">{item.clearing_code}</Tag>
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
              </Row>
            </Card>
          )}

          <Card title="数据搜索">
            <Form
              form={searchForm}
              layout="inline"
              onFinish={handleSearch}
              style={{ marginBottom: 16 }}
            >
              <Form.Item name="query" style={{ width: 300 }}>
                <Input
                  placeholder="输入银行名称、联行号或关键词"
                  prefix={<SearchOutlined />}
                />
              </Form.Item>
              <Form.Item name="search_type">
                <Select defaultValue="auto" style={{ width: 120 }}>
                  <Option value="auto">自动</Option>
                  <Option value="name">银行名称</Option>
                  <Option value="code">联行号</Option>
                  <Option value="keyword">关键词</Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={searchLoading}>
                  搜索
                </Button>
              </Form.Item>
            </Form>

            <Table
              columns={searchColumns}
              dataSource={searchResults}
              loading={searchLoading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
              locale={{ emptyText: '暂无搜索结果' }}
            />
          </Card>
        </TabPane>

        <TabPane tab="统计信息" key="2">
          <Card title="Redis详细信息">
            {redisStats ? (
              <Descriptions bordered column={2}>
                <Descriptions.Item label="Redis URL">
                  {redisStats.redis_url}
                </Descriptions.Item>
                <Descriptions.Item label="键前缀">
                  {redisStats.key_prefix}
                </Descriptions.Item>
                <Descriptions.Item label="银行数据键">
                  {redisStats.key_statistics.bank_keys}
                </Descriptions.Item>
                <Descriptions.Item label="名称索引键">
                  {redisStats.key_statistics.name_keys}
                </Descriptions.Item>
                <Descriptions.Item label="联行号索引键">
                  {redisStats.key_statistics.code_keys}
                </Descriptions.Item>
                <Descriptions.Item label="关键词索引键">
                  {redisStats.key_statistics.keyword_keys}
                </Descriptions.Item>
                <Descriptions.Item label="最后更新时间" span={2}>
                  {redisStats.last_updated !== 'Unknown' 
                    ? new Date(redisStats.last_updated).toLocaleString('zh-CN')
                    : '未知'
                  }
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin size="large" />
                <div style={{ marginTop: 16 }}>加载统计信息中...</div>
              </div>
            )}
          </Card>
        </TabPane>
      </Tabs>

      {/* 文件预览模态框 */}
      <Modal
        title="文件预览"
        visible={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {previewData && (
          <div>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="文件名">
                {previewData.filename}
              </Descriptions.Item>
              <Descriptions.Item label="文件大小">
                {(previewData.file_size / 1024 / 1024).toFixed(2)} MB
              </Descriptions.Item>
              <Descriptions.Item label="总行数">
                {previewData.total_lines}
              </Descriptions.Item>
              <Descriptions.Item label="有效记录数">
                {previewData.parsed_count}
              </Descriptions.Item>
              <Descriptions.Item label="预览记录数">
                {previewData.preview_count}
              </Descriptions.Item>
              <Descriptions.Item label="处理时间">
                {previewData.processing_time.toFixed(2)}秒
              </Descriptions.Item>
            </Descriptions>

            <Table
              size="small"
              columns={[
                {
                  title: '行号',
                  dataIndex: 'line_number',
                  key: 'line_number',
                  width: 60,
                },
                {
                  title: '联行编号',
                  dataIndex: 'bank_code',
                  key: 'bank_code',
                  width: 120,
                  render: (code: string) => <Tag color="blue">{code}</Tag>,
                },
                {
                  title: '银行名称',
                  dataIndex: 'bank_name',
                  key: 'bank_name',
                  ellipsis: true,
                },
                {
                  title: '清算行行号',
                  dataIndex: 'clearing_code',
                  key: 'clearing_code',
                  width: 120,
                  render: (code: string) => code || '-',
                },
              ]}
              dataSource={previewData.preview_data}
              pagination={false}
              scroll={{ y: 300 }}
            />
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RedisManagement;