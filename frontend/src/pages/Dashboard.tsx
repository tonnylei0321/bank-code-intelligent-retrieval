/**
 * 仪表盘页面
 * 
 * 功能：
 * - 系统概览统计
 * - 最近训练任务
 * - 最近查询记录
 * - 快捷操作
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Progress,
  List,
  Space,
  Button,
} from 'antd';
import {
  DatabaseOutlined,
  RocketOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { dataAPI, trainingAPI, queryAPI } from '../services/api';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    datasetCount: 0,
    trainingJobCount: 0,
    queryCount: 0,
    completedJobCount: 0,
  });
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [recentQueries, setRecentQueries] = useState<any[]>([]);

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

      setStats({
        datasetCount: datasets.length,
        trainingJobCount: jobs.length,
        queryCount: queries.length,
        completedJobCount: jobs.filter((j: any) => j.status === 'completed').length,
      });

      setRecentJobs(jobs.slice(0, 5));
      setRecentQueries(queries.slice(0, 10));
    } catch (error) {
      console.error('获取统计数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  // 训练任务表格列
  const jobColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error',
          stopped: 'warning',
        };
        return <Tag color={colorMap[status]}>{status}</Tag>;
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number) => (
        <Progress percent={Math.round(progress || 0)} size="small" />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ];

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>系统概览</h1>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据集总数"
              value={stats.datasetCount}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
            <Button
              type="link"
              size="small"
              onClick={() => navigate('/data')}
              style={{ marginTop: 8 }}
            >
              查看详情 →
            </Button>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="训练任务总数"
              value={stats.trainingJobCount}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <Button
              type="link"
              size="small"
              onClick={() => navigate('/training')}
              style={{ marginTop: 8 }}
            >
              查看详情 →
            </Button>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成训练"
              value={stats.completedJobCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <Button
              type="link"
              size="small"
              onClick={() => navigate('/models')}
              style={{ marginTop: 8 }}
            >
              查看模型 →
            </Button>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="查询次数"
              value={stats.queryCount}
              prefix={<QuestionCircleOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
            <Button
              type="link"
              size="small"
              onClick={() => navigate('/qa')}
              style={{ marginTop: 8 }}
            >
              开始问答 →
            </Button>
          </Card>
        </Col>
      </Row>

      {/* 快捷操作 */}
      <Card title="快捷操作" style={{ marginBottom: 24 }}>
        <Space size="middle">
          <Button
            type="primary"
            icon={<DatabaseOutlined />}
            onClick={() => navigate('/data')}
          >
            上传数据集
          </Button>
          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => navigate('/training')}
          >
            创建训练任务
          </Button>
          <Button
            type="primary"
            icon={<QuestionCircleOutlined />}
            onClick={() => navigate('/qa')}
          >
            智能问答
          </Button>
        </Space>
      </Card>

      <Row gutter={16}>
        {/* 最近训练任务 */}
        <Col span={14}>
          <Card
            title="最近训练任务"
            extra={
              <Button type="link" onClick={() => navigate('/training')}>
                查看全部 →
              </Button>
            }
          >
            <Table
              columns={jobColumns}
              dataSource={recentJobs}
              loading={loading}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>

        {/* 最近查询记录 */}
        <Col span={10}>
          <Card
            title="最近查询记录"
            extra={
              <Button type="link" onClick={() => navigate('/qa')}>
                查看全部 →
              </Button>
            }
          >
            <List
              loading={loading}
              dataSource={recentQueries}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <div style={{ fontSize: 13 }}>
                        <Tag color="blue" style={{ marginRight: 8 }}>
                          Q
                        </Tag>
                        {item.question}
                      </div>
                    }
                    description={
                      <div style={{ fontSize: 12, color: '#666' }}>
                        <Space size="small">
                          <ClockCircleOutlined />
                          <span>
                            {new Date(item.created_at).toLocaleString('zh-CN')}
                          </span>
                          {item.response_time && (
                            <span>{item.response_time}ms</span>
                          )}
                        </Space>
                      </div>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无查询记录' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
