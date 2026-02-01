/**
 * 极简主义仪表板页面 - SaaS 2.0 风格
 * 
 * 设计原则：
 * - 极简主义：大片留白，移除多余装饰
 * - 毛玻璃效果：backdrop-filter 和半透明背景
 * - 视觉层级：大号数据，小号辅助信息
 * - Bento Grid：便当格布局风格
 * - 现代字体：Inter 字体系统
 */

import React, { useState, useEffect } from 'react';
import { Card, Button, List, Empty, Avatar } from 'antd';
import {
  MessageOutlined,
  DatabaseOutlined,
  RocketOutlined,
  ApiOutlined,
  UserOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { dataAPI, trainingAPI, queryAPI } from '../services/api';

interface SystemMetrics {
  totalQuestions: number;
  successRate: number;
  avgResponseTime: number;
  activeUsers: number;
  redisRecords: number;
  trainingJobs: number;
  modelsDeployed: number;
  systemHealth: number;
}

interface RecentActivity {
  id: string;
  type: 'question' | 'training' | 'model' | 'user';
  title: string;
  description: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error';
  user?: string;
}

interface QuickAction {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  path: string;
  shortcut?: string;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<SystemMetrics>({
    totalQuestions: 0,
    successRate: 0,
    avgResponseTime: 0,
    activeUsers: 0,
    redisRecords: 159475,
    trainingJobs: 0,
    modelsDeployed: 0,
    systemHealth: 98.5,
  });

  const [recentActivities, setRecentActivities] = useState<RecentActivity[]>([]);

  const quickActions: QuickAction[] = [
    {
      key: 'intelligent-qa',
      title: '智能问答',
      description: '开始新的问答会话',
      icon: <MessageOutlined className="text-xl" />,
      color: 'from-blue-500 to-blue-600',
      path: '/intelligent-qa',
      shortcut: 'Q',
    },
    {
      key: 'training',
      title: '创建训练',
      description: '启动新的模型训练',
      icon: <RocketOutlined className="text-xl" />,
      color: 'from-green-500 to-green-600',
      path: '/training-center',
      shortcut: 'T',
    },
    {
      key: 'samples',
      title: '样本管理',
      description: '管理训练数据',
      icon: <DatabaseOutlined className="text-xl" />,
      color: 'from-purple-500 to-purple-600',
      path: '/sample-management',
      shortcut: 'S',
    },
    {
      key: 'models',
      title: '模型管理',
      description: '部署和管理模型',
      icon: <ApiOutlined className="text-xl" />,
      color: 'from-orange-500 to-orange-600',
      path: '/models',
      shortcut: 'M',
    },
  ];

  // 获取统计数据
  const fetchStats = async () => {
    setLoading(true);
    try {
      // 获取数据集数量
      const datasetsRes = await dataAPI.getDatasets();
      const datasets = datasetsRes.data || [];

      // 获取训练任务
      const jobsRes = await trainingAPI.getTrainingJobs();
      const jobs = jobsRes.data?.jobs || [];

      // 获取查询历史
      const queriesRes = await queryAPI.getQueryHistory(20);
      const queries = queriesRes.data?.queries || [];

      // 计算指标
      const completedJobs = jobs.filter((j: any) => j.status === 'completed');
      const successfulQueries = queries.filter((q: any) => q.confidence > 0.7);
      const avgTime = queries.length > 0 
        ? queries.reduce((sum: number, q: any) => sum + (q.response_time || 0), 0) / queries.length / 1000
        : 0;

      setMetrics({
        totalQuestions: queries.length,
        successRate: queries.length > 0 ? (successfulQueries.length / queries.length) * 100 : 0,
        avgResponseTime: avgTime,
        activeUsers: 156, // 模拟数据
        redisRecords: 159475,
        trainingJobs: jobs.length,
        modelsDeployed: completedJobs.length,
        systemHealth: 98.5,
      });

      // 构建最近活动
      const activities: RecentActivity[] = [
        ...queries.slice(0, 3).map((q: any, index: number) => ({
          id: `q-${index}`,
          type: 'question' as const,
          title: '智能问答查询',
          description: q.question.length > 50 ? q.question.substring(0, 50) + '...' : q.question,
          timestamp: getRelativeTime(q.created_at),
          status: q.confidence > 0.7 ? 'success' as const : 'warning' as const,
          user: '用户',
        })),
        ...jobs.slice(0, 2).map((j: any, index: number) => ({
          id: `j-${index}`,
          type: 'training' as const,
          title: j.status === 'completed' ? '模型训练完成' : '模型训练中',
          description: `${j.model_name} - 任务 #${j.id}`,
          timestamp: getRelativeTime(j.created_at),
          status: j.status === 'completed' ? 'success' as const : 
                  j.status === 'failed' ? 'error' as const : 'warning' as const,
          user: '系统',
        })),
      ];

      setRecentActivities(activities);
    } catch (error) {
      console.error('获取统计数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取相对时间
  const getRelativeTime = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    return `${diffDays}天前`;
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'question':
        return <MessageOutlined className="text-blue-500" />;
      case 'training':
        return <RocketOutlined className="text-green-500" />;
      case 'model':
        return <ApiOutlined className="text-purple-500" />;
      case 'user':
        return <UserOutlined className="text-orange-500" />;
      default:
        return <MessageOutlined className="text-gray-500" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined className="text-green-500 text-xs" />;
      case 'warning':
        return <ExclamationCircleOutlined className="text-yellow-500 text-xs" />;
      case 'error':
        return <ExclamationCircleOutlined className="text-red-500 text-xs" />;
      default:
        return <CheckCircleOutlined className="text-gray-500 text-xs" />;
    }
  };

  // 键盘快捷键处理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.altKey) {
        const action = quickActions.find(a => a.shortcut?.toLowerCase() === event.key.toLowerCase());
        if (action) {
          navigate(action.path);
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [navigate]);

  useEffect(() => {
    fetchStats();
  }, []);

  return (
    <div className="minimalist-container">
      <div className="content-area">
        {/* 页面标题 - 极简设计 */}
        <div className="section-spacing">
          <h1 className="title-primary">银行智能问答系统</h1>
          <p className="subtitle">
            现代化的AI驱动问答平台，为银行业务提供智能化服务支持
          </p>
        </div>

        {/* 核心指标 - Bento Grid 布局 */}
        <div className="bento-grid-4 section-spacing">
          <Card className="glass-card group hover:scale-105 transition-all duration-300 cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">总问答数</p>
                <p className="metric-primary">{metrics.totalQuestions.toLocaleString()}</p>
                <div className="flex items-center mt-3">
                  <ArrowUpOutlined className="text-green-500 text-xs mr-1" />
                  <span className="text-xs text-green-600 font-medium">+12.5% 较昨日</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <MessageOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300 cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">成功率</p>
                <p className="metric-primary">{metrics.successRate.toFixed(1)}%</p>
                <div className="mt-3">
                  <div className="progress-glass">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${metrics.successRate}%` }}
                    />
                  </div>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300 cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">平均响应时间</p>
                <p className="metric-primary">{metrics.avgResponseTime.toFixed(1)}s</p>
                <div className="flex items-center mt-3">
                  <ArrowDownOutlined className="text-green-500 text-xs mr-1" />
                  <span className="text-xs text-green-600 font-medium">-0.3s 较昨日</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <CheckCircleOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300 cursor-pointer">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">活跃用户</p>
                <p className="metric-primary">{metrics.activeUsers}</p>
                <div className="flex items-center mt-3">
                  <ArrowUpOutlined className="text-green-500 text-xs mr-1" />
                  <span className="text-xs text-green-600 font-medium">+8 较昨日</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <UserOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>
        </div>

        {/* 快捷操作 - 大片留白设计 */}
        <div className="section-spacing">
          <div className="flex items-center justify-between mb-8">
            <h2 className="title-secondary">快捷操作</h2>
            <p className="metric-secondary">使用 Alt + 快捷键快速访问</p>
          </div>
          
          <div className="bento-grid-4">
            {quickActions.map((action) => (
              <Card 
                key={action.key}
                className="glass-card cursor-pointer group hover:scale-105 transition-all duration-300"
                onClick={() => navigate(action.path)}
              >
                <div className="flex items-center space-x-4">
                  <div className={`w-14 h-14 bg-gradient-to-br ${action.color} rounded-2xl flex items-center justify-center text-white group-hover:scale-110 transition-transform`}>
                    {action.icon}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors mb-1">
                      {action.title}
                    </h3>
                    <p className="text-sm text-gray-600 mb-2">{action.description}</p>
                    {action.shortcut && (
                      <div className="tag-primary">Alt + {action.shortcut}</div>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* 底部信息区域 - 两栏布局 */}
        <div className="bento-grid-2">
          {/* 系统状态 */}
          <Card className="glass-card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="title-secondary mb-0">系统状态</h3>
              <div className="tag-success">健康</div>
            </div>
            
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <span className="metric-secondary">Redis 记录数</span>
                <span className="font-bold text-lg text-gray-900">{metrics.redisRecords.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="metric-secondary">训练任务</span>
                <span className="font-bold text-lg text-gray-900">{metrics.trainingJobs}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="metric-secondary">部署模型</span>
                <span className="font-bold text-lg text-gray-900">{metrics.modelsDeployed}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="metric-secondary">系统健康度</span>
                <div className="flex items-center space-x-3">
                  <div className="progress-glass w-20">
                    <div 
                      className="progress-bar" 
                      style={{ width: `${metrics.systemHealth}%` }}
                    />
                  </div>
                  <span className="font-bold text-lg text-green-600">{metrics.systemHealth}%</span>
                </div>
              </div>
            </div>
          </Card>

          {/* 最近活动 */}
          <Card className="glass-card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="title-secondary mb-0">最近活动</h3>
              <Button 
                type="text" 
                size="small" 
                className="text-gray-500 hover:text-blue-600 font-medium"
              >
                查看全部
              </Button>
            </div>
            
            {recentActivities.length > 0 ? (
              <List
                dataSource={recentActivities}
                renderItem={(item) => (
                  <List.Item className="border-none px-0 py-4 hover:bg-gray-50 hover:bg-opacity-50 rounded-xl transition-colors">
                    <List.Item.Meta
                      avatar={
                        <div className="relative">
                          <Avatar 
                            size={40} 
                            className="bg-gray-100 border-2 border-white shadow-sm"
                            icon={getActivityIcon(item.type)}
                          />
                          <div className="absolute -bottom-1 -right-1">
                            {getStatusIcon(item.status)}
                          </div>
                        </div>
                      }
                      title={
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-gray-900">{item.title}</span>
                          <span className="metric-secondary">{item.timestamp}</span>
                        </div>
                      }
                      description={
                        <div>
                          <p className="text-sm text-gray-600 mb-2">{item.description}</p>
                          {item.user && (
                            <div className="tag-glass">
                              {item.user}
                            </div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={<span className="metric-secondary">暂无最近活动</span>}
              />
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
