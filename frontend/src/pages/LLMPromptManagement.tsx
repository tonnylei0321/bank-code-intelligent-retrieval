import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Switch, message, Space, Tag, Popconfirm, Tabs } from 'antd';
import { PlusOutlined, EditOutlined, ReloadOutlined, SyncOutlined, EyeOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { TabPane } = Tabs;

interface PromptTemplate {
  id: number;
  provider: string;
  prompt_type: string;
  question_type: string;
  template: string;
  description: string;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const LLMPromptManagement: React.FC = () => {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplate | null>(null);
  const [viewingTemplate, setViewingTemplate] = useState<PromptTemplate | null>(null);
  const [form] = Form.useForm();
  const [activeProvider, setActiveProvider] = useState<string>('all');
  
  const token = localStorage.getItem('access_token');

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/llm-prompt-templates', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      } else {
        message.error('加载提示词模板失败');
      }
    } catch (error) {
      message.error('加载提示词模板失败');
    } finally {
      setLoading(false);
    }
  };

  const initDefaultTemplates = async () => {
    try {
      const response = await fetch('/api/v1/llm-prompt-templates/init-defaults', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const result = await response.json();
        message.success(result.message);
        loadTemplates();
      } else {
        message.error('初始化默认模板失败');
      }
    } catch (error) {
      message.error('初始化默认模板失败');
    }
  };

  const handleEdit = (template: PromptTemplate) => {
    setEditingTemplate(template);
    form.setFieldsValue({
      template: template.template,
      description: template.description,
      is_active: template.is_active
    });
    setModalVisible(true);
  };

  const handleView = (template: PromptTemplate) => {
    setViewingTemplate(template);
    setViewModalVisible(true);
  };

  const handleSave = async (values: any) => {
    try {
      if (editingTemplate) {
        // 更新
        const response = await fetch(`/api/v1/llm-prompt-templates/${editingTemplate.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(values)
        });
        
        if (response.ok) {
          message.success('更新成功');
          setModalVisible(false);
          form.resetFields();
          setEditingTemplate(null);
          loadTemplates();
        } else {
          message.error('更新失败');
        }
      }
    } catch (error) {
      message.error('保存失败');
    }
  };

  const handleReset = async (template: PromptTemplate) => {
    try {
      const response = await fetch(`/api/v1/llm-prompt-templates/${template.id}/reset`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        message.success('已重置为默认提示词');
        loadTemplates();
      } else {
        message.error('重置失败');
      }
    } catch (error) {
      message.error('重置失败');
    }
  };

  const getProviderName = (provider: string) => {
    const names: Record<string, string> = {
      'qwen': '通义千问',
      'deepseek': 'DeepSeek',
      'volces': '火山引擎'
    };
    return names[provider] || provider;
  };

  const getQuestionTypeName = (type: string) => {
    const names: Record<string, string> = {
      'exact': '精确查询',
      'fuzzy': '模糊查询',
      'reverse': '反向查询',
      'natural': '自然语言'
    };
    return names[type] || type;
  };

  const getProviderColor = (provider: string) => {
    const colors: Record<string, string> = {
      'qwen': 'blue',
      'deepseek': 'green',
      'volces': 'purple'
    };
    return colors[provider] || 'default';
  };

  const columns = [
    {
      title: 'LLM提供商',
      dataIndex: 'provider',
      key: 'provider',
      width: 120,
      render: (provider: string) => (
        <Tag color={getProviderColor(provider)}>
          {getProviderName(provider)}
        </Tag>
      )
    },
    {
      title: '问题类型',
      dataIndex: 'question_type',
      key: 'question_type',
      width: 120,
      render: (type: string) => getQuestionTypeName(type)
    },
    {
      title: '提示词预览',
      dataIndex: 'template',
      key: 'template',
      ellipsis: true,
      render: (text: string) => (
        <div className="text-gray-600 truncate" style={{ maxWidth: 400 }}>
          {text.substring(0, 100)}...
        </div>
      )
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
      )
    },
    {
      title: '类型',
      dataIndex: 'is_default',
      key: 'is_default',
      width: 80,
      render: (isDefault: boolean) => (
        isDefault ? <Tag color="gold">默认</Tag> : <Tag>自定义</Tag>
      )
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 180,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }) : '-'
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (record: PromptTemplate) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            查看
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要重置为默认提示词吗？"
            onConfirm={() => handleReset(record)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              size="small"
              icon={<SyncOutlined />}
            >
              重置
            </Button>
          </Popconfirm>
        </Space>
      )
    }
  ];

  // 按提供商过滤模板
  const filteredTemplates = activeProvider === 'all' 
    ? templates 
    : templates.filter(t => t.provider === activeProvider);

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl border border-blue-200">
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <EditOutlined className="text-white text-sm" />
            </div>
            <div>
              <h4 className="font-semibold text-blue-900 mb-1">大模型提示词管理</h4>
              <p className="text-sm text-blue-800">
                管理不同LLM提供商的样本生成提示词模板。支持查看、编辑和重置提示词,优化样本生成效果。
              </p>
            </div>
          </div>
        </div>
      </div>

      <Card
        title="提示词模板列表"
        extra={
          <Space>
            <Button
              icon={<PlusOutlined />}
              onClick={initDefaultTemplates}
            >
              初始化默认模板
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadTemplates}
            >
              刷新
            </Button>
          </Space>
        }
        className="glass-card"
      >
        <Tabs activeKey={activeProvider} onChange={setActiveProvider} className="mb-4">
          <TabPane tab="全部" key="all" />
          <TabPane tab="通义千问" key="qwen" />
          <TabPane tab="DeepSeek" key="deepseek" />
          <TabPane tab="火山引擎" key="volces" />
        </Tabs>

        <Table
          columns={columns}
          dataSource={filteredTemplates}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showTotal: (total) => `共 ${total} 条`
          }}
        />
      </Card>

      {/* 编辑模态框 */}
      <Modal
        title="编辑提示词模板"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingTemplate(null);
        }}
        onOk={() => form.submit()}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        {editingTemplate && (
          <div className="mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <Tag color={getProviderColor(editingTemplate.provider)}>
                {getProviderName(editingTemplate.provider)}
              </Tag>
              <Tag>{getQuestionTypeName(editingTemplate.question_type)}</Tag>
              {editingTemplate.is_default && <Tag color="gold">默认模板</Tag>}
            </div>
          </div>
        )}
        
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Form.Item
            name="template"
            label="提示词模板"
            rules={[{ required: true, message: '请输入提示词模板' }]}
          >
            <TextArea
              rows={12}
              placeholder="输入提示词模板，可以使用变量: {bank_name}, {bank_code}, {clearing_code}"
              className="font-mono text-sm"
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input placeholder="输入提示词描述" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>

        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-sm text-yellow-800">
            <strong>提示:</strong> 提示词中可以使用以下变量:
          </p>
          <ul className="text-sm text-yellow-800 mt-2 ml-4">
            <li>• <code>{'{bank_name}'}</code> - 银行名称</li>
            <li>• <code>{'{bank_code}'}</code> - 联行号</li>
            <li>• <code>{'{clearing_code}'}</code> - 清算行行号</li>
          </ul>
        </div>
      </Modal>

      {/* 查看模态框 */}
      <Modal
        title="查看提示词模板"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setViewingTemplate(null);
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {viewingTemplate && (
          <div>
            <div className="flex items-center space-x-2 mb-4">
              <Tag color={getProviderColor(viewingTemplate.provider)}>
                {getProviderName(viewingTemplate.provider)}
              </Tag>
              <Tag>{getQuestionTypeName(viewingTemplate.question_type)}</Tag>
              {viewingTemplate.is_default && <Tag color="gold">默认模板</Tag>}
              <Tag color={viewingTemplate.is_active ? 'green' : 'red'}>
                {viewingTemplate.is_active ? '启用' : '禁用'}
              </Tag>
            </div>

            {viewingTemplate.description && (
              <div className="mb-4">
                <div className="text-sm text-gray-600 mb-1">描述:</div>
                <div className="text-gray-800">{viewingTemplate.description}</div>
              </div>
            )}

            <div className="mb-4">
              <div className="text-sm text-gray-600 mb-1">提示词模板:</div>
              <div className="p-4 bg-gray-50 rounded border border-gray-200 font-mono text-sm whitespace-pre-wrap">
                {viewingTemplate.template}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">创建时间:</span>
                <span className="ml-2">{new Date(viewingTemplate.created_at).toLocaleString('zh-CN')}</span>
              </div>
              <div>
                <span className="text-gray-600">更新时间:</span>
                <span className="ml-2">{new Date(viewingTemplate.updated_at).toLocaleString('zh-CN')}</span>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default LLMPromptManagement;
