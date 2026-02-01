/**
 * 权限管理页面
 * 
 * 功能：
 * - 角色权限管理
 * - 用户权限分配
 * - 权限组管理
 * - 权限审计日志
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Tree,
  Switch,
  Alert,
  Tabs,
  List,
  Typography,
  Divider,
  Tooltip,
  message,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  SafetyCertificateOutlined,
  UserOutlined,
  TeamOutlined,
  SettingOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  AuditOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

const { TabPane } = Tabs;
const { Text, Title } = Typography;
const { Option } = Select;
const { TreeNode } = Tree;

interface Role {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  user_count: number;
  created_at: string;
  is_system: boolean;
}

interface Permission {
  id: string;
  name: string;
  description: string;
  category: string;
  is_system: boolean;
}

interface PermissionGroup {
  id: number;
  name: string;
  description: string;
  permissions: string[];
  created_at: string;
}

interface AuditLog {
  id: number;
  user_id: number;
  user_name: string;
  action: string;
  resource: string;
  details: string;
  ip_address: string;
  created_at: string;
}

const PermissionManagement: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [permissionGroups, setPermissionGroups] = useState<PermissionGroup[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [modalType, setModalType] = useState<'role' | 'group'>('role');
  const [editingItem, setEditingItem] = useState<any>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('roles');

  // 权限树数据
  const permissionTree = [
    {
      title: '系统管理',
      key: 'system',
      children: [
        { title: '用户管理', key: 'user.manage' },
        { title: '角色管理', key: 'role.manage' },
        { title: '权限管理', key: 'permission.manage' },
        { title: '系统设置', key: 'system.settings' },
      ],
    },
    {
      title: '数据管理',
      key: 'data',
      children: [
        { title: '数据集管理', key: 'dataset.manage' },
        { title: '数据上传', key: 'data.upload' },
        { title: '数据导出', key: 'data.export' },
        { title: '数据删除', key: 'data.delete' },
      ],
    },
    {
      title: '训练管理',
      key: 'training',
      children: [
        { title: '创建训练任务', key: 'training.create' },
        { title: '管理训练任务', key: 'training.manage' },
        { title: '查看训练结果', key: 'training.view' },
        { title: '删除训练任务', key: 'training.delete' },
      ],
    },
    {
      title: '模型管理',
      key: 'model',
      children: [
        { title: '模型部署', key: 'model.deploy' },
        { title: '模型管理', key: 'model.manage' },
        { title: '模型评估', key: 'model.evaluate' },
        { title: '模型删除', key: 'model.delete' },
      ],
    },
    {
      title: '问答服务',
      key: 'qa',
      children: [
        { title: '智能问答', key: 'qa.intelligent' },
        { title: '传统问答', key: 'qa.traditional' },
        { title: '问答历史', key: 'qa.history' },
        { title: '问答统计', key: 'qa.statistics' },
      ],
    },
  ];

  // 获取角色列表
  const fetchRoles = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      const mockRoles: Role[] = [
        {
          id: 1,
          name: '超级管理员',
          description: '拥有所有权限的系统管理员',
          permissions: ['*'],
          user_count: 2,
          created_at: '2024-01-01T00:00:00Z',
          is_system: true,
        },
        {
          id: 2,
          name: '训练管理员',
          description: '负责模型训练和管理',
          permissions: ['training.*', 'model.*', 'data.view'],
          user_count: 5,
          created_at: '2024-01-02T00:00:00Z',
          is_system: false,
        },
        {
          id: 3,
          name: '普通用户',
          description: '基础用户权限',
          permissions: ['qa.intelligent', 'qa.traditional', 'qa.history'],
          user_count: 20,
          created_at: '2024-01-03T00:00:00Z',
          is_system: false,
        },
      ];
      setRoles(mockRoles);
    } catch (error) {
      console.error('获取角色列表失败:', error);
      message.error('获取角色列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取权限组列表
  const fetchPermissionGroups = async () => {
    try {
      // 模拟API调用
      const mockGroups: PermissionGroup[] = [
        {
          id: 1,
          name: '数据管理组',
          description: '数据相关的所有权限',
          permissions: ['data.*'],
          created_at: '2024-01-01T00:00:00Z',
        },
        {
          id: 2,
          name: '训练管理组',
          description: '训练相关的所有权限',
          permissions: ['training.*', 'model.view'],
          created_at: '2024-01-02T00:00:00Z',
        },
      ];
      setPermissionGroups(mockGroups);
    } catch (error) {
      console.error('获取权限组失败:', error);
    }
  };

  // 获取审计日志
  const fetchAuditLogs = async () => {
    try {
      // 模拟API调用
      const mockLogs: AuditLog[] = [
        {
          id: 1,
          user_id: 1,
          user_name: 'admin',
          action: '创建角色',
          resource: '训练管理员',
          details: '创建了新的角色：训练管理员',
          ip_address: '192.168.1.100',
          created_at: '2024-02-01T10:30:00Z',
        },
        {
          id: 2,
          user_id: 2,
          user_name: 'manager',
          action: '分配权限',
          resource: '用户权限',
          details: '为用户张三分配了数据管理权限',
          ip_address: '192.168.1.101',
          created_at: '2024-02-01T09:15:00Z',
        },
      ];
      setAuditLogs(mockLogs);
    } catch (error) {
      console.error('获取审计日志失败:', error);
    }
  };

  // 创建/编辑角色
  const handleSaveRole = async (values: any) => {
    try {
      if (editingItem) {
        message.success('角色更新成功');
      } else {
        message.success('角色创建成功');
      }
      setModalVisible(false);
      form.resetFields();
      setEditingItem(null);
      fetchRoles();
    } catch (error) {
      console.error('保存角色失败:', error);
      message.error('保存失败');
    }
  };

  // 删除角色
  const handleDeleteRole = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个角色吗？此操作不可恢复。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          message.success('删除成功');
          fetchRoles();
        } catch (error) {
          console.error('删除角色失败:', error);
          message.error('删除失败');
        }
      },
    });
  };

  useEffect(() => {
    fetchRoles();
    fetchPermissionGroups();
    fetchAuditLogs();
  }, []);

  // 角色表格列
  const roleColumns = [
    {
      title: '角色名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Role) => (
        <div>
          <Text strong>{text}</Text>
          {record.is_system && (
            <Tag color="red" size="small" style={{ marginLeft: 8 }}>
              系统角色
            </Tag>
          )}
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description}
          </Text>
        </div>
      ),
    },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      key: 'permissions',
      width: 120,
      render: (permissions: string[]) => (
        <Statistic
          value={permissions.length}
          valueStyle={{ fontSize: 14 }}
          prefix={<SafetyCertificateOutlined />}
        />
      ),
    },
    {
      title: '用户数量',
      dataIndex: 'user_count',
      key: 'user_count',
      width: 120,
      render: (count: number) => (
        <Statistic
          value={count}
          valueStyle={{ fontSize: 14 }}
          prefix={<UserOutlined />}
        />
      ),
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
      render: (_, record: Role) => (
        <Space>
          <Tooltip title="查看权限">
            <Button
              type="link"
              icon={<EyeOutlined />}
              onClick={() => {
                Modal.info({
                  title: `${record.name} - 权限详情`,
                  content: (
                    <div>
                      {record.permissions.map((perm, index) => (
                        <Tag key={index} style={{ margin: 4 }}>
                          {perm}
                        </Tag>
                      ))}
                    </div>
                  ),
                  width: 600,
                });
              }}
            />
          </Tooltip>
          <Tooltip title="编辑角色">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingItem(record);
                setModalType('role');
                form.setFieldsValue(record);
                setModalVisible(true);
              }}
              disabled={record.is_system}
            />
          </Tooltip>
          <Tooltip title="删除角色">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteRole(record.id)}
              disabled={record.is_system}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 权限组表格列
  const groupColumns = [
    {
      title: '组名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: PermissionGroup) => (
        <div>
          <Text strong>{text}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.description}
          </Text>
        </div>
      ),
    },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      key: 'permissions',
      width: 120,
      render: (permissions: string[]) => (
        <Statistic
          value={permissions.length}
          valueStyle={{ fontSize: 14 }}
          prefix={<SafetyCertificateOutlined />}
        />
      ),
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
      width: 150,
      render: (_, record: PermissionGroup) => (
        <Space>
          <Tooltip title="编辑权限组">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingItem(record);
                setModalType('group');
                form.setFieldsValue(record);
                setModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="删除权限组">
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 审计日志表格列
  const auditColumns = [
    {
      title: '用户',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 100,
      render: (name: string) => (
        <Tag color="blue" icon={<UserOutlined />}>
          {name}
        </Tag>
      ),
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      width: 120,
      render: (action: string) => (
        <Tag color="green">{action}</Tag>
      ),
    },
    {
      title: '资源',
      dataIndex: 'resource',
      key: 'resource',
      width: 150,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1>权限管理</h1>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingItem(null);
              setModalType('role');
              form.resetFields();
              setModalVisible(true);
            }}
          >
            创建角色
          </Button>
          <Button
            icon={<TeamOutlined />}
            onClick={() => {
              setEditingItem(null);
              setModalType('group');
              form.resetFields();
              setModalVisible(true);
            }}
          >
            创建权限组
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总角色数"
              value={roles.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="权限组数"
              value={permissionGroups.length}
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="系统角色"
              value={roles.filter(r => r.is_system).length}
              prefix={<SettingOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日操作"
              value={auditLogs.length}
              prefix={<AuditOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="角色管理" key="roles">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="角色管理"
                description="管理系统角色和权限分配。系统角色不可编辑或删除。"
                type="info"
                showIcon
              />
            </div>
            
            <Table
              columns={roleColumns}
              dataSource={roles}
              loading={loading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个角色`,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="权限组" key="groups">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="权限组管理"
                description="管理权限组，可以将相关权限组合在一起，便于批量分配。"
                type="info"
                showIcon
              />
            </div>
            
            <Table
              columns={groupColumns}
              dataSource={permissionGroups}
              loading={loading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 个权限组`,
              }}
            />
          </Card>
        </TabPane>

        <TabPane tab="审计日志" key="audit">
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="权限审计日志"
                description="记录所有权限相关的操作，包括角色创建、权限分配等。"
                type="info"
                showIcon
              />
            </div>
            
            <Table
              columns={auditColumns}
              dataSource={auditLogs}
              loading={loading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 创建/编辑模态框 */}
      <Modal
        title={`${editingItem ? '编辑' : '创建'}${modalType === 'role' ? '角色' : '权限组'}`}
        visible={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingItem(null);
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveRole}
        >
          <Form.Item
            name="name"
            label={`${modalType === 'role' ? '角色' : '权限组'}名称`}
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="输入名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea
              rows={3}
              placeholder="输入描述信息"
            />
          </Form.Item>

          <Form.Item
            name="permissions"
            label="权限配置"
            rules={[{ required: true, message: '请选择权限' }]}
          >
            <Tree
              checkable
              defaultExpandAll
              treeData={permissionTree}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingItem ? '更新' : '创建'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PermissionManagement;