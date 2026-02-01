/**
 * 样本生成管理页面 - 完整的样本生成管理系统
 * 
 * 功能：
 * - QA生成：使用原有的QAGenerator API
 * - 提示词管理：管理LLM提示词模板
 * - 生成策略配置：LLM生成和规则生成
 * - 样本查看和管理：查看生成的样本
 * - 统计分析：生成统计和质量分析
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Space,
  Tag,
  Tooltip,
  Typography,
  Divider,
  Row,
  Col,
  Alert,
  Progress,
  Statistic,
  Tabs,
  InputNumber,
  Checkbox,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  SettingOutlined,
  BulbOutlined,
  CodeOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
  FileTextOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

interface Dataset {
  id: number;
  filename: string;
  total_records: number;
  status: string;
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

interface QAPair {
  id: number;
  dataset_id: number;
  question: string;
  answer: string;
  question_type: string;
  split_type: string;
  source_record_id?: number;
  generated_at: string;
}

interface GenerationStats {
  dataset_id: number;
  total_pairs: number;
  train_pairs: number;
  val_pairs: number;
  test_pairs: number;
  exact_pairs: number;
  fuzzy_pairs: number;
  reverse_pairs: number;
  natural_pairs: number;
}

const SampleGenerationManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState('generation');
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [prompts, setPrompts] = useState<LLMPrompt[]>([]);
  const [samples, setSamples] = useState<QAPair[]>([]);
  const [stats, setStats] = useState<GenerationStats | null>(null);
  const [loading, setLoading] = useState(false);
  
  // 模态框状态
  const [generationModalVisible, setGenerationModalVisible] = useState(false);
  const [promptModalVisible, setPromptModalVisible] = useState(false);
  const [previewModalVisible, setPreviewModalVisible] = useState(false);
  
  // 表单和选中项
  const [generationForm] = Form.useForm();
  const [promptForm] = Form.useForm();
  const [editingPrompt, setEditingPrompt] = useState<LLMPrompt | null>(null);
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<LLMPrompt | null>(null);

  const token = localStorage.getItem('access_token');

  useEffect(() => {
    fetchDatasets();
    fetchPrompts();
  }, []);

  useEffect(() => {
    if (selectedDataset) {
      fetchSamples(selectedDataset);
      fetchStats(selectedDataset);
    }
  }, [selectedDataset]);

  // 数据获取函数
  const fetchDatasets = async () => {
    try {
      const response = await fetch('/api/v1/datasets', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDatasets(data || []);
      }
    } catch (error) {
      console.error('获取数据集失败:', error);
    }
  };

  const fetchPrompts = async () => {
    try {
      const response = await fetch('/api/v1/llm-prompts', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setPrompts(data.data || []);
      }
    } catch (error) {
      console.error('获取提示词失败:', error);
    }
  };

  const fetchSamples = async (datasetId: number) => {
    try {
      const response = await fetch(`/api/v1/qa-pairs/${datasetId}?limit=100`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSamples(data || []);
      }
    } catch (error) {
      console.error('获取样本失败:', error);
    }
  };

  const fetchStats = async (datasetId: number) => {
    try {
      const response = await fetch(`/api/v1/qa-pairs/${datasetId}/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('获取统计失败:', error);
    }
  };

  // QA生成处理
  const handleGeneration = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/qa-pairs/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          dataset_id: values.dataset_id,
          question_types: values.question_types,
          train_ratio: values.train_ratio || 0.8,
          val_ratio: values.val_ratio || 0.1,
          test_ratio: values.test_ratio || 0.1,
        }),
      });

      if (response.ok) {
        const result = await response.json();
        message.success(`生成成功！共生成 ${result.total_generated} 个问答对`);
        setGenerationModalVisible(false);
        generationForm.resetFields();
        
        // 刷新数据
        if (values.dataset_id) {
          setSelectedDataset(values.dataset_id);
          fetchSamples(values.dataset_id);
          fetchStats(values.dataset_id);
        }
      } else {
        const error = await response.json();
        message.error(`生成失败: ${error.detail}`);
      }
    } catch (error) {
      message.error('生成失败');
    } finally {
      setLoading(false);
    }
  };

  // 提示词管理
  const handlePromptSubmit = async (values: any) => {
    try {
      const url = editingPrompt 
        ? `/api/v1/llm-prompts/${editingPrompt.llm_name}`
        : '/api/v1/llm-prompts';
      
      const method = editingPrompt ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success(editingPrompt ? '更新成功' : '创建成功');
        setPromptModalVisible(false);
        fetchPrompts();
      } else {
        const error = await response.json();
        message.error(error.detail || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDeletePrompt = async (llmName: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个提示词配置吗？',
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/llm-prompts/${llmName}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
          });
          if (response.ok) {
            message.success('删除成功');
            fetchPrompts();
          }
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleInitDefaults = async () => {
    try {
      const response = await fetch('/api/v1/llm-prompts/init-defaults', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const result = await response.json();
        message.success(result.message);
        fetchPrompts();
      }
    } catch (error) {
      message.error('初始化失败');
    }
  };

  // 表格列定义
  const promptColumns = [
    {
      title: 'LLM名称',
      dataIndex: 'llm_name',
      key: 'llm_name',
      width: 120,
      render: (text: string) => <Tag color=\"blue\">{text}</Tag>,
    },
    {
      title: '显示名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record: LLMPrompt) => (
        <Space>
          <Button
            type=\"link\"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedPrompt(record);
              setPreviewModalVisible(true);
            }}
          />
          <Button
            type=\"link\"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingPrompt(record);
              promptForm.setFieldsValue(record);
              setPromptModalVisible(true);
            }}
          />
          <Button
            type=\"link\"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeletePrompt(record.llm_name)}
          />
        </Space>
      ),
    },
  ];

  const sampleColumns = [
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '答案',
      dataIndex: 'answer',
      key: 'answer',
      ellipsis: true,
      width: '30%',
    },
    {
      title: '类型',
      dataIndex: 'question_type',
      key: 'question_type',
      width: 100,
      render: (type: string) => {
        const colors = {
          exact: 'blue',
          fuzzy: 'green',
          reverse: 'orange',
          natural: 'purple',
        };
        return <Tag color={colors[type as keyof typeof colors]}>{type}</Tag>;
      },
    },
    {
      title: '数据集',
      dataIndex: 'split_type',
      key: 'split_type',
      width: 80,
      render: (split: string) => {
        const colors = {
          train: 'green',
          val: 'orange',
          test: 'red',
        };
        return <Tag color={colors[split as keyof typeof colors]}>{split}</Tag>;
      },
    },
  ];

  return (
    <div className=\"minimalist-container\">
      <div className=\"content-area\">
        {/* 页面标题 */}
        <div className=\"section-spacing\">
          <div className=\"flex items-center justify-between\">
            <div>
              <h1 className=\"title-primary\">样本生成管理</h1>
              <p className=\"subtitle\">完整的样本生成管理系统，支持LLM生成、规则生成和提示词管理</p>
            </div>
          </div>
        </div>

        {/* 主要内容 */}
        <Card className=\"glass-card section-spacing\">
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            {/* QA生成标签页 */}
            <TabPane
              tab={
                <div className=\"flex items-center space-x-2\">
                  <PlayCircleOutlined />
                  <span>QA生成</span>
                </div>
              }
              key=\"generation\"
            >
              <div className=\"space-y-6\">
                {/* 生成配置 */}
                <div className=\"p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50\">
                  <div className=\"flex items-center justify-between mb-4\">
                    <h4 className=\"font-semibold text-blue-900\">问答对生成</h4>
                    <Button
                      type=\"primary\"
                      icon={<PlayCircleOutlined />}
                      onClick={() => setGenerationModalVisible(true)}
                      className=\"btn-primary-glass\"
                    >
                      开始生成
                    </Button>
                  </div>
                  <p className=\"text-sm text-blue-800\">
                    使用原有的QAGenerator系统，支持4种问题类型：精确匹配、模糊匹配、反向查询、自然语言
                  </p>
                </div>

                {/* 数据集选择 */}
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title=\"选择数据集\" className=\"glass-card\">
                      <Select
                        placeholder=\"选择要生成样本的数据集\"
                        style={{ width: '100%' }}
                        value={selectedDataset}
                        onChange={setSelectedDataset}
                      >
                        {datasets.map(dataset => (
                          <Option key={dataset.id} value={dataset.id}>
                            {dataset.filename} ({dataset.total_records} 条记录)
                          </Option>
                        ))}
                      </Select>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title=\"生成统计\" className=\"glass-card\">
                      {stats ? (
                        <div className=\"grid grid-cols-2 gap-4\">
                          <Statistic title=\"总样本\" value={stats.total_pairs} />
                          <Statistic title=\"训练集\" value={stats.train_pairs} />
                          <Statistic title=\"验证集\" value={stats.val_pairs} />
                          <Statistic title=\"测试集\" value={stats.test_pairs} />
                        </div>
                      ) : (
                        <Text type=\"secondary\">请选择数据集查看统计</Text>
                      )}
                    </Card>
                  </Col>
                </Row>

                {/* 样本列表 */}
                {selectedDataset && (
                  <Card title=\"生成的样本\" className=\"glass-card\">
                    <Table
                      columns={sampleColumns}
                      dataSource={samples}
                      rowKey=\"id\"
                      pagination={{ pageSize: 10 }}
                    />
                  </Card>
                )}
              </div>
            </TabPane>

            {/* 提示词管理标签页 */}
            <TabPane
              tab={
                <div className=\"flex items-center space-x-2\">
                  <CodeOutlined />
                  <span>提示词管理</span>
                </div>
              }
              key=\"prompts\"
            >
              <div className=\"space-y-6\">
                <div className=\"flex items-center justify-between\">
                  <div>
                    <h4 className=\"font-semibold text-gray-900\">LLM提示词配置</h4>
                    <p className=\"text-sm text-gray-600\">管理不同LLM的提示词模板</p>
                  </div>
                  <Space>
                    <Button
                      icon={<BulbOutlined />}
                      onClick={handleInitDefaults}
                    >
                      初始化默认模板
                    </Button>
                    <Button
                      type=\"primary\"
                      icon={<PlusOutlined />}
                      onClick={() => {
                        setEditingPrompt(null);
                        promptForm.resetFields();
                        setPromptModalVisible(true);
                      }}
                    >
                      新建提示词
                    </Button>
                  </Space>
                </div>

                <Table
                  columns={promptColumns}
                  dataSource={prompts}
                  rowKey=\"id\"
                  pagination={{ pageSize: 10 }}
                />
              </div>
            </TabPane>

            {/* 统计分析标签页 */}
            <TabPane
              tab={
                <div className=\"flex items-center space-x-2\">
                  <BarChartOutlined />
                  <span>统计分析</span>
                </div>
              }
              key=\"analytics\"
            >
              <div className=\"space-y-6\">
                {stats && (
                  <>
                    <Row gutter={16}>
                      <Col span={6}>
                        <Card className=\"glass-card\">
                          <Statistic
                            title=\"总样本数\"
                            value={stats.total_pairs}
                            prefix={<FileTextOutlined />}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card className=\"glass-card\">
                          <Statistic
                            title=\"精确匹配\"
                            value={stats.exact_pairs}
                            valueStyle={{ color: '#1890ff' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card className=\"glass-card\">
                          <Statistic
                            title=\"模糊匹配\"
                            value={stats.fuzzy_pairs}
                            valueStyle={{ color: '#52c41a' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card className=\"glass-card\">
                          <Statistic
                            title=\"反向查询\"
                            value={stats.reverse_pairs}
                            valueStyle={{ color: '#fa8c16' }}
                          />
                        </Card>
                      </Col>
                    </Row>

                    <Card title=\"数据集分布\" className=\"glass-card\">
                      <Row gutter={16}>
                        <Col span={8}>
                          <div className=\"text-center\">
                            <div className=\"text-2xl font-bold text-green-600\">{stats.train_pairs}</div>
                            <div className=\"text-sm text-gray-600\">训练集</div>
                            <Progress
                              percent={Math.round((stats.train_pairs / stats.total_pairs) * 100)}
                              strokeColor=\"#52c41a\"
                              showInfo={false}
                            />
                          </div>
                        </Col>
                        <Col span={8}>
                          <div className=\"text-center\">
                            <div className=\"text-2xl font-bold text-orange-600\">{stats.val_pairs}</div>
                            <div className=\"text-sm text-gray-600\">验证集</div>
                            <Progress
                              percent={Math.round((stats.val_pairs / stats.total_pairs) * 100)}
                              strokeColor=\"#fa8c16\"
                              showInfo={false}
                            />
                          </div>
                        </Col>
                        <Col span={8}>
                          <div className=\"text-center\">
                            <div className=\"text-2xl font-bold text-red-600\">{stats.test_pairs}</div>
                            <div className=\"text-sm text-gray-600\">测试集</div>
                            <Progress
                              percent={Math.round((stats.test_pairs / stats.total_pairs) * 100)}
                              strokeColor=\"#f5222d\"
                              showInfo={false}
                            />
                          </div>
                        </Col>
                      </Row>
                    </Card>
                  </>
                )}
              </div>
            </TabPane>
          </Tabs>
        </Card>

        {/* QA生成弹窗 */}
        <Modal
          title=\"生成问答对\"
          open={generationModalVisible}
          onCancel={() => setGenerationModalVisible(false)}
          footer={null}
          width={600}
        >
          <Form
            form={generationForm}
            layout=\"vertical\"
            onFinish={handleGeneration}
            initialValues={{
              question_types: ['exact', 'fuzzy', 'reverse', 'natural'],
              train_ratio: 0.8,
              val_ratio: 0.1,
              test_ratio: 0.1,
            }}
          >
            <Form.Item
              name=\"dataset_id\"
              label=\"选择数据集\"
              rules={[{ required: true, message: '请选择数据集' }]}
            >
              <Select placeholder=\"选择要生成样本的数据集\">
                {datasets.map(dataset => (
                  <Option key={dataset.id} value={dataset.id}>
                    {dataset.filename} ({dataset.total_records} 条记录)
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name=\"question_types\"
              label=\"问题类型\"
              rules={[{ required: true, message: '请选择问题类型' }]}
            >
              <Checkbox.Group>
                <Row>
                  <Col span={12}><Checkbox value=\"exact\">精确匹配</Checkbox></Col>
                  <Col span={12}><Checkbox value=\"fuzzy\">模糊匹配</Checkbox></Col>
                  <Col span={12}><Checkbox value=\"reverse\">反向查询</Checkbox></Col>
                  <Col span={12}><Checkbox value=\"natural\">自然语言</Checkbox></Col>
                </Row>
              </Checkbox.Group>
            </Form.Item>

            <Divider>数据集划分比例</Divider>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name=\"train_ratio\" label=\"训练集比例\">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name=\"val_ratio\" label=\"验证集比例\">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name=\"test_ratio\" label=\"测试集比例\">
                  <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item>
              <Space>
                <Button type=\"primary\" htmlType=\"submit\" loading={loading}>
                  开始生成
                </Button>
                <Button onClick={() => setGenerationModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 提示词编辑弹窗 */}
        <Modal
          title={editingPrompt ? '编辑提示词' : '新建提示词'}
          open={promptModalVisible}
          onCancel={() => setPromptModalVisible(false)}
          footer={null}
          width={800}
        >
          <Form
            form={promptForm}
            layout=\"vertical\"
            onFinish={handlePromptSubmit}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name=\"llm_name\"
                  label=\"LLM名称\"
                  rules={[{ required: true, message: '请输入LLM名称' }]}
                >
                  <Input disabled={!!editingPrompt} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name=\"display_name\"
                  label=\"显示名称\"
                  rules={[{ required: true, message: '请输入显示名称' }]}
                >
                  <Input />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name=\"description\" label=\"描述\">
              <Input />
            </Form.Item>

            <Form.Item
              name=\"prompt_template\"
              label=\"提示词模板\"
              rules={[{ required: true, message: '请输入提示词模板' }]}
            >
              <TextArea rows={8} />
            </Form.Item>

            <Form.Item name=\"is_active\" label=\"启用\" valuePropName=\"checked\">
              <Switch />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button type=\"primary\" htmlType=\"submit\">
                  {editingPrompt ? '更新' : '创建'}
                </Button>
                <Button onClick={() => setPromptModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 提示词预览弹窗 */}
        <Modal
          title=\"提示词预览\"
          open={previewModalVisible}
          onCancel={() => setPreviewModalVisible(false)}
          footer={[<Button key=\"close\" onClick={() => setPreviewModalVisible(false)}>关闭</Button>]}
          width={800}
        >
          {selectedPrompt && (
            <div className=\"space-y-4\">
              <div>
                <Text strong>LLM名称：</Text>
                <Tag color=\"blue\">{selectedPrompt.llm_name}</Tag>
              </div>
              <div>
                <Text strong>显示名称：</Text>
                <span>{selectedPrompt.display_name}</span>
              </div>
              <div>
                <Text strong>状态：</Text>
                <Tag color={selectedPrompt.is_active ? 'green' : 'red'}>
                  {selectedPrompt.is_active ? '启用' : '禁用'}
                </Tag>
              </div>
              <div>
                <Text strong>提示词模板：</Text>
                <pre className=\"mt-2 p-3 bg-gray-100 rounded text-sm whitespace-pre-wrap\">
                  {selectedPrompt.prompt_template}
                </pre>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
};

export default SampleGenerationManagement;