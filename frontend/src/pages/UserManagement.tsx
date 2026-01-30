/**
 * 用户管理页面（管理员）
 * 
 * 功能：
 * - 用户列表展示
 * - 查看用户详情
 * - 删除用户
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  message,
  Space,
  Tag,
  Drawer,
  Descriptions,
} from 'antd';
import {
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { adminAPI } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // 获取用户列表
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await adminAPI.getAllUsers();
      setUsers(response.data || []);
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 查看用户详情
  const handleViewDetail = (user: User) => {
    setSelectedUser(user);
    setDetailDrawerVisible(true);
  };

  // 删除用户
  const handleDelete = (user: User) => {
    Modal.confirm({
      title: '确认删除用户',
      content: `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await adminAPI.deleteUser(user.id);
          message.success('用户已删除');
          fetchUsers();
        } catch (error: any) {
          message.error(error.response?.data?.error_message || '删除失败');
        }
      },
    });
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>
          {role === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'success' : 'default'}>
          {isActive ? '激活' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
            disabled={record.role === 'admin'} // 不能删除管理员
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title={
          <Space>
            <UserOutlined />
            用户管理
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchUsers}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={users}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 个用户`,
          }}
        />
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="用户详情"
        placement="right"
        width={500}
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
      >
        {selectedUser && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="用户ID">{selectedUser.id}</Descriptions.Item>
            <Descriptions.Item label="用户名">
              {selectedUser.username}
            </Descriptions.Item>
            <Descriptions.Item label="邮箱">{selectedUser.email}</Descriptions.Item>
            <Descriptions.Item label="角色">
              <Tag color={selectedUser.role === 'admin' ? 'red' : 'blue'}>
                {selectedUser.role === 'admin' ? '管理员' : '普通用户'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedUser.is_active ? 'success' : 'default'}>
                {selectedUser.is_active ? '激活' : '禁用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedUser.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {new Date(selectedUser.updated_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default UserManagement;
