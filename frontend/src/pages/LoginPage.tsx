import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAppDispatch } from '../hooks/redux';
import { login } from '../store/slices/authSlice';

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const dispatch = useAppDispatch();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    try {
      await dispatch(login(values)).unwrap();
      message.success('登录成功');
    } catch (error: any) {
      message.error(error.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card className="login-form">
        <h1 className="login-title">企业级小模型训练平台</h1>
        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>
        <div style={{ textAlign: 'center', color: '#999', fontSize: '12px' }}>
          默认账号: admin / admin123
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;