/**
 * 数据管理页面
 * 
 * 功能：
 * - 数据集列表展示
 * - 上传新数据集
 * - 查看数据集详情
 * - 预览数据内容
 * - 验证数据格式
 * - 查看统计信息
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Upload,
  Modal,
  Drawer,
  message,
  Space,
  Tag,
  Descriptions,
  Spin,
  Statistic,
  Row,
  Col,
  Progress,
  Switch,
  InputNumber,
  Form,
  Alert,
  Divider,
} from 'antd';
import {
  UploadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
  ReloadOutlined,
  DeleteOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { dataAPI } from '../services/api';

interface Dataset {
  id: number;
  filename: string;
  file_path: string;
  total_records: number;
  valid_records: number;
  invalid_records: number;
  status: string;
  created_at: string;
  updated_at: string;
}

interface DatasetStats {
  total_records: number;
  unique_bank_codes: number;
  unique_bank_names: number;
  data_quality_score: number;
}

const DataManagement: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [previewDrawerVisible, setPreviewDrawerVisible] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [datasetStats, setDatasetStats] = useState<DatasetStats | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  
  // 智能生成相关状态
  const [useSmartGeneration, setUseSmartGeneration] = useState(false);
  const [samplesPerBank, setSamplesPerBank] = useState(7);
  const [useLLM, setUseLLM] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationStatus, setGenerationStatus] = useState('');
  const [generating, setGenerating] = useState(false);

  // 获取数据集列表
  const fetchDatasets = async () => {
    setLoading(true);
    try {
      const response = await dataAPI.getDatasets();
      setDatasets(response.data || []);
    } catch (error: any) {
      message.error(error.response?.data?.error_message || '获取数据集列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  // 上传数据集
  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    // 获取文件对象
    const fileItem = fileList[0];
    const file = (fileItem.originFileObj || fileItem) as File;
    
    if (!file) {
      message.error('无法获取文件对象');
      return;
    }

    // 检查是否使用智能生成
    if (useSmartGeneration) {
      // 使用智能生成
      await handleSmartGeneration(file);
    } else {
      // 普通上传
      setUploading(true);
      try {
        await dataAPI.uploadDataset(file);
        message.success('数据集上传成功');
        setUploadModalVisible(false);
        setFileList([]);
        fetchDatasets();
      } catch (error: any) {
        message.error(error.response?.data?.error_message || '上传失败');
      } finally {
        setUploading(false);
      }
    }
  };

  // 智能生成训练数据
  const handleSmartGeneration = async (file: File) => {
    setGenerating(true);
    setGenerationProgress(0);
    setGenerationStatus('开始上传文件...');

    try {
      // 创建 FormData
      const formData = new FormData();
      formData.append('file', file);
      formData.append('samples_per_bank', samplesPerBank.toString());
      formData.append('use_llm', useLLM.toString());

      setGenerationStatus('正在生成训练样本...');
      setGenerationProgress(20);

      // 调用智能生成 API
      const response = await fetch('http://localhost:8000/api/v1/bank-data/upload-and-generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '生成失败');
      }

      const result = await response.json();
      
      setGenerationProgress(100);
      setGenerationStatus('生成完成！');

      // 显示成功信息
      Modal.success({
        title: '智能生成成功！',
        content: (
          <div>
            <p>✅ 成功处理 <strong>{result.total_banks?.toLocaleString()}</strong> 个银行</p>
            <p>✅ 生成 <strong>{result.total_samples?.toLocaleString()}</strong> 个训练样本</p>
            <p>✅ 每个银行平均 <strong>{result.samples_per_bank}</strong> 个问法</p>
            <p>✅ 数据集 ID: <strong>{result.dataset_id}</strong></p>
            <Divider />
            <p>现在可以使用这个数据集训练模型了！</p>
          </div>
        ),
        okText: '去训练',
        onOk: () => {
          // 跳转到训练页面
          window.location.href = '/training';
        },
      });

      setUploadModalVisible(false);
      setFileList([]);
      setUseSmartGeneration(false);
      fetchDatasets();

    } catch (error: any) {
      message.error(error.message || '智能生成失败');
      setGenerationStatus('生成失败');
    } finally {
      setGenerating(false);
      setGenerationProgress(0);
      setGenerationStatus('');
    }
  };

  // 查看数据集详情
  const handleViewDetail = async (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setDetailDrawerVisible(true);
    
    try {
      const response = await dataAPI.getDatasetStats(dataset.id);
      setDatasetStats(response.data);
    } catch (error: any) {
      message.error('获取统计信息失败');
    }
  };

  // 预览数据
  const handlePreview = async (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setPreviewDrawerVisible(true);
    
    try {
      const response = await dataAPI.previewDataset(dataset.id, 20);
      setPreviewData(response.data || []);
    } catch (error: any) {
      message.error('获取预览数据失败');
    }
  };

  // 验证数据集（带进度显示）
  const [validating, setValidating] = useState(false);
  const [validationProgress, setValidationProgress] = useState(0);
  const [validationStatus, setValidationStatus] = useState('');

  const handleValidate = async (dataset: Dataset) => {
    setValidating(true);
    setValidationProgress(0);
    setValidationStatus('开始验证数据集...');

    try {
      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setValidationProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 500);

      setValidationStatus('正在验证数据格式...');
      const response = await dataAPI.validateDataset(dataset.id);
      
      clearInterval(progressInterval);
      setValidationProgress(100);
      
      if (response.data.status === 'validated') {
        setValidationStatus('验证完成，正在生成问答对...');
        message.success(`数据集验证通过！有效记录: ${response.data.valid_records}/${response.data.total_records}`);
        
        // 等待QA生成完成（轮询检查）
        await pollQAGenerationStatus(dataset.id);
      } else {
        message.warning(`数据集验证失败: ${response.data.errors?.join(', ')}`);
      }
      
      fetchDatasets();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '验证失败');
    } finally {
      setValidating(false);
      setValidationProgress(0);
      setValidationStatus('');
    }
  };

  // 轮询QA生成状态
  const pollQAGenerationStatus = async (datasetId: number) => {
    return new Promise<void>((resolve) => {
      let attempts = 0;
      const maxAttempts = 60; // 最多轮询60次（约5分钟）
      
      const checkStatus = setInterval(async () => {
        attempts++;
        
        try {
          const response = await dataAPI.getDatasetStats(datasetId);
          const qaCount = response.data?.qa_pair_count || 0;
          
          if (qaCount > 0) {
            clearInterval(checkStatus);
            setValidationStatus('问答对生成完成！');
            message.success(`问答对生成完成！共生成 ${qaCount} 条问答对`);
            resolve();
          } else if (attempts >= maxAttempts) {
            clearInterval(checkStatus);
            setValidationStatus('问答对生成超时');
            message.warning('问答对生成可能需要更长时间，请稍后刷新查看');
            resolve();
          } else {
            setValidationStatus(`正在生成问答对... (${attempts * 5}秒)`);
          }
        } catch (error) {
          // 继续轮询
        }
      }, 5000); // 每5秒检查一次
    });
  };

  // 删除数据集
  const handleDelete = (dataset: Dataset) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除数据集 "${dataset.filename}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await dataAPI.deleteDataset(dataset.id);
          message.success('数据集已删除');
          fetchDatasets();
        } catch (error: any) {
          message.error(error.response?.data?.error_message || '删除失败');
        }
      },
    });
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '记录数',
      dataIndex: 'total_records',
      key: 'total_records',
      width: 120,
      render: (count: number, record: Dataset) => {
        if (record.status === 'validated' && record.valid_records > 0) {
          return `${record.valid_records.toLocaleString()} / ${count.toLocaleString()}`;
        }
        return count?.toLocaleString() || '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          uploaded: 'blue',
          validated: 'green',
          processing: 'orange',
          error: 'red',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: '已验证',
      dataIndex: 'status',
      key: 'validated',
      width: 100,
      render: (status: string) =>
        status === 'validated' || status === 'indexed' ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            是
          </Tag>
        ) : (
          <Tag>否</Tag>
        ),
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => {
        if (!time) return '-';
        try {
          const date = new Date(time);
          if (isNaN(date.getTime())) return '-';
          return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          });
        } catch (error) {
          return '-';
        }
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: any, record: Dataset) => (
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
            icon={<FileTextOutlined />}
            onClick={() => handlePreview(record)}
          >
            预览
          </Button>
          {record.status === 'uploaded' && (
            <Button
              type="link"
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleValidate(record)}
              loading={validating}
            >
              验证
            </Button>
          )}
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  // 预览数据的列定义
  const previewColumns = previewData.length > 0
    ? Object.keys(previewData[0]).map((key) => ({
        title: key,
        dataIndex: key,
        key: key,
        ellipsis: true,
      }))
    : [];

  return (
    <div>
      <Card
        title="数据管理"
        extra={
          <Space>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalVisible(true)}
            >
              上传数据集
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchDatasets}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={datasets}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      {/* 验证进度对话框 */}
      <Modal
        title="数据验证进度"
        open={validating}
        footer={null}
        closable={false}
        width={500}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 20, marginBottom: 20 }}>
            <Progress
              percent={validationProgress}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          <p style={{ fontSize: 16, color: '#666' }}>{validationStatus}</p>
        </div>
      </Modal>

      {/* 上传对话框 */}
      <Modal
        title={
          <Space>
            <UploadOutlined />
            {useSmartGeneration ? '智能生成训练数据' : '上传数据集'}
            {useSmartGeneration && <Tag color="blue" icon={<RobotOutlined />}>AI 增强</Tag>}
          </Space>
        }
        open={uploadModalVisible}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
          setUseSmartGeneration(false);
        }}
        confirmLoading={uploading || generating}
        okText={useSmartGeneration ? '开始生成' : '上传'}
        cancelText="取消"
        width={600}
      >
        <Upload
          fileList={fileList}
          beforeUpload={(file) => {
            // 检查文件类型
            const isCSV = file.name.endsWith('.csv');
            const isExcel = file.name.endsWith('.xlsx') || file.name.endsWith('.xls');
            const isUNL = file.name.endsWith('.unl');
            
            if (!isCSV && !isExcel && !isUNL) {
              message.error('只支持 CSV、Excel 和 .unl 文件');
              return false;
            }
            
            // .unl 文件自动启用智能生成
            if (isUNL) {
              setUseSmartGeneration(true);
              message.info('检测到 .unl 文件，已自动启用智能生成模式');
            }
            
            setFileList([file as any]);
            return false;
          }}
          onRemove={() => {
            setFileList([]);
          }}
          maxCount={1}
        >
          <Button icon={<UploadOutlined />}>选择文件</Button>
        </Upload>
        
        <p style={{ marginTop: 16, color: '#666' }}>
          支持的文件格式：CSV、Excel (.xlsx, .xls)、.unl
          <br />
          {useSmartGeneration ? (
            <span style={{ color: '#1890ff' }}>
              <ThunderboltOutlined /> .unl 文件将自动生成多样化训练样本
            </span>
          ) : (
            '文件应包含银行代码相关数据'
          )}
        </p>

        <Divider />

        {/* 智能生成选项 */}
        <Form layout="vertical">
          <Form.Item label={
            <Space>
              <RobotOutlined />
              <span>智能生成训练数据</span>
              <Tag color="blue">推荐</Tag>
            </Space>
          }>
            <Switch
              checked={useSmartGeneration}
              onChange={setUseSmartGeneration}
              checkedChildren="开启"
              unCheckedChildren="关闭"
            />
            <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              自动为每个银行生成多种自然语言问法，提升模型准确率
            </p>
          </Form.Item>

          {useSmartGeneration && (
            <>
              <Alert
                message="智能生成模式"
                description={
                  <div>
                    <p>✨ 系统将为每个银行自动生成多种问法：</p>
                    <ul style={{ marginLeft: 20, marginTop: 8 }}>
                      <li>完整名称：中国工商银行股份有限公司北京市分行</li>
                      <li>简称：工商银行北京市分行</li>
                      <li>口语化：北京工商银行、工行北京</li>
                      <li>地区组合：北京市工商银行</li>
                      <li>查询句式：工商银行北京的联行号</li>
                    </ul>
                    <p style={{ marginTop: 8, color: '#1890ff' }}>
                      <strong>预期效果：</strong>准确率从 68% 提升到 88%+
                    </p>
                  </div>
                }
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Form.Item 
                label="每个银行生成样本数"
                tooltip="建议 5-10 个，数量越多训练数据越丰富"
              >
                <InputNumber
                  min={3}
                  max={15}
                  value={samplesPerBank}
                  onChange={(value) => setSamplesPerBank(value || 7)}
                  style={{ width: '100%' }}
                  addonAfter="个样本"
                />
                <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  推荐值：7（平衡质量和数量）
                </p>
              </Form.Item>

              <Form.Item 
                label={
                  <Space>
                    <span>使用大模型增强</span>
                    <Tag color="orange">实验性</Tag>
                  </Space>
                }
                tooltip="使用大模型生成更自然的问法，但速度较慢且需要更多内存"
              >
                <Switch
                  checked={useLLM}
                  onChange={setUseLLM}
                  checkedChildren="开启"
                  unCheckedChildren="关闭"
                />
                <p style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                  {useLLM ? (
                    <span style={{ color: '#ff7a00' }}>
                      ⚠️ 需要加载大模型（~15GB），生成速度较慢
                    </span>
                  ) : (
                    <span style={{ color: '#52c41a' }}>
                      ✅ 使用规则生成（快速、稳定、推荐）
                    </span>
                  )}
                </p>
              </Form.Item>

              {/* 预估信息 */}
              <Alert
                message="预估信息"
                description={
                  <div>
                    <p>假设文件包含 <strong>10,000</strong> 个银行：</p>
                    <ul style={{ marginLeft: 20, marginTop: 8 }}>
                      <li>将生成约 <strong>{(10000 * samplesPerBank).toLocaleString()}</strong> 个训练样本</li>
                      <li>预计耗时：{useLLM ? '约 30-60 分钟' : '约 2-5 分钟'}</li>
                      <li>磁盘空间：约 {Math.ceil(10000 * samplesPerBank * 0.0001)} MB</li>
                    </ul>
                  </div>
                }
                type="success"
                showIcon
                style={{ marginTop: 16 }}
              />
            </>
          )}
        </Form>
      </Modal>

      {/* 生成进度对话框 */}
      <Modal
        title="智能生成进度"
        open={generating}
        footer={null}
        closable={false}
        width={500}
      >
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin size="large" tip="正在生成训练样本..." />
          <div style={{ marginTop: 20, marginBottom: 20 }}>
            <Progress
              percent={generationProgress}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>
          <p style={{ fontSize: 16, color: '#666' }}>{generationStatus}</p>
          <p style={{ fontSize: 12, color: '#999', marginTop: 16 }}>
            {useLLM ? '使用大模型生成中，请耐心等待...' : '使用规则生成，速度较快...'}
          </p>
        </div>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="数据集详情"
        placement="right"
        width={600}
        onClose={() => {
          setDetailDrawerVisible(false);
          setDatasetStats(null);
        }}
        open={detailDrawerVisible}
      >
        {selectedDataset && (
          <>
            <Descriptions column={1} bordered>
              <Descriptions.Item label="ID">{selectedDataset.id}</Descriptions.Item>
              <Descriptions.Item label="文件名">
                {selectedDataset.filename}
              </Descriptions.Item>
              <Descriptions.Item label="文件路径">
                {selectedDataset.file_path}
              </Descriptions.Item>
              <Descriptions.Item label="总记录数">
                {selectedDataset.total_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="有效记录">
                {selectedDataset.valid_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="无效记录">
                {selectedDataset.invalid_records?.toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color="blue">{selectedDataset.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="已验证">
                {selectedDataset.status === 'validated' || selectedDataset.status === 'indexed' ? '是' : '否'}
              </Descriptions.Item>
              <Descriptions.Item label="上传时间">
                {new Date(selectedDataset.created_at).toLocaleString('zh-CN', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </Descriptions.Item>
            </Descriptions>

            {datasetStats && (
              <>
                <h3 style={{ marginTop: 24, marginBottom: 16 }}>统计信息</h3>
                <Row gutter={16}>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="总记录数"
                        value={datasetStats.total_records}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="唯一银行代码"
                        value={datasetStats.unique_bank_codes}
                      />
                    </Card>
                  </Col>
                  <Col span={12} style={{ marginTop: 16 }}>
                    <Card>
                      <Statistic
                        title="唯一银行名称"
                        value={datasetStats.unique_bank_names}
                      />
                    </Card>
                  </Col>
                  <Col span={12} style={{ marginTop: 16 }}>
                    <Card>
                      <Statistic
                        title="数据质量分数"
                        value={datasetStats.data_quality_score}
                        precision={2}
                        suffix="/ 100"
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            )}
          </>
        )}
      </Drawer>

      {/* 预览抽屉 */}
      <Drawer
        title="数据预览"
        placement="right"
        width={800}
        onClose={() => {
          setPreviewDrawerVisible(false);
          setPreviewData([]);
        }}
        open={previewDrawerVisible}
      >
        {selectedDataset && (
          <>
            <p style={{ marginBottom: 16 }}>
              <strong>文件名：</strong>
              {selectedDataset.filename}
            </p>
            <Table
              columns={previewColumns}
              dataSource={previewData}
              rowKey={(record, index) => index?.toString() || '0'}
              pagination={false}
              scroll={{ x: 'max-content' }}
              size="small"
            />
            <p style={{ marginTop: 16, color: '#666' }}>
              显示前 {previewData.length} 条记录
            </p>
          </>
        )}
      </Drawer>
    </div>
  );
};

export default DataManagement;
