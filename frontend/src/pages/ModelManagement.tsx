/**
 * 模型管理页面
 * 
 * 功能：
 * - 查看训练完成的模型（训练任务）
 * - 启动模型评估
 * - 查看评估结果
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Select,
  message,
  Space,
  Tag,
  Drawer,
  Descriptions,
  List,
} from 'antd';
import {
  EyeOutlined,
  ExperimentOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { trainingAPI, evaluationAPI, dataAPI } from '../services/api';

const ModelManagement: React.FC = () => {
  const [models, setModels] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [evalModalVisible, setEvalModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedModel, setSelectedModel] = useState<any>(null);
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [form] = Form.useForm();

  // 获取已完成的训练任务（作为模型列表）
  const fetchModels = async () => {
    setLoading(true);
    try {
      const response = await trainingAPI.getTrainingJobs();
      const jobs = response.data?.jobs || [];
      // 只显示已完成的训练任务
      setModels(jobs.filter((j: any) => j.status === 'completed'));
    } catch (error: any) {
      message.error('获取模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取数据集列表
  const fetchDatasets = async () => {
    try {
      const response = await dataAPI.getDatasets();
      setDatasets(response.data || []);
    } catch (error) {
      console.error('获取数据集失败');
    }
  };

  useEffect(() => {
    fetchModels();
    fetchDatasets();
  }, []);

  // 启动评估
  const handleStartEvaluation = async (values: any) => {
    try {
      await evaluationAPI.startEvaluation({
        training_job_id: selectedModel.id,
        ...values,
      });
      message.success('评估任务已启动');
      setEvalModalVisible(false);
      form.resetFields();
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '启动评估失败');
    }
  };

  // 查看模型详情
  const handleViewDetail = async (model: any) => {
    setSelectedModel(model);
    setDetailDrawerVisible(true);
    
    // 获取该模型的评估记录
    try {
      const response = await evaluationAPI.getEvaluationsByJob(model.id);
      setEvaluations(response.data?.evaluations || []);
    } catch (error) {
      console.error('获取评估记录失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '模型名称',
      dataIndex: 'model_name',
      key: 'model_name',
    },
    {
      title: '数据集ID',
      dataIndex: 'dataset_id',
      key: 'dataset_id',
      width: 100,
    },
    {
      title: '训练参数',
      key: 'params',
      render: (_: any, record: any) => (
        <Space direction="vertical" size="small">
          <span>LoRA Rank: {record.lora_rank}</span>
          <span>Epochs: {record.num_epochs}</span>
          <span>LR: {record.learning_rate}</span>
        </Space>
      ),
    },
    {
      title: '最终Loss',
      dataIndex: 'loss',
      key: 'loss',
      width: 100,
      render: (loss: number) => loss?.toFixed(4) || '-',
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => (
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
            icon={<ExperimentOutlined />}
            onClick={() => {
              setSelectedModel(record);
              setEvalModalVisible(true);
            }}
          >
            评估
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="模型管理"
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchModels}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={models}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 个模型`,
          }}
        />
      </Card>

      {/* 启动评估对话框 */}
      <Modal
        title="启动模型评估"
        open={evalModalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setEvalModalVisible(false);
          form.resetFields();
        }}
        okText="启动"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" onFinish={handleStartEvaluation}>
          <Form.Item
            name="evaluation_type"
            label="评估类型"
            rules={[{ required: true, message: '请选择评估类型' }]}
          >
            <Select placeholder="选择评估类型">
              <Select.Option value="accuracy">准确率评估</Select.Option>
              <Select.Option value="performance">性能评估</Select.Option>
              <Select.Option value="comprehensive">综合评估</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item name="test_dataset_id" label="测试数据集（可选）">
            <Select placeholder="选择测试数据集" allowClear>
              {datasets.map((ds) => (
                <Select.Option key={ds.id} value={ds.id}>
                  {ds.filename} (ID: {ds.id})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="模型详情"
        placement="right"
        width={600}
        onClose={() => setDetailDrawerVisible(false)}
        open={detailDrawerVisible}
      >
        {selectedModel && (
          <>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="模型ID">{selectedModel.id}</Descriptions.Item>
              <Descriptions.Item label="模型名称">
                {selectedModel.model_name}
              </Descriptions.Item>
              <Descriptions.Item label="数据集ID">
                {selectedModel.dataset_id}
              </Descriptions.Item>
              <Descriptions.Item label="LoRA Rank">
                {selectedModel.lora_rank}
              </Descriptions.Item>
              <Descriptions.Item label="学习率">
                {selectedModel.learning_rate}
              </Descriptions.Item>
              <Descriptions.Item label="训练轮数">
                {selectedModel.num_epochs}
              </Descriptions.Item>
              <Descriptions.Item label="批次大小">
                {selectedModel.batch_size}
              </Descriptions.Item>
              <Descriptions.Item label="最终Loss">
                {selectedModel.loss?.toFixed(4)}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {new Date(selectedModel.completed_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>

            <h3 style={{ marginTop: 24, marginBottom: 16 }}>评估记录</h3>
            {evaluations.length > 0 ? (
              <List
                dataSource={evaluations}
                renderItem={(item: any) => (
                  <List.Item>
                    <List.Item.Meta
                      title={
                        <Space>
                          <span>评估 #{item.id}</span>
                          <Tag color="blue">{item.evaluation_type}</Tag>
                          <Tag color={item.status === 'completed' ? 'success' : 'processing'}>
                            {item.status}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div>
                          {item.metrics && (
                            <div>
                              准确率: {(item.metrics.accuracy * 100).toFixed(2)}%
                            </div>
                          )}
                          <div style={{ fontSize: 12, color: '#999' }}>
                            {new Date(item.created_at).toLocaleString('zh-CN')}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <p style={{ color: '#999' }}>暂无评估记录</p>
            )}
          </>
        )}
      </Drawer>
    </div>
  );
};

export default ModelManagement;
