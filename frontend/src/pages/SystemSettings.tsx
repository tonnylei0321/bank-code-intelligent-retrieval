/**
 * 系统设置页面（管理员）
 * 
 * 功能：
 * - 查看系统日志
 * - 日志级别筛选
 * - 日志文件列表
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Select,
  Button,
  message,
  Space,
  Tag,
  List,
  Row,
  Col,
} from 'antd';
import {
  ReloadOutlined,
  FileTextOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { logsAPI } from '../services/api';

interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  module: string;
}

const SystemSettings: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logFiles, setLogFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [logLevel, setLogLevel] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);

  // 获取日志
  const fetchLogs = async (page: number = 1, level: string = '') => {
    setLoading(true);
    try {
      const response = await logsAPI.getLogs({
        page,
        page_size: 50,
        level: level || undefined,
      });
      setLogs(response.data?.logs || []);
    } catch (error: any) {
      message.error('获取日志失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取日志文件列表
  const fetchLogFiles = async () => {
    try {
      const response = await logsAPI.getLogFiles();
      setLogFiles(response.data || []);
    } catch (error) {
      console.error('获取日志文件列表失败');
    }
  };

  useEffect(() => {
    fetchLogs(1, logLevel);
    fetchLogFiles();
  }, []);

  // 日志级别颜色映射
  const getLevelColor = (level: string) => {
    const colorMap: Record<string, string> = {
      DEBUG: 'default',
      INFO: 'blue',
      WARNING: 'orange',
      ERROR: 'red',
      CRITICAL: 'red',
    };
    return colorMap[level] || 'default';
  };

  // 表格列定义
  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 100,
      render: (level: string) => (
        <Tag color={getLevelColor(level)}>{level}</Tag>
      ),
    },
    {
      title: '模块',
      dataIndex: 'module',
      key: 'module',
      width: 150,
      ellipsis: true,
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
  ];

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>
        <SettingOutlined /> 系统设置
      </h1>

      <Row gutter={16}>
        {/* 左侧：系统日志 */}
        <Col span={18}>
          <Card
            title="系统日志"
            extra={
              <Space>
                <Select
                  style={{ width: 120 }}
                  placeholder="日志级别"
                  allowClear
                  value={logLevel || undefined}
                  onChange={(value) => {
                    setLogLevel(value || '');
                    setCurrentPage(1);
                    fetchLogs(1, value || '');
                  }}
                >
                  <Select.Option value="DEBUG">DEBUG</Select.Option>
                  <Select.Option value="INFO">INFO</Select.Option>
                  <Select.Option value="WARNING">WARNING</Select.Option>
                  <Select.Option value="ERROR">ERROR</Select.Option>
                  <Select.Option value="CRITICAL">CRITICAL</Select.Option>
                </Select>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => fetchLogs(currentPage, logLevel)}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <Table
              columns={columns}
              dataSource={logs}
              loading={loading}
              rowKey={(record, index) => `${record.timestamp}-${index}`}
              pagination={{
                current: currentPage,
                pageSize: 50,
                onChange: (page) => {
                  setCurrentPage(page);
                  fetchLogs(page, logLevel);
                },
                showTotal: (total) => `共 ${total} 条日志`,
              }}
              size="small"
            />
          </Card>
        </Col>

        {/* 右侧：日志文件列表 */}
        <Col span={6}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                日志文件
              </Space>
            }
            extra={
              <Button size="small" icon={<ReloadOutlined />} onClick={fetchLogFiles}>
                刷新
              </Button>
            }
          >
            <List
              dataSource={logFiles}
              renderItem={(file) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<FileTextOutlined />}
                    title={<span style={{ fontSize: 13 }}>{file}</span>}
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无日志文件' }}
            />
          </Card>

          <Card
            title="系统信息"
            style={{ marginTop: 16 }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <strong>应用名称：</strong>
                <br />
                银行代码检索系统
              </div>
              <div>
                <strong>版本：</strong>
                <br />
                v1.0.0
              </div>
              <div>
                <strong>后端框架：</strong>
                <br />
                FastAPI + Python
              </div>
              <div>
                <strong>前端框架：</strong>
                <br />
                React + TypeScript
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemSettings;
