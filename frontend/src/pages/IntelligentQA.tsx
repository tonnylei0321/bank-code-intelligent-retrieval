/**
 * 智能问答页面 - 现代化设计，采用Bento Grid布局和F-Pattern设计
 * 
 * 设计原则：
 * - F-Pattern布局：核心功能位于顶部，详细信息位于下方
 * - Bento Grid：圆角网格布局，微妙边框
 * - 单色系进阶：白/深灰基调，Electric Blue强调色
 * - 渐进式披露：默认隐藏低频操作，悬浮显示详情
 * - 键盘快捷键：Alt + Q 快速提问，Alt + M 切换模式
 * 
 * 功能：
 * - 智能问答交互（支持多种AI模型）
 * - 传统问答（基于训练模型）
 * - 模式切换（智能模式 vs 传统模式）
 * - 模型选择和配置
 * - 检索策略选择（RAG vs Redis）
 * - 问答历史记录
 * - 统计信息展示
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Input,
  Select,
  Tag,
  Form,
  Switch,
  Table,
  Progress,
  Typography,
  List,
  message,
} from 'antd';
import {
  MessageOutlined,
  SendOutlined,
  RobotOutlined,
  HistoryOutlined,
  BarChartOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  ExperimentOutlined,
  ApiOutlined,
  MonitorOutlined,
  EyeOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { queryAPI, trainingAPI } from '../services/api';

const { TextArea } = Input;
const { Option } = Select;
const { Paragraph } = Typography;

interface Model {
  type: string;
  name: string;
  provider: string;
  status: string;
}

interface QAResult {
  question: string;
  answer: string;
  confidence: number;
  matched_banks: any[];
  suggestions: string[];
  analysis: any;
  retrieval_strategy: string;
  context_count: number;
  quality: string;
  model_used: string;
  response_time: number;
  timestamp: string;
  retrieved_docs?: any[];
  use_rag?: boolean;
  confidence_score?: number;
}

interface QAHistory {
  id: number;
  question: string;
  answer: string;
  confidence: number;
  response_time: number;
  created_at: string;
  model_used: string;
  strategy: string;
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

const IntelligentQA: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [currentModel, setCurrentModel] = useState('gpt-3.5-turbo');
  const [question, setQuestion] = useState('');
  const [qaResult, setQaResult] = useState<QAResult | null>(null);
  const [qaHistory, setQaHistory] = useState<QAHistory[]>([]);
  const [strategy, setStrategy] = useState('redis_only'); // 默认使用Redis
  const [useRAG, setUseRAG] = useState(false); // RAG检索增强开关
  const [askingQuestion, setAskingQuestion] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [form] = Form.useForm();
  
  // 新增：问答模式
  const [qaMode, setQaMode] = useState<'intelligent' | 'traditional'>('intelligent');
  const [availableModels, setAvailableModels] = useState<TrainingJob[]>([]);
  const [selectedModel, setSelectedModel] = useState<number | null>(null);
  const [modelsLoading, setModelsLoading] = useState(false);

  // 热门问题示例
  const popularQuestions = [
    { question: '中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？', category: '精确查询', mode: 'intelligent' },
    { question: '福州有哪些工商银行支行？', category: '地区查询', mode: 'intelligent' },
    { question: '102290002916是哪个银行？', category: '联行号查询', mode: 'intelligent' },
    { question: '什么是联行号？', category: '知识问答', mode: 'traditional' },
    { question: '中国银行的银行代码是什么？', category: '传统查询', mode: 'traditional' },
  ];

  // 获取智能问答可用模型
  const fetchModels = async () => {
    try {
      const response = await fetch('/api/intelligent-qa/models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      
      if (data.success) {
        setModels(data.data.available_models || []);
        setCurrentModel(data.data.current_model || 'gpt-3.5-turbo');
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  // 获取传统问答可用的训练模型
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

  // 智能问答提交
  const handleIntelligentQA = async (values: any) => {
    if (!values.question?.trim()) {
      message.warning('请输入问题');
      return;
    }

    setAskingQuestion(true);
    setQaResult(null);

    try {
      const response = await fetch('/api/intelligent-qa/ask', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: values.question,
          model_type: currentModel,
          retrieval_strategy: strategy,
        }),
      });
      const data = await response.json();
      
      if (data.success) {
        setQaResult(data.data);
        message.success('问答完成');
        fetchQAHistory(); // 刷新历史记录
      } else {
        message.error('问答失败: ' + (data.error_message || '未知错误'));
      }
    } catch (error) {
      console.error('问答失败:', error);
      message.error('问答失败');
    } finally {
      setAskingQuestion(false);
    }
  };

  // 传统问答提交
  const handleTraditionalQA = async (values: any) => {
    if (!values.question?.trim()) {
      message.warning('请输入问题');
      return;
    }

    if (!selectedModel) {
      message.warning('请选择一个训练好的模型');
      return;
    }

    setAskingQuestion(true);
    setQaResult(null);

    try {
      const startTime = Date.now();
      const response = await queryAPI.query({
        question: values.question.trim(),
        use_rag: useRAG,
        top_k: 5,
        model_id: selectedModel,
      });
      const endTime = Date.now();

      const result = {
        question: values.question,
        answer: response.data.answer,
        confidence: response.data.confidence_score ? response.data.confidence_score / 100 : 0,
        matched_banks: [],
        suggestions: [],
        analysis: null,
        retrieval_strategy: useRAG ? 'rag_only' : 'traditional',
        context_count: response.data.retrieved_docs?.length || 0,
        quality: 'good',
        model_used: 'traditional_model',
        response_time: (endTime - startTime) / 1000,
        timestamp: new Date().toISOString(),
        retrieved_docs: response.data.retrieved_docs,
        use_rag: useRAG,
        confidence_score: response.data.confidence_score,
      };

      setQaResult(result);
      message.success('问答完成');
      fetchQAHistory(); // 刷新历史记录
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '查询失败');
    } finally {
      setAskingQuestion(false);
    }
  };

  // 提交问题
  const handleAskQuestion = async (values: any) => {
    if (qaMode === 'intelligent') {
      await handleIntelligentQA(values);
    } else {
      await handleTraditionalQA(values);
    }
  };

  // 获取问答历史
  const fetchQAHistory = async () => {
    setHistoryLoading(true);
    try {
      if (qaMode === 'intelligent') {
        const response = await fetch('/api/intelligent-qa/history?limit=20', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        });
        const data = await response.json();
        
        if (data.success) {
          setQaHistory(data.data.history || []);
        }
      } else {
        const response = await queryAPI.getQueryHistory(20);
        const items = response.data?.items || [];
        const formattedHistory = items.map((item: any) => ({
          id: item.id,
          question: item.question,
          answer: item.answer,
          confidence: item.confidence || 0,
          response_time: item.response_time || 0,
          created_at: item.created_at,
          model_used: 'traditional_model',
          strategy: 'traditional',
        }));
        setQaHistory(formattedHistory);
      }
    } catch (error) {
      console.error('获取历史记录失败:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  // 使用热门问题
  const handlePopularQuestion = (popularQuestion: string, mode: 'intelligent' | 'traditional') => {
    setQuestion(popularQuestion);
    setQaMode(mode);
    form.setFieldsValue({ question: popularQuestion });
  };

  // 处理RAG开关变化
  const handleRAGToggle = (checked: boolean) => {
    setUseRAG(checked);
    // 根据开关状态设置检索策略
    if (checked) {
      setStrategy('rag_only'); // 勾选时使用RAG检索
    } else {
      setStrategy('redis_only'); // 关闭时使用Redis检索
    }
  };

  // 处理模式切换
  const handleModeChange = (mode: 'intelligent' | 'traditional') => {
    setQaMode(mode);
    setQaResult(null); // 清空之前的结果
    fetchQAHistory(); // 重新加载历史记录
  };

  // 键盘快捷键处理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.altKey) {
        switch (event.key.toLowerCase()) {
          case 'q':
            event.preventDefault();
            document.querySelector('textarea')?.focus();
            break;
          case 'm':
            event.preventDefault();
            setQaMode(qaMode === 'intelligent' ? 'traditional' : 'intelligent');
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [qaMode]);

  useEffect(() => {
    fetchModels();
    fetchAvailableModels();
    fetchQAHistory();
  }, []);

  useEffect(() => {
    fetchQAHistory();
  }, [qaMode]);

  // 历史记录表格列
  const historyColumns = [
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      ellipsis: true,
      width: '40%',
    },
    {
      title: '模型',
      dataIndex: 'model_used',
      key: 'model_used',
      width: 120,
      render: (model: string) => <Tag color="blue">{model}</Tag>,
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
      width: 100,
      render: (strategy: string) => <Tag color="green">{strategy}</Tag>,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 100,
      render: (confidence: number) => (
        <Progress 
          percent={Math.round(confidence * 100)} 
          size="small" 
          status={confidence > 0.8 ? 'success' : confidence > 0.6 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      width: 100,
      render: (time: number) => `${time.toFixed(2)}s`,
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
  ];

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'success';
      case 'good': return 'processing';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'default';
    }
  };

  const getQualityText = (quality: string) => {
    switch (quality) {
      case 'excellent': return '优秀';
      case 'good': return '良好';
      case 'fair': return '一般';
      case 'poor': return '较差';
      default: return '未知';
    }
  };

  return (
    <div className="minimalist-container">
      <div className="content-area">
        {/* 页面标题 - 极简设计 */}
        <div className="section-spacing">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="title-primary">智能问答</h1>
              <p className="subtitle">支持多种AI模型的智能问答系统，提供精准的银行业务咨询服务</p>
            </div>
            <div className="flex items-center space-x-4">
              {/* 问答模式切换 */}
              <div className="flex items-center space-x-2">
                <Button
                  className={`btn-${qaMode === 'intelligent' ? 'primary' : 'secondary'}-glass`}
                  onClick={() => handleModeChange('intelligent')}
                  icon={<ThunderboltOutlined />}
                >
                  智能模式
                </Button>
                <Button
                  className={`btn-${qaMode === 'traditional' ? 'primary' : 'secondary'}-glass`}
                  onClick={() => handleModeChange('traditional')}
                  icon={<ExperimentOutlined />}
                >
                  传统模式
                </Button>
              </div>
              <div className="tag-glass">Alt+M 切换</div>
            </div>
          </div>
        </div>

        {/* 核心指标 - Bento Grid 布局 */}
        <div className="bento-grid-4 section-spacing">
          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">当前模式</p>
                <p className="text-2xl font-bold text-gray-900">
                  {qaMode === 'intelligent' ? '智能模式' : '传统模式'}
                </p>
                <div className="flex items-center mt-3">
                  {qaMode === 'intelligent' ? (
                    <ThunderboltOutlined className="text-green-500 text-sm mr-2" />
                  ) : (
                    <ExperimentOutlined className="text-blue-500 text-sm mr-2" />
                  )}
                  <span className="text-sm text-gray-600 font-medium">
                    {qaMode === 'intelligent' ? '多模型AI推理' : '本地训练模型'}
                  </span>
                </div>
              </div>
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform ${
                qaMode === 'intelligent' 
                  ? 'bg-gradient-to-br from-green-500 to-green-600' 
                  : 'bg-gradient-to-br from-blue-500 to-blue-600'
              }`}>
                {qaMode === 'intelligent' ? (
                  <ThunderboltOutlined className="text-white text-2xl" />
                ) : (
                  <ExperimentOutlined className="text-white text-2xl" />
                )}
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">检索方式</p>
                <p className="text-2xl font-bold text-gray-900">
                  {useRAG ? 'RAG检索' : (qaMode === 'intelligent' ? 'Redis检索' : '直接回答')}
                </p>
                <div className="flex items-center mt-3">
                  <span className="text-sm text-gray-600 font-medium">
                    {useRAG ? '语义相似度检索' : qaMode === 'intelligent' ? '快速精确匹配' : '模型生成'}
                  </span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <RobotOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">历史问答</p>
                <p className="metric-primary">{qaHistory.length}</p>
                <div className="flex items-center mt-3">
                  <HistoryOutlined className="text-blue-500 text-sm mr-2" />
                  <span className="text-sm text-gray-600 font-medium">本次会话记录</span>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <MessageOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>

          <Card className="glass-card group hover:scale-105 transition-all duration-300">
            <div className="flex items-center justify-between">
              <div>
                <p className="metric-secondary mb-2">平均置信度</p>
                <p className="metric-primary">
                  {qaHistory.length > 0 
                    ? `${Math.round(qaHistory.reduce((sum, h) => sum + h.confidence, 0) / qaHistory.length * 100)}%`
                    : '0%'
                  }
                </p>
                <div className="mt-3">
                  <div className="progress-glass">
                    <div 
                      className="progress-bar" 
                      style={{ 
                        width: `${qaHistory.length > 0 
                          ? Math.round(qaHistory.reduce((sum, h) => sum + h.confidence, 0) / qaHistory.length * 100)
                          : 0
                        }%` 
                      }}
                    />
                  </div>
                </div>
              </div>
              <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                <BarChartOutlined className="text-white text-2xl" />
              </div>
            </div>
          </Card>
        </div>

        {/* 主要内容区域 - 两栏布局 */}
        <div className="bento-grid-2 gap-8">
          <div className="space-y-8">
            {/* 问答界面 */}
            <Card className="glass-card">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  {qaMode === 'intelligent' ? <ThunderboltOutlined className="text-2xl text-blue-500" /> : <ExperimentOutlined className="text-2xl text-blue-500" />}
                  <div>
                    <h3 className="title-secondary mb-0">
                      {qaMode === 'intelligent' ? '智能问答' : '传统问答'}
                    </h3>
                    <p className="metric-secondary">
                      {qaMode === 'intelligent' ? '多模型AI' : '训练模型'}
                    </p>
                  </div>
                </div>
                <div className="tag-primary">Alt+Q 快速聚焦</div>
              </div>
              
              {/* 模式说明 */}
              <div className="p-4 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50 mb-6">
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                    <InfoCircleOutlined className="text-white text-sm" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-1">
                      {qaMode === 'intelligent' ? '智能模式' : '传统模式'}
                    </h4>
                    <p className="text-sm text-blue-800">
                      {qaMode === 'intelligent' 
                        ? '使用多种AI模型（GPT、Claude等）进行智能问答，支持复杂推理和语义理解'
                        : '使用本地训练的模型进行问答，基于特定领域的训练数据'
                      }
                    </p>
                  </div>
                </div>
              </div>

              {/* 模型选择区域 */}
              {qaMode === 'intelligent' ? (
                <div className="p-4 bg-gray-50 bg-opacity-50 rounded-2xl border border-gray-200 border-opacity-50 mb-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-6">
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-700">AI模型:</span>
                        <Select
                          value={currentModel}
                          onChange={setCurrentModel}
                          className="w-40"
                          placeholder="选择模型"
                        >
                          <Option value="gpt-3.5-turbo">GPT-3.5</Option>
                          <Option value="gpt-4">GPT-4</Option>
                          <Option value="claude-3-sonnet">Claude-3</Option>
                          <Option value="local">本地模型</Option>
                        </Select>
                      </div>
                      <div className="w-px h-6 bg-gray-300"></div>
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-700">RAG检索增强:</span>
                        <Switch
                          checked={useRAG}
                          onChange={handleRAGToggle}
                          checkedChildren="RAG"
                          unCheckedChildren="Redis"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-gray-50 bg-opacity-50 rounded-2xl border border-gray-200 border-opacity-50 mb-6">
                  <div className="flex items-start space-x-3 mb-4">
                    <RobotOutlined className="text-blue-500 text-lg mt-1" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-900 mb-2">训练模型选择</h4>
                      <Select
                        className="w-full mb-4"
                        placeholder="选择训练好的模型"
                        value={selectedModel}
                        onChange={setSelectedModel}
                        loading={modelsLoading}
                        disabled={modelsLoading || availableModels.length === 0}
                      >
                        {availableModels.map((job) => (
                          <Select.Option key={job.id} value={job.id}>
                            <div className="flex items-center justify-between">
                              <div>
                                <div className="tag-primary">Job #{job.id}</div>
                                <span className="font-medium ml-2">{job.model_name}</span>
                                {job.train_loss && (
                                  <span className="text-gray-500 ml-2 text-xs">
                                    (Loss: {job.train_loss.toFixed(4)})
                                  </span>
                                )}
                              </div>
                              <span className="text-gray-400 text-xs">
                                {new Date(job.completed_at).toLocaleDateString('zh-CN')}
                              </span>
                            </div>
                          </Select.Option>
                        ))}
                      </Select>
                      <div className="flex items-center justify-between p-3 bg-white rounded-xl border border-gray-200">
                        <div className="flex items-center space-x-3">
                          <span className="font-medium text-gray-700">RAG检索增强:</span>
                          <Switch
                            checked={useRAG}
                            onChange={setUseRAG}
                            checkedChildren="开启"
                            unCheckedChildren="关闭"
                          />
                        </div>
                        <span className="text-sm text-gray-500">
                          {useRAG ? '将使用知识库检索增强回答' : '仅使用模型直接回答'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <Form form={form} onFinish={handleAskQuestion} layout="vertical">
                <Form.Item name="question" label={
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-gray-900">请输入您的问题</span>
                    <div className="tag-primary">Alt+Q</div>
                  </div>
                }>
                  <TextArea
                    rows={4}
                    placeholder={
                      qaMode === 'intelligent' 
                        ? "例如：中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？"
                        : "例如：中国银行的银行代码是什么？"
                    }
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    className="input-glass"
                  />
                </Form.Item>
                
                {/* 检索方式说明 */}
                <div className="p-3 bg-gray-50 bg-opacity-50 rounded-xl border border-gray-200 border-opacity-50 mb-6">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-600">当前检索方式:</span>
                    <div className={`tag-${useRAG ? 'success' : 'primary'}`}>
                      {useRAG ? 'RAG检索增强' : (qaMode === 'intelligent' ? 'Redis快速检索' : '模型直接回答')}
                    </div>
                    <span className="text-sm text-gray-500">
                      {useRAG 
                        ? '使用向量数据库进行语义相似度检索，适合复杂查询' 
                        : qaMode === 'intelligent'
                          ? '使用Redis缓存进行快速精确匹配，适合精确查询'
                          : '使用训练模型直接生成回答'
                      }
                    </span>
                  </div>
                </div>
                
                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SendOutlined />}
                    loading={askingQuestion}
                    size="large"
                    disabled={qaMode === 'traditional' && !selectedModel}
                    className="btn-primary-glass h-12 px-8 font-semibold"
                  >
                    {askingQuestion ? '思考中...' : '提问'}
                  </Button>
                </Form.Item>
              </Form>
            </Card>

            {/* 问答结果 */}
            {qaResult && (
              <Card className="glass-card">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
                      <RobotOutlined className="text-white text-lg" />
                    </div>
                    <div>
                      <h3 className="title-secondary mb-0">回答结果</h3>
                      <div className={`tag-${getQualityColor(qaResult.quality)}`}>
                        质量: {getQualityText(qaResult.quality)}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <div className="tag-primary">
                      置信度: {Math.round(qaResult.confidence * 100)}%
                    </div>
                    <div className="tag-warning">
                      {qaResult.response_time.toFixed(2)}s
                    </div>
                    <div className={`tag-${qaMode === 'intelligent' ? 'success' : 'primary'}`}>
                      {qaMode === 'intelligent' ? '智能模式' : '传统模式'}
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-blue-50 bg-opacity-50 rounded-2xl border border-blue-200 border-opacity-50 mb-6">
                  <div className="flex items-start space-x-4">
                    <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center flex-shrink-0 mt-1">
                      <RobotOutlined className="text-white text-lg" />
                    </div>
                    <div className="flex-1">
                      <Paragraph className="mb-0 text-gray-800 leading-relaxed whitespace-pre-wrap font-medium">
                        {qaResult.answer}
                      </Paragraph>
                    </div>
                  </div>
                </div>

                {qaResult.matched_banks && qaResult.matched_banks.length > 0 && (
                  <Card className="glass-card mb-6 border-green-200 bg-green-50 bg-opacity-30">
                    <h4 className="font-semibold text-green-800 mb-4 flex items-center">
                      <CheckCircleOutlined className="mr-2" />
                      匹配的银行信息
                    </h4>
                    <List
                      size="small"
                      dataSource={qaResult.matched_banks.slice(0, 3)}
                      renderItem={(bank: any) => (
                        <List.Item className="border-none py-3 hover:bg-green-50 hover:bg-opacity-50 rounded-xl transition-colors">
                          <List.Item.Meta
                            title={<span className="font-semibold text-gray-900">{bank.bank_name}</span>}
                            description={
                              <div className="flex flex-wrap gap-2 mt-2">
                                <div className="tag-glass bg-gray-100 px-3 py-1 rounded-lg text-xs font-mono">
                                  {bank.bank_code}
                                </div>
                                <div className="tag-success">匹配度: {Math.round(bank.match_score)}%</div>
                                <div className="tag-primary">{bank.source}</div>
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                )}

                {qaResult.retrieved_docs && qaResult.retrieved_docs.length > 0 && (
                  <Card className="glass-card mb-6 border-purple-200 bg-purple-50 bg-opacity-30">
                    <h4 className="font-semibold text-purple-800 mb-4 flex items-center">
                      <FileTextOutlined className="mr-2" />
                      参考文档
                    </h4>
                    <List
                      size="small"
                      dataSource={qaResult.retrieved_docs}
                      renderItem={(doc: any, index: number) => (
                        <List.Item className="border-none py-3 hover:bg-purple-50 hover:bg-opacity-50 rounded-xl transition-colors">
                          <div className="w-full">
                            <div className="flex items-start space-x-3">
                              <div className="tag-primary">#{index + 1}</div>
                              <div className="flex-1">
                                <p className="text-sm text-gray-700 mb-2 leading-relaxed">{doc.content || doc.text}</p>
                                {doc.score && (
                                  <span className="text-xs text-gray-500 font-medium">
                                    相关度: {(doc.score * 100).toFixed(1)}%
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  </Card>
                )}

                {qaResult.suggestions && qaResult.suggestions.length > 0 && (
                  <div className="p-4 bg-yellow-50 bg-opacity-50 rounded-2xl border border-yellow-200 border-opacity-50">
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-yellow-500 rounded-lg flex items-center justify-center flex-shrink-0">
                        <BulbOutlined className="text-white text-sm" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-yellow-900 mb-2">建议</h4>
                        <ul className="space-y-1">
                          {qaResult.suggestions.map((suggestion, index) => (
                            <li key={index} className="text-sm text-yellow-800">{suggestion}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            )}
          </div>

          {/* 侧边栏 */}
          <div className="space-y-8">
            {/* 热门问题 */}
            <Card className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-yellow-500 rounded-xl flex items-center justify-center">
                  <BulbOutlined className="text-white text-lg" />
                </div>
                <h3 className="title-secondary mb-0">热门问题</h3>
              </div>
              <List
                size="small"
                dataSource={popularQuestions}
                renderItem={(item) => (
                  <List.Item className="border-none py-3 hover:bg-gray-50 hover:bg-opacity-50 rounded-xl transition-colors cursor-pointer">
                    <div className="w-full">
                      <Button
                        type="text"
                        size="small"
                        onClick={() => handlePopularQuestion(item.question, item.mode)}
                        className="h-auto p-0 text-left text-gray-700 hover:text-blue-600 font-normal w-full text-left"
                        style={{ 
                          whiteSpace: 'normal',
                          wordBreak: 'break-all',
                          textAlign: 'left',
                        }}
                      >
                        {item.question}
                      </Button>
                      <div className="flex flex-wrap gap-2 mt-3">
                        <div className="tag-primary">{item.category}</div>
                        <div className={`tag-${item.mode === 'intelligent' ? 'success' : 'warning'}`}>
                          {item.mode === 'intelligent' ? '智能' : '传统'}
                        </div>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </Card>

            {/* 系统状态 */}
            <Card className="glass-card">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center">
                  <MonitorOutlined className="text-white text-lg" />
                </div>
                <h3 className="title-secondary mb-0">系统状态</h3>
              </div>
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-gray-50 bg-opacity-50 rounded-xl">
                  <div>
                    <p className="metric-secondary mb-1">当前模式</p>
                    <p className="text-lg font-bold" style={{ color: qaMode === 'intelligent' ? '#10b981' : '#3b82f6' }}>
                      {qaMode === 'intelligent' ? '智能模式' : '传统模式'}
                    </p>
                  </div>
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                    qaMode === 'intelligent' ? 'bg-green-100' : 'bg-blue-100'
                  }`}>
                    {qaMode === 'intelligent' ? (
                      <ThunderboltOutlined className="text-green-600 text-xl" />
                    ) : (
                      <ExperimentOutlined className="text-blue-600 text-xl" />
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 bg-opacity-50 rounded-xl">
                  <div>
                    <p className="metric-secondary mb-1">检索方式</p>
                    <p className="text-lg font-bold text-blue-600">
                      {useRAG ? 'RAG检索' : (qaMode === 'intelligent' ? 'Redis检索' : '直接回答')}
                    </p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                    <RobotOutlined className="text-blue-600 text-xl" />
                  </div>
                </div>

                {qaMode === 'intelligent' && (
                  <div className="flex items-center justify-between p-4 bg-gray-50 bg-opacity-50 rounded-xl">
                    <div>
                      <p className="metric-secondary mb-1">当前模型</p>
                      <p className="text-lg font-bold text-purple-600">{currentModel}</p>
                    </div>
                    <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                      <ApiOutlined className="text-purple-600 text-xl" />
                    </div>
                  </div>
                )}

                {qaMode === 'traditional' && selectedModel && (
                  <div className="flex items-center justify-between p-4 bg-gray-50 bg-opacity-50 rounded-xl">
                    <div>
                      <p className="metric-secondary mb-1">训练模型</p>
                      <p className="text-lg font-bold text-orange-600">
                        {availableModels.find(m => m.id === selectedModel)?.model_name || 'Unknown'}
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
                      <ExperimentOutlined className="text-orange-600 text-xl" />
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>

        {/* 问答历史 - 全宽度 */}
        <Card className="glass-card section-spacing">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center">
                <HistoryOutlined className="text-white text-lg" />
              </div>
              <div>
                <h3 className="title-secondary mb-0">问答历史</h3>
                <p className="metric-secondary">{qaHistory.length} 条记录</p>
              </div>
            </div>
            <Button 
              type="text" 
              size="small" 
              icon={<EyeOutlined />}
              className="btn-secondary-glass"
            >
              导出记录
            </Button>
          </div>
          
          <div className="table-glass">
            <Table
              columns={historyColumns}
              dataSource={qaHistory}
              loading={historyLoading}
              rowKey="id"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
              locale={{ emptyText: '暂无问答记录' }}
            />
          </div>
        </Card>
      </div>
    </div>
  );
};

export default IntelligentQA;