/**
 * 提示词管理页面 - 极简主义设计，毛玻璃效果
 * 
 * 功能：
 * - LLM提示词配置管理
 * - 支持创建、编辑、删除、启用/禁用
 * - 提示词模板预览和测试
 * - 默认模板初始化
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
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
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

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

const PromptManagement: React.FC = () => {
  const [prompts, setPrompts] = useState<LLMPrompt[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<LLMPrompt | null>(null);
  const [selectedPrompt, setSelectedPrompt] = useState<LLMPrompt | null>(null);
  const [form] = Form.useForm();

  const token = localStorage.getItem('access_token');

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/llm-prompts', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setPrompts(data.data || []);
      } else {
        message.error('获取提示词列表失败');
      }
    } catch (error) {
      console.error('获取提示词失败:', error);
      message.error('获取提示词失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPrompt(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (prompt: LLMPrompt) => {
    setEditingPrompt(prompt);
    form.setFieldsValue({
      llm_name: prompt.llm_name,
      display_name: prompt.display_name,
      prompt_template: prompt.prompt_template,
      description: prompt.description,
      is_active: prompt.is_active,
    });
    setModalVisible(true);
  };

  const handlePreview = (prompt: LLMPrompt) => {
    setSelectedPrompt(prompt);
    setPreviewVisible(true);
  };

  const handleSubmit = async (values: any) => {
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
        setModalVisible(false);
        fetchPrompts();
      } else {
        const error = await response.json();
        message.error(error.detail || '操作失败');
      }
    } catch (error) {
      message.error('操作失败');
    }
  };

  const handleDelete = async (llmName: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个提示词配置吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/llm-prompts/${llmName}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (response.ok) {
            message.success('删除成功');
            fetchPrompts();
          } else {
            message.error('删除失败');
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
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        message.success(result.message);
        fetchPrompts();
      } else {
        const error = await response.json();
        message.error(error.detail || '初始化失败');
      }
    } catch (error) {
      message.error('初始化失败');
    }
  };

  const columns = [
    {
      title: 'LLM名称',
      dataIndex: 'llm_name',
      key: 'llm_name',
      width: 120,
      render: (text: string) => (
        <Tag color=\"blue\" className=\"font-mono\">{text}</Tag>
      ),
    },
    {
      title: '显示名称',
      dataIndex: 'display_name',
      key: 'display_name',
      width: 200,
      render: (text: string) => (
        <Text strong>{text}</Text>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Text type=\"secondary\">{text || '无描述'}</Text>
      ),
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
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: LLMPrompt) => (
        <Space>
          <Tooltip title=\"预览模板\">
            <Button
              type=\"link\"
              icon={<EyeOutlined />}
              onClick={() => handlePreview(record)}
            />
          </Tooltip>
          <Tooltip title=\"编辑\">
            <Button
              type=\"link\"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title=\"删除\">
            <Button
              type=\"link\"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.llm_name)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className=\"minimalist-container\">
      <div className=\"content-area\">
        {/* 页面标题 */}
        <div className=\"section-spacing\">
          <div className=\"flex items-center justify-between\">
            <div>
              <h1 className=\"title-primary\">提示词管理</h1>
              <p className=\"subtitle\">管理LLM提示词模板，配置不同模型的生成策略和参数</p>
            </div>
            <div className=\"flex items-center space-x-4\">
              <Button 
                type=\"primary\" 
                icon={<PlusOutlined />}
                onClick={handleCreate}
                className=\"btn-primary-glass\"
              >
                新建提示词
              </Button>
              <Button 
                icon={<BulbOutlined />}
                onClick={handleInitDefaults}
                className=\"btn-secondary-glass\"
              >
                初始化默认模板
              </Button>
            </div>
          </div>
        </div>

        {/* 功能说明 */}
        <div className=\"section-spacing\">
          <Alert
            message=\"提示词管理说明\"
            description={
              <div className=\"space-y-2\">
                <p>• <strong>LLM名称</strong>：用于系统内部识别的唯一标识符，如 qwen、deepseek、chatglm</p>
                <p>• <strong>显示名称</strong>：用户界面显示的友好名称，如 \"阿里通义千问\"</p>
                <p>• <strong>提示词模板</strong>：支持变量替换，如 {'{bank_name}'}, {'{bank_code}'}, {'{num_samples}'}</p>
                <p>• <strong>状态控制</strong>：只有启用状态的提示词才会在样本生成时使用</p>
              </div>
            }
            type=\"info\"
            showIcon
            className=\"glass-card\"
          />
        </div>

        {/* 提示词列表 */}
        <Card 
          title={
            <div className=\"flex items-center space-x-3\">
              <div className=\"w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center\">
                <SettingOutlined className=\"text-white text-sm\" />
              </div>
              <span className=\"font-semibold\">提示词配置列表</span>
            </div>
          }
          extra={
            <Button icon={<ReloadOutlined />} onClick={fetchPrompts}>
              刷新
            </Button>
          }
          className=\"glass-card section-spacing\"
        >
          <div className=\"table-glass\">
            <Table
              columns={columns}
              dataSource={prompts}
              loading={loading}
              rowKey=\"id\"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个提示词配置`,
              }}
            />
          </div>
        </Card>

        {/* 创建/编辑弹窗 */}
        <Modal
          title={
            <div className=\"flex items-center space-x-3\">
              <div className=\"w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center\">
                <CodeOutlined className=\"text-white text-sm\" />
              </div>
              <span className=\"font-semibold\">
                {editingPrompt ? '编辑提示词' : '新建提示词'}
              </span>
            </div>
          }
          open={modalVisible}
          onCancel={() => setModalVisible(false)}
          footer={null}
          width={800}
          className=\"modal-glass\"
        >
          <Form
            form={form}
            layout=\"vertical\"
            onFinish={handleSubmit}
            className=\"mt-6\"
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name=\"llm_name\"
                  label=\"LLM名称\"
                  rules={[
                    { required: true, message: '请输入LLM名称' },
                    { pattern: /^[a-z0-9_-]+$/, message: '只能包含小写字母、数字、下划线和连字符' }
                  ]}
                >
                  <Input 
                    placeholder=\"如：qwen, deepseek, chatglm\"
                    disabled={!!editingPrompt}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name=\"display_name\"
                  label=\"显示名称\"
                  rules={[{ required: true, message: '请输入显示名称' }]}
                >
                  <Input placeholder=\"如：阿里通义千问\" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name=\"description\"
              label=\"描述\"
            >
              <Input placeholder=\"描述这个LLM的特点和适用场景\" />
            </Form.Item>

            <Form.Item
              name=\"prompt_template\"
              label=\"提示词模板\"
              rules={[{ required: true, message: '请输入提示词模板' }]}
            >
              <TextArea
                rows={12}
                placeholder={`请输入提示词模板，支持以下变量：
- {bank_name}: 银行名称
- {bank_code}: 银行联行号
- {num_samples}: 生成样本数量

示例：
你是一个银行业务专家。请为以下银行生成{num_samples}种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成{num_samples}种用户可能的问法
2. 包括：完整名称、简称、口语化表达等
3. 返回JSON格式...`}
              />
            </Form.Item>

            <Form.Item
              name=\"is_active\"
              label=\"启用状态\"
              valuePropName=\"checked\"
              initialValue={true}
            >
              <Switch checkedChildren=\"启用\" unCheckedChildren=\"禁用\" />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button 
                  type=\"primary\" 
                  htmlType=\"submit\"
                  className=\"btn-primary-glass\"
                >
                  {editingPrompt ? '更新' : '创建'}
                </Button>
                <Button onClick={() => setModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 预览弹窗 */}
        <Modal
          title={
            <div className=\"flex items-center space-x-3\">
              <div className=\"w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center\">
                <EyeOutlined className=\"text-white text-sm\" />
              </div>
              <span className=\"font-semibold\">提示词模板预览</span>
            </div>
          }
          open={previewVisible}
          onCancel={() => setPreviewVisible(false)}
          footer={[
            <Button key=\"close\" onClick={() => setPreviewVisible(false)}>
              关闭
            </Button>
          ]}
          width={900}
          className=\"modal-glass\"
        >
          {selectedPrompt && (
            <div className=\"space-y-6\">
              {/* 基本信息 */}
              <div className=\"p-4 bg-gray-50 bg-opacity-50 rounded-2xl border border-gray-200 border-opacity-50\">
                <h4 className=\"font-semibold text-gray-900 mb-3\">基本信息</h4>
                <div className=\"grid grid-cols-2 gap-4\">
                  <div>
                    <label className=\"text-sm font-medium text-gray-600\">LLM名称</label>
                    <div className=\"text-sm text-gray-900 font-mono\">{selectedPrompt.llm_name}</div>
                  </div>
                  <div>
                    <label className=\"text-sm font-medium text-gray-600\">显示名称</label>
                    <div className=\"text-sm text-gray-900\">{selectedPrompt.display_name}</div>
                  </div>
                  <div>
                    <label className=\"text-sm font-medium text-gray-600\">状态</label>
                    <div>
                      <Tag color={selectedPrompt.is_active ? 'green' : 'red'}>
                        {selectedPrompt.is_active ? '启用' : '禁用'}
                      </Tag>
                    </div>
                  </div>
                  <div>
                    <label className=\"text-sm font-medium text-gray-600\">更新时间</label>
                    <div className=\"text-sm text-gray-900\">
                      {new Date(selectedPrompt.updated_at).toLocaleString('zh-CN')}
                    </div>
                  </div>
                </div>
                {selectedPrompt.description && (
                  <div className=\"mt-4\">
                    <label className=\"text-sm font-medium text-gray-600\">描述</label>
                    <div className=\"text-sm text-gray-900\">{selectedPrompt.description}</div>
                  </div>
                )}
              </div>

              {/* 提示词模板 */}
              <div className=\"p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50\">
                <h4 className=\"font-semibold text-blue-900 mb-3\">提示词模板</h4>
                <div className=\"p-3 bg-white bg-opacity-70 rounded-xl border border-blue-200 border-opacity-30\">
                  <pre className=\"text-sm text-gray-800 whitespace-pre-wrap font-mono leading-relaxed\">
                    {selectedPrompt.prompt_template}
                  </pre>
                </div>
              </div>

              {/* 变量说明 */}
              <div className=\"p-4 bg-yellow-50 bg-opacity-50 rounded-2xl border border-yellow-200 border-opacity-50\">
                <h4 className=\"font-semibold text-yellow-900 mb-3\">支持的变量</h4>
                <div className=\"space-y-2 text-sm\">
                  <div className=\"flex items-center space-x-2\">
                    <code className=\"px-2 py-1 bg-yellow-200 bg-opacity-50 rounded text-yellow-800\">{'{bank_name}'}</code>
                    <span className=\"text-yellow-800\">银行完整名称</span>
                  </div>
                  <div className=\"flex items-center space-x-2\">
                    <code className=\"px-2 py-1 bg-yellow-200 bg-opacity-50 rounded text-yellow-800\">{'{bank_code}'}</code>
                    <span className=\"text-yellow-800\">银行联行号</span>
                  </div>
                  <div className=\"flex items-center space-x-2\">
                    <code className=\"px-2 py-1 bg-yellow-200 bg-opacity-50 rounded text-yellow-800\">{'{num_samples}'}</code>
                    <span className=\"text-yellow-800\">要生成的样本数量</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </div>
  );
};

export default PromptManagement;