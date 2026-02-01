/**
 * 极简主义仪表板布局 - SaaS 2.0 风格
 * 
 * 设计原则：
 * - 极简侧边栏：仅显示图标，悬浮展开
 * - 毛玻璃效果：backdrop-filter 和半透明背景
 * - 大片留白：增加视觉呼吸空间
 * - 视觉层级：主色调仅用于激活状态
 * - 现代字体：Inter 字体系统
 */

import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Button } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  MessageOutlined,
  DatabaseOutlined,
  RocketOutlined,
  ApiOutlined,
  CloudServerOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ExperimentOutlined,
  MonitorOutlined,
  TeamOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useAppDispatch, useAppSelector } from '../../hooks/redux';
import { logout } from '../../store/slices/authSlice';

const { Header, Sider, Content } = Layout;

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(true); // 默认收起
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);

  const handleLogout = async () => {
    await dispatch(logout());
    navigate('/login');
  };

  const userMenu = (
    <Menu className="glass-card border-0 shadow-lg">
      <Menu.Item key="profile" icon={<UserOutlined />} className="rounded-lg mx-2 my-1">
        <span className="font-medium">个人信息</span>
      </Menu.Item>
      <Menu.Divider className="my-2 border-gray-200" />
      <Menu.Item 
        key="logout" 
        icon={<LogoutOutlined />} 
        onClick={handleLogout}
        className="rounded-lg mx-2 my-1 text-red-600 hover:bg-red-50"
      >
        <span className="font-medium">退出登录</span>
      </Menu.Item>
    </Menu>
  );

  const menuItems = [
    {
      key: '/dashboard',
      icon: <HomeOutlined className="text-lg" />,
      label: '首页',
    },
    {
      key: '/intelligent-qa',
      icon: <MessageOutlined className="text-lg" />,
      label: '智能问答',
    },
    {
      key: '/dataset-management',
      icon: <DatabaseOutlined className="text-lg" />,
      label: '数据集管理',
    },
    {
      key: 'sample-center',
      icon: <ExperimentOutlined className="text-lg" />,
      label: '样本管理',
      children: [
        {
          key: '/sample-management',
          icon: <ExperimentOutlined className="text-base" />,
          label: '样本管理',
        },
        {
          key: '/llm-prompt-management',
          icon: <MessageOutlined className="text-base" />,
          label: '大模型提示词管理',
        },
      ],
    },
    {
      key: 'training-center',
      icon: <RocketOutlined className="text-lg" />,
      label: '训练中心',
      children: [
        {
          key: '/training',
          icon: <ExperimentOutlined className="text-base" />,
          label: '训练管理',
        },
        {
          key: '/training-monitor',
          icon: <MonitorOutlined className="text-base" />,
          label: '训练监控',
        },
      ],
    },
    {
      key: '/models',
      icon: <ApiOutlined className="text-lg" />,
      label: '模型管理',
    },
    {
      key: 'data-services',
      icon: <CloudServerOutlined className="text-lg" />,
      label: '数据服务',
      children: [
        {
          key: '/rag',
          icon: <ThunderboltOutlined className="text-base" />,
          label: 'RAG管理',
        },
        {
          key: '/redis',
          icon: <DatabaseOutlined className="text-base" />,
          label: 'Redis管理',
        },
      ],
    },
  ];

  // 管理员专用菜单
  if (user?.role === 'admin') {
    menuItems.push({
      key: 'system-management',
      icon: <SettingOutlined className="text-lg" />,
      label: '系统管理',
      children: [
        {
          key: '/users',
          icon: <TeamOutlined className="text-base" />,
          label: '用户管理',
        },
        {
          key: '/permissions',
          icon: <SafetyCertificateOutlined className="text-base" />,
          label: '权限管理',
        },
        {
          key: '/settings',
          icon: <SettingOutlined className="text-base" />,
          label: '系统设置',
        },
        {
          key: '/trace',
          icon: <AuditOutlined className="text-base" />,
          label: '全链追踪',
        },
      ],
    });
  }

  return (
    <div className="minimalist-container">
      <Layout style={{ minHeight: '100vh', background: 'transparent' }}>
        {/* 极简侧边栏 */}
        <Sider 
          trigger={null} 
          collapsible 
          collapsed={collapsed}
          width={240}
          collapsedWidth={64}
          className="fixed left-0 top-0 h-full z-50 transition-all duration-300"
          style={{
            background: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderRight: '1px solid rgba(0, 0, 0, 0.05)',
          }}
          onMouseEnter={() => setCollapsed(false)}
          onMouseLeave={() => setCollapsed(true)}
        >
          {/* Logo 区域 */}
          <div className="flex items-center justify-center h-16 border-b border-gray-100">
            <div className="text-center">
              {collapsed ? (
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">智</span>
                </div>
              ) : (
                <h1 className="font-bold text-lg text-gray-900 transition-all duration-200">
                  银行智能问答系统
                </h1>
              )}
            </div>
          </div>
          
          {/* 导航菜单 */}
          <div className="py-4">
            <Menu
              mode="inline"
              selectedKeys={[location.pathname]}
              items={menuItems}
              onClick={({ key }) => navigate(key)}
              className="border-none bg-transparent"
              inlineIndent={collapsed ? 0 : 24}
            />
          </div>
        </Sider>
        
        <Layout style={{ marginLeft: collapsed ? 64 : 240, transition: 'margin-left 0.3s' }}>
          {/* 极简顶部栏 */}
          <Header 
            className="flex items-center justify-between px-6 h-16 sticky top-0 z-40"
            style={{
              background: 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(20px)',
              WebkitBackdropFilter: 'blur(20px)',
              borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
            }}
          >
            <div className="flex items-center space-x-4">
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
                className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
                style={{ fontSize: '16px', color: '#6b7280' }}
              />
              
              {/* 面包屑导航 */}
              <div className="hidden md:flex items-center space-x-2 text-sm">
                <span className="text-gray-400">/</span>
                <span className="font-medium text-gray-700">
                  {menuItems.find(item => item.key === location.pathname)?.label || '首页'}
                </span>
              </div>
            </div>
            
            {/* 用户信息 */}
            <Dropdown overlay={userMenu} placement="bottomRight" trigger={['click']}>
              <div className="flex items-center space-x-3 cursor-pointer hover:bg-gray-50 px-3 py-2 rounded-xl transition-colors">
                <Avatar 
                  icon={<UserOutlined />} 
                  className="bg-gradient-to-br from-blue-500 to-blue-600"
                  size={32}
                />
                <div className="hidden md:block">
                  <div className="font-medium text-gray-900 text-sm">{user?.username}</div>
                  <div className="text-xs text-gray-500">{user?.role === 'admin' ? '管理员' : '用户'}</div>
                </div>
              </div>
            </Dropdown>
          </Header>
          
          {/* 主内容区域 */}
          <Content 
            className="content-area"
            style={{
              background: 'transparent',
              minHeight: 'calc(100vh - 64px)',
              overflow: 'auto',
            }}
          >
            {children}
          </Content>
        </Layout>

        {/* 移动端菜单遮罩 */}
        {mobileMenuOpen && (
          <div 
            className="fixed inset-0 bg-black bg-opacity-20 z-40 md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
        )}
      </Layout>
    </div>
  );
};

export default DashboardLayout;