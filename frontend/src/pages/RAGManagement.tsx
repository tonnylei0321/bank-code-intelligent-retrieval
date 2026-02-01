import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Table, 
  Space, 
  message, 
  Statistic, 
  Row, 
  Col, 
  Input, 
  Form, 
  Spin, 
  Tag, 
  Alert, 
  Checkbox,
  Tabs,
  InputNumber,
  Select,
  Divider,
  Tooltip
} from 'antd';
import { 
  DatabaseOutlined, 
  SyncOutlined, 
  SearchOutlined, 
  ReloadOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  SaveOutlined,
  UndoOutlined
} from '@ant-design/icons';
import { useAppSelector } from '../hooks/redux';

const { TabPane } = Tabs;
const { Option } = Select;

interface RAGConfig {
  // 检索阶段参数
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  similarity_threshold: number;
  vector_model: string;
  
  // 增强阶段参数
  temperature: number;
  max_tokens: number;
  context_format: string;
  instruction: string;
  
  // 混合检索参数
  vector_weight: number;
  keyword_weight: number;
  enable_hybrid: boolean;
  
  // 性能优化参数
  batch_size: number;
  cache_enabled: boolean;
  cache_ttl: number;
}

interface RAGStats {
  vector_db_count: number;
  source_db_count: number;
  is_synced: boolean;
  collection_name: string;
  embedding_model_dimension: number;
  vector_db_path: string;
}

interface RAGSearchResult {
  bank_name: string;
  bank_code: string;
  clearing_code: string;
  similarity_score: number;
  keywords: string[];
  bank_id: number;
}

interface RAGSearchResponse {
  question: string;
  results: RAGSearchResult[];
  total_found: number;
  search_time_ms: number;
}

const RAGManagement: React.FC = () => {
  const [stats, setStats] = useState<RAGStats | null>(null);
  const [config, setConfig] = useState<RAGConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<RAGSearchResponse | null>(null);
  const [form] = Form.useForm();
  const [fileForm] = Form.useForm();
  const [configForm] = Form.useForm();
  
  const token = useAppSelector(state => state.auth.token);

  // 获取RAG配置
  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/v1/rag/config', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
        configForm.setFieldsValue(data.config);
      } else {
        message.error('获取RAG配置失败');
      }
    } catch (error) {
      console.error('获取RAG配置失败:', error);
      message.error('获取RAG配置失败');
    }
  };

  // 更新RAG配置
  const updateConfig = async (values: Partial<RAGConfig>) => {
    setConfigLoading(true);
    try {
      const response = await fetch('/api/v1/rag/config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
        configForm.setFieldsValue(data.config);
        message.success(data.message);
      } else {
        const error = await response.json();
        message.error(error.detail || '更新RAG配置失败');
      }
    } catch (error) {
      console.error('更新RAG配置失败:', error);
      message.error('更新RAG配置失败');
    } finally {
      setConfigLoading(false);
    }
  };

  // 重置RAG配置
  const resetConfig = async () => {
    setConfigLoading(true);
    try {
      const response = await fetch('/api/v1/rag/config/reset', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setConfig(data.config);
        configForm.setFieldsValue(data.config);
        message.success(data.message);
      } else {
        const error = await response.json();
        message.error(error.detail || '重置RAG配置失败');
      }
    } catch (error) {
      console.error('重置RAG配置失败:', error);
      message.error('重置RAG配置失败');
    } finally {
      setConfigLoading(false);
    }
  };

  // 获取RAG统计信息
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/rag/stats', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        message.error('获取RAG统计信息失败');
      }
    } catch (error) {
      console.error('获取RAG统计信息失败:', error);
      message.error('获取RAG统计信息失败');
    }
  };

  // 从文件加载到RAG
  const loadFromFile = async (values: { file_path: string; force_rebuild: boolean }) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/rag/load-from-file', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_path: values.file_path,
          force_rebuild: values.force_rebuild || false
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        message.success(data.message);
        setTimeout(fetchStats, 2000);
      } else {
        const error = await response.json();
        message.error(error.detail || '从文件加载失败');
      }
    } catch (error) {
      console.error('从文件加载失败:', error);
      message.error('从文件加载失败');
    } finally {
      setLoading(false);
    }
  };

  // 初始化RAG数据库
  const initializeRAG = async (forceRebuild = false) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/rag/initialize?force_rebuild=${forceRebuild}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        message.success(data.message);
        // 延迟刷新统计信息，给后台任务一些时间
        setTimeout(fetchStats, 2000);
      } else {
        const error = await response.json();
        message.error(error.detail || '初始化RAG数据库失败');
      }
    } catch (error) {
      console.error('初始化RAG数据库失败:', error);
      message.error('初始化RAG数据库失败');
    } finally {
      setLoading(false);
    }
  };

  // 更新RAG数据库
  const updateRAG = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/rag/update', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        message.success(data.message);
        setTimeout(fetchStats, 2000);
      } else {
        const error = await response.json();
        message.error(error.detail || '更新RAG数据库失败');
      }
    } catch (error) {
      console.error('更新RAG数据库失败:', error);
      message.error('更新RAG数据库失败');
    } finally {
      setLoading(false);
    }
  };

  // 测试RAG检索
  const testRAGSearch = async (values: { question: string; top_k: number }) => {
    setSearchLoading(true);
    try {
      const response = await fetch('/api/v1/rag/search', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: values.question,
          top_k: values.top_k || 5,
          similarity_threshold: 0.7
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
        message.success(`找到 ${data.total_found} 个相关结果，耗时 ${data.search_time_ms.toFixed(2)}ms`);
      } else {
        const error = await response.json();
        message.error(error.detail || 'RAG检索失败');
      }
    } catch (error) {
      console.error('RAG检索失败:', error);
      message.error('RAG检索失败');
    } finally {
      setSearchLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchConfig();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const searchColumns = [
    {
      title: '银行名称',
      dataIndex: 'bank_name',
      key: 'bank_name',
      width: '40%',
    },
    {
      title: '联行号',
      dataIndex: 'bank_code',
      key: 'bank_code',
      width: '15%',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: '清算代码',
      dataIndex: 'clearing_code',
      key: 'clearing_code',
      width: '15%',
      render: (text: string) => text || '-',
    },
    {
      title: '相似度分数',
      dataIndex: 'similarity_score',
      key: 'similarity_score',
      width: '15%',
      render: (score: number) => (
        <Tag color={score > 0.9 ? 'green' : score > 0.8 ? 'orange' : 'red'}>
          {(score * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      key: 'keywords',
      width: '15%',
      render: (keywords: string[] | undefined) => {
        if (!keywords || !Array.isArray(keywords)) {
          return <Tag>-</Tag>;
        }
        return (
          <div>
            {keywords.slice(0, 3).map((keyword, index) => (
              <Tag key={index}>{keyword}</Tag>
            ))}
            {keywords.length > 3 && <Tag>+{keywords.length - 3}</Tag>}
          </div>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <h1>RAG系统管理</h1>
      
      <Tabs defaultActiveKey="status" type="card">
        <TabPane tab="系统状态" key="status">
          {/* 统计信息 */}
          <Card title="系统状态" style={{ marginBottom: '24px' }}>
            {stats ? (
              <>
                <Row gutter={16}>
                  <Col span={6}>
                    <Statistic
                      title="向量数据库记录数"
                      value={stats.vector_db_count}
                      prefix={<DatabaseOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="源数据库记录数"
                      value={stats.source_db_count}
                      prefix={<DatabaseOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <Statistic
                      title="嵌入模型维度"
                      value={stats.embedding_model_dimension}
                      prefix={<ThunderboltOutlined />}
                    />
                  </Col>
                  <Col span={6}>
                    <div>
                      <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>同步状态</div>
                      <Tag color={stats.is_synced ? 'green' : 'orange'} style={{ fontSize: '16px', padding: '4px 12px' }}>
                        {stats.is_synced ? '已同步' : '需要同步'}
                      </Tag>
                    </div>
                  </Col>
                </Row>
                
                <div style={{ marginTop: '16px' }}>
                  <p><strong>集合名称:</strong> {stats.collection_name}</p>
                  <p><strong>存储路径:</strong> <code>{stats.vector_db_path}</code></p>
                </div>
                
                {!stats.is_synced && (
                  <Alert
                    message="数据不同步"
                    description="向量数据库与源数据库的记录数不一致，建议执行更新操作。"
                    type="warning"
                    showIcon
                    style={{ marginTop: '16px' }}
                  />
                )}
              </>
            ) : (
              <Spin size="large" />
            )}
          </Card>

          {/* 管理操作 */}
          <Card title="管理操作" style={{ marginBottom: '24px' }}>
            <Space size="middle">
              <Button
                type="primary"
                icon={<DatabaseOutlined />}
                loading={loading}
                onClick={() => initializeRAG(false)}
              >
                初始化向量数据库
              </Button>
              
              <Button
                icon={<SyncOutlined />}
                loading={loading}
                onClick={updateRAG}
              >
                更新数据库
              </Button>
              
              <Button
                icon={<ReloadOutlined />}
                loading={loading}
                onClick={() => initializeRAG(true)}
                danger
              >
                重建数据库
              </Button>
              
              <Button
                icon={<InfoCircleOutlined />}
                onClick={fetchStats}
              >
                刷新状态
              </Button>
            </Space>
            
            <div style={{ marginTop: '16px' }}>
              <Alert
                message="操作说明"
                description={
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    <li><strong>初始化:</strong> 首次创建向量数据库，如果已存在则跳过</li>
                    <li><strong>更新:</strong> 增量同步新增或删除的银行记录</li>
                    <li><strong>重建:</strong> 删除现有数据库并完全重新创建（谨慎使用）</li>
                  </ul>
                }
                type="info"
                showIcon
              />
            </div>
          </Card>

          {/* 从文件导入 */}
          <Card title="从文件导入" style={{ marginBottom: '24px' }}>
            <Form
              form={fileForm}
              layout="inline"
              onFinish={loadFromFile}
              style={{ marginBottom: '16px' }}
              initialValues={{
                file_path: 'data/T_BANK_LINE_NO_ICBC_ALL.unl',
                force_rebuild: true
              }}
            >
              <Form.Item
                name="file_path"
                rules={[{ required: true, message: '请输入文件路径' }]}
                style={{ width: '400px' }}
              >
                <Input placeholder="输入银行数据文件路径" />
              </Form.Item>
              
              <Form.Item name="force_rebuild" valuePropName="checked">
                <Checkbox>强制重建</Checkbox>
              </Form.Item>
              
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<DatabaseOutlined />}
                  loading={loading}
                >
                  从文件导入
                </Button>
              </Form.Item>
            </Form>

            <Alert
              message="文件导入说明"
              description={
                <div>
                  <p>支持从银行数据文件直接导入到RAG向量数据库：</p>
                  <ul style={{ margin: 0, paddingLeft: '20px' }}>
                    <li>文件格式：竖线分隔（|），第一列为联行号，第二列为银行名称</li>
                    <li>默认文件：data/T_BANK_LINE_NO_ICBC_ALL.unl</li>
                    <li>强制重建：清空现有数据并重新导入</li>
                    <li>导入过程在后台执行，请耐心等待</li>
                  </ul>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </TabPane>

        <TabPane tab="参数配置" key="config">
          <Card 
            title={
              <Space>
                <SettingOutlined />
                RAG参数配置
              </Space>
            } 
            style={{ marginBottom: '24px' }}
            extra={
              <Space>
                <Button
                  icon={<UndoOutlined />}
                  onClick={resetConfig}
                  loading={configLoading}
                >
                  重置默认值
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={() => configForm.submit()}
                  loading={configLoading}
                >
                  保存配置
                </Button>
              </Space>
            }
          >
            {config ? (
              <Form
                form={configForm}
                layout="vertical"
                onFinish={updateConfig}
                initialValues={config}
              >
                <Alert
                  message="配置说明"
                  description="RAG参数配置影响检索准确性和性能，请根据实际需求调整。修改后需要保存才能生效。"
                  type="info"
                  showIcon
                  style={{ marginBottom: '24px' }}
                />

                <Divider orientation="left">检索阶段参数</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item
                      name="chunk_size"
                      label={
                        <Space>
                          文档分块大小
                          <Tooltip title="将长文档分割成小块的大小，影响检索粒度">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={100}
                        max={2048}
                        style={{ width: '100%' }}
                        addonAfter="字符"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="chunk_overlap"
                      label={
                        <Space>
                          分块重叠大小
                          <Tooltip title="相邻文档块之间的重叠字符数，保持上下文连续性">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0}
                        max={200}
                        style={{ width: '100%' }}
                        addonAfter="字符"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="top_k"
                      label={
                        <Space>
                          检索结果数量
                          <Tooltip title="每次检索返回的最大结果数量">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={1}
                        max={50}
                        style={{ width: '100%' }}
                        addonAfter="个"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="similarity_threshold"
                      label={
                        <Space>
                          相似度阈值
                          <Tooltip title="过滤低相似度结果的阈值，越高越严格">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0.0}
                        max={1.0}
                        step={0.1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="vector_model"
                      label={
                        <Space>
                          向量模型
                          <Tooltip title="用于生成文档向量的预训练模型">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <Select style={{ width: '100%' }}>
                        <Option value="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2">
                          paraphrase-multilingual-MiniLM-L12-v2
                        </Option>
                        <Option value="sentence-transformers/all-MiniLM-L6-v2">
                          all-MiniLM-L6-v2
                        </Option>
                        <Option value="sentence-transformers/all-mpnet-base-v2">
                          all-mpnet-base-v2
                        </Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Divider orientation="left">增强阶段参数</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item
                      name="temperature"
                      label={
                        <Space>
                          生成温度
                          <Tooltip title="控制生成文本的随机性，越低越确定">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0.0}
                        max={2.0}
                        step={0.1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="max_tokens"
                      label={
                        <Space>
                          最大生成长度
                          <Tooltip title="生成答案的最大token数量">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={50}
                        max={2048}
                        style={{ width: '100%' }}
                        addonAfter="tokens"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="context_format"
                      label={
                        <Space>
                          上下文格式
                          <Tooltip title="传递给模型的上下文信息格式">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <Select style={{ width: '100%' }}>
                        <Option value="structured">结构化</Option>
                        <Option value="natural">自然语言</Option>
                        <Option value="json">JSON格式</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  name="instruction"
                  label={
                    <Space>
                      系统指令
                      <Tooltip title="指导模型如何处理和回答问题的系统提示">
                        <InfoCircleOutlined />
                      </Tooltip>
                    </Space>
                  }
                >
                  <Input.TextArea
                    rows={3}
                    placeholder="输入系统指令，指导模型如何回答问题"
                  />
                </Form.Item>

                <Divider orientation="left">混合检索参数</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item
                      name="vector_weight"
                      label={
                        <Space>
                          向量检索权重
                          <Tooltip title="向量检索在混合检索中的权重">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0.0}
                        max={1.0}
                        step={0.1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="keyword_weight"
                      label={
                        <Space>
                          关键词检索权重
                          <Tooltip title="关键词检索在混合检索中的权重">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0.0}
                        max={1.0}
                        step={0.1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="enable_hybrid"
                      label={
                        <Space>
                          启用混合检索
                          <Tooltip title="是否启用向量检索和关键词检索的混合模式">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                      valuePropName="checked"
                    >
                      <Checkbox>启用混合检索</Checkbox>
                    </Form.Item>
                  </Col>
                </Row>

                <Divider orientation="left">性能优化参数</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item
                      name="batch_size"
                      label={
                        <Space>
                          批处理大小
                          <Tooltip title="批量处理向量化的记录数量">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={10}
                        max={1000}
                        style={{ width: '100%' }}
                        addonAfter="条"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="cache_enabled"
                      label={
                        <Space>
                          启用缓存
                          <Tooltip title="是否启用查询结果缓存">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                      valuePropName="checked"
                    >
                      <Checkbox>启用缓存</Checkbox>
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      name="cache_ttl"
                      label={
                        <Space>
                          缓存过期时间
                          <Tooltip title="缓存结果的有效时间">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={60}
                        max={86400}
                        style={{ width: '100%' }}
                        addonAfter="秒"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Alert
                  message="银行代码检索优化建议"
                  description={
                    <div>
                      <p><strong>推荐配置（金融场景）：</strong></p>
                      <ul style={{ margin: 0, paddingLeft: '20px' }}>
                        <li>相似度阈值：0.3-0.5（平衡准确性和召回率）</li>
                        <li>检索结果数量：5-10个（提供足够选择）</li>
                        <li>向量权重：0.6，关键词权重：0.4（混合检索最佳比例）</li>
                        <li>生成温度：0.1（确保答案准确性）</li>
                        <li>启用缓存：提升重复查询性能</li>
                      </ul>
                    </div>
                  }
                  type="success"
                  showIcon
                  style={{ marginTop: '16px' }}
                />
              </Form>
            ) : (
              <Spin size="large" />
            )}
          </Card>
        </TabPane>

        <TabPane tab="检索测试" key="test">
          {/* RAG检索测试 */}
          <Card title="检索测试" style={{ marginBottom: '24px' }}>
            <Form
              form={form}
              layout="inline"
              onFinish={testRAGSearch}
              style={{ marginBottom: '16px' }}
            >
              <Form.Item
                name="question"
                rules={[{ required: true, message: '请输入测试问题' }]}
                style={{ width: '300px' }}
              >
                <Input placeholder="输入测试问题，如：工商银行北京分行" />
              </Form.Item>
              
              <Form.Item name="top_k" initialValue={5}>
                <Input type="number" placeholder="返回结果数" style={{ width: '120px' }} />
              </Form.Item>
              
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SearchOutlined />}
                  loading={searchLoading}
                >
                  测试检索
                </Button>
              </Form.Item>
            </Form>

            {searchResults && (
              <div>
                <div style={{ marginBottom: '16px' }}>
                  <Tag color="blue">问题: {searchResults.question}</Tag>
                  <Tag color="green">找到 {searchResults.total_found} 个结果</Tag>
                  <Tag color="orange">耗时 {searchResults.search_time_ms.toFixed(2)}ms</Tag>
                </div>
                
                <Table
                  columns={searchColumns}
                  dataSource={searchResults.results}
                  rowKey="bank_id"
                  pagination={false}
                  size="small"
                />
              </div>
            )}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default RAGManagement;