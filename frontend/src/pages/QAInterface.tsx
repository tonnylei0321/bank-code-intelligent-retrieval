/**
 * 智能问答页面
 * 
 * 功能：
 * - 问答输入和提交
 * - 实时显示答案
 * - 查询历史记录
 * - RAG开关
 * - 响应时间显示
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  List,
  message,
  Space,
  Tag,
  Switch,
  Spin,
  Empty,
  Divider,
  Row,
  Col,
  Statistic,
  Select,
  Alert,
} from 'antd';
import {
  SendOutlined,
  HistoryOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { queryAPI, trainingAPI } from '../services/api';

const { TextArea } = Input;

interface QueryRecord {
  id: number;
  question: string;
  answer: string;
  response_time: number;
  confidence: number;  // 修改字段名
  model_version: string;
  created_at: string;
}

interface TrainingJob {
  id: number;
  model_name: string;
  status: string;
  model_path: string;
  completed_at: string;
  train_loss: number;
  val_loss: number;
}

const QAInterface: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [useRAG, setUseRAG] = useState(true);
  const [currentAnswer, setCurrentAnswer] = useState<any>(null);
  const [history, setHistory] = useState<QueryRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState<TrainingJob[]>([]);
  const [selectedModel, setSelectedModel] = useState<number | null>(null);
  const [modelsLoading, setModelsLoading] = useState(false);

  // 获取可用的训练模型
  const fetchAvailableModels = async () => {
    setModelsLoading(true);
    try {
      const response = await trainingAPI.getTrainingJobs();
      const completedJobs = (response.data?.jobs || []).filter(
        (job: TrainingJob) => job.status === 'completed' && job.model_path
      );
      setAvailableModels(completedJobs);
      
      // 默认选择最新的模型
      if (completedJobs.length > 0 && !selectedModel) {
        setSelectedModel(completedJobs[0].id);
      }
    } catch (error: any) {
      console.error('获取模型列表失败', error);
    } finally {
      setModelsLoading(false);
    }
  };

  // 获取查询历史
  const fetchHistory = async () => {
    setHistoryLoading(true);
    try {
      const response = await queryAPI.getQueryHistory(50);
      console.log('History response:', response.data); // 调试日志
      setHistory(response.data?.items || []); // 修改为 items 字段
    } catch (error: any) {
      console.error('获取历史记录失败', error);
      message.error('获取历史记录失败');
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailableModels();
    fetchHistory();
  }, []);

  // 提交查询
  const handleQuery = async () => {
    if (!question.trim()) {
      message.warning('请输入问题');
      return;
    }

    if (!selectedModel) {
      message.warning('请选择一个训练好的模型');
      return;
    }

    setLoading(true);
    setCurrentAnswer(null);

    try {
      const startTime = Date.now();
      const response = await queryAPI.query({
        question: question.trim(),
        use_rag: useRAG,
        top_k: 5,
        model_id: selectedModel,  // 传递选中的模型ID
      });
      const endTime = Date.now();

      const result = {
        ...response.data,
        response_time: endTime - startTime,
        model_id: selectedModel,
        question: question.trim(), // 保留用户的问题
      };

      setCurrentAnswer(result);
      // 不清空问题输入框，让用户可以看到自己问的问题
      // setQuestion(''); // 注释掉这行
      
      // 刷新历史记录
      fetchHistory();
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '查询失败');
    } finally {
      setLoading(false);
    }
  };

  // 按回车提交
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  return (
    <div>
      <Row gutter={16}>
        {/* 左侧：问答界面 */}
        <Col span={16}>
          <Card title="智能问答" style={{ minHeight: 600 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {/* 模型选择区域 */}
              <Alert
                message="模型选择"
                description={
                  <div style={{ marginTop: 8 }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div>
                        <RobotOutlined style={{ marginRight: 8 }} />
                        <span>请选择要使用的训练模型：</span>
                      </div>
                      <Select
                        style={{ width: '100%' }}
                        placeholder="选择训练好的模型"
                        value={selectedModel}
                        onChange={setSelectedModel}
                        loading={modelsLoading}
                        disabled={modelsLoading || availableModels.length === 0}
                      >
                        {availableModels.map((job) => (
                          <Select.Option key={job.id} value={job.id}>
                            <div>
                              <Tag color="blue">Job #{job.id}</Tag>
                              <span style={{ fontWeight: 500 }}>{job.model_name}</span>
                              {job.train_loss && (
                                <span style={{ color: '#666', marginLeft: 8, fontSize: 12 }}>
                                  (Loss: {job.train_loss.toFixed(4)})
                                </span>
                              )}
                              <span style={{ color: '#999', marginLeft: 8, fontSize: 11 }}>
                                {new Date(job.completed_at).toLocaleDateString('zh-CN')}
                              </span>
                            </div>
                          </Select.Option>
                        ))}
                      </Select>
                      {availableModels.length === 0 && !modelsLoading && (
                        <div style={{ color: '#ff4d4f', fontSize: 12 }}>
                          暂无可用模型，请先训练模型
                        </div>
                      )}
                      {selectedModel && (
                        <div style={{ fontSize: 12, color: '#52c41a' }}>
                          ✓ 当前使用模型：
                          {availableModels.find((j) => j.id === selectedModel)?.model_name}
                        </div>
                      )}
                    </Space>
                  </div>
                }
                type="info"
                showIcon
              />

              {/* 输入区域 */}
              <div>
                <div style={{ marginBottom: 8 }}>
                  <Space>
                    <span>RAG检索增强：</span>
                    <Switch
                      checked={useRAG}
                      onChange={setUseRAG}
                      checkedChildren="开启"
                      unCheckedChildren="关闭"
                    />
                    <span style={{ color: '#666', fontSize: 12 }}>
                      {useRAG ? '将使用知识库检索增强回答' : '仅使用模型直接回答'}
                    </span>
                  </Space>
                </div>

                <TextArea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="请输入您的问题，例如：中国银行的银行代码是什么？"
                  rows={4}
                  maxLength={500}
                  showCount
                />

                <div style={{ marginTop: 16, textAlign: 'right' }}>
                  <Button
                    type="primary"
                    size="large"
                    icon={<SendOutlined />}
                    onClick={handleQuery}
                    loading={loading}
                  >
                    提问
                  </Button>
                </div>
              </div>

              <Divider />

              {/* 答案显示区域 */}
              <div>
                <h3>回答：</h3>
                {loading ? (
                  <div style={{ textAlign: 'center', padding: '40px 0' }}>
                    <Spin size="large" tip="正在思考中..." />
                  </div>
                ) : currentAnswer ? (
                  <div>
                    <Card
                      style={{
                        backgroundColor: '#f6ffed',
                        borderColor: '#b7eb8f',
                      }}
                    >
                      <div style={{ fontSize: 16, lineHeight: 1.8 }}>
                        {currentAnswer.answer}
                      </div>

                      <Divider />

                      <Row gutter={16}>
                        <Col span={8}>
                          <Statistic
                            title="响应时间"
                            value={currentAnswer.response_time}
                            suffix="ms"
                            prefix={<ClockCircleOutlined />}
                          />
                        </Col>
                        {currentAnswer.confidence_score !== undefined && (
                          <Col span={8}>
                            <Statistic
                              title="置信度"
                              value={currentAnswer.confidence_score}
                              precision={2}
                              suffix="%"
                              prefix={<CheckCircleOutlined />}
                            />
                          </Col>
                        )}
                        <Col span={8}>
                          <div style={{ marginTop: 8 }}>
                            <div style={{ color: '#666', fontSize: 14 }}>
                              检索模式
                            </div>
                            <Tag color={currentAnswer.use_rag ? 'green' : 'blue'}>
                              {currentAnswer.use_rag ? 'RAG增强' : '直接回答'}
                            </Tag>
                          </div>
                        </Col>
                      </Row>

                      {currentAnswer.retrieved_docs && currentAnswer.retrieved_docs.length > 0 && (
                        <>
                          <Divider />
                          <div>
                            <h4>参考文档：</h4>
                            <List
                              size="small"
                              dataSource={currentAnswer.retrieved_docs}
                              renderItem={(doc: any, index: number) => (
                                <List.Item>
                                  <div>
                                    <Tag color="blue">#{index + 1}</Tag>
                                    {doc.content || doc.text}
                                    {doc.score && (
                                      <span style={{ color: '#666', marginLeft: 8 }}>
                                        (相关度: {(doc.score * 100).toFixed(1)}%)
                                      </span>
                                    )}
                                  </div>
                                </List.Item>
                              )}
                            />
                          </div>
                        </>
                      )}
                    </Card>
                  </div>
                ) : (
                  <Empty
                    description="请输入问题开始查询"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                )}
              </div>
            </Space>
          </Card>
        </Col>

        {/* 右侧：历史记录 */}
        <Col span={8}>
          <Card
            title={
              <Space>
                <HistoryOutlined />
                查询历史
              </Space>
            }
            extra={
              <Button size="small" onClick={fetchHistory}>
                刷新
              </Button>
            }
            style={{ minHeight: 600 }}
          >
            <List
              loading={historyLoading}
              dataSource={history}
              renderItem={(item) => (
                <List.Item
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setQuestion(item.question);
                    setCurrentAnswer({
                      answer: item.answer,
                      response_time: item.response_time,
                      confidence_score: item.confidence * 100, // 转换为百分比
                      use_rag: true, // 默认值，因为历史记录没有这个字段
                      question: item.question, // 添加问题字段
                    });
                  }}
                >
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
                      <div>
                        <div
                          style={{
                            fontSize: 12,
                            color: '#666',
                            marginTop: 4,
                            marginBottom: 4,
                          }}
                        >
                          <Tag color="green" style={{ marginRight: 4 }}>
                            A
                          </Tag>
                          {item.answer.length > 60
                            ? item.answer.substring(0, 60) + '...'
                            : item.answer}
                        </div>
                        <div style={{ fontSize: 11, color: '#999' }}>
                          <Space size="small">
                            <span>
                              {new Date(item.created_at).toLocaleString('zh-CN')}
                            </span>
                            {item.response_time && (
                              <span>{Math.round(item.response_time)}ms</span>
                            )}
                            <Tag color="green">RAG</Tag>
                          </Space>
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: '暂无查询历史' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default QAInterface;
