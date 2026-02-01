import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout, Spin } from 'antd';

import { useAppSelector, useAppDispatch } from './hooks/redux';
import { validateToken } from './store/slices/authSlice';
import LoginPage from './pages/LoginPage';
import DashboardLayout from './components/Layout/DashboardLayout';
import Dashboard from './pages/Dashboard';
import DatasetManagement from './pages/DatasetManagement';
import SampleManagement from './pages/SampleManagementNew';
import TrainingCenter from './pages/TrainingCenter';
import TrainingManagement from './pages/TrainingManagement';
import TrainingMonitor from './pages/TrainingMonitor';
import ModelManagement from './pages/ModelManagement';
import IntelligentQA from './pages/IntelligentQA';
import UserManagement from './pages/UserManagement';
import PermissionManagement from './pages/PermissionManagement';
import SystemSettings from './pages/SystemSettings';
import RAGManagement from './pages/RAGManagement';
import RedisManagement from './pages/RedisManagement';
import TraceManagement from './pages/TraceManagement';
import LLMPromptManagement from './pages/LLMPromptManagement';

import './App.css';

const { Content } = Layout;

function App() {
  const dispatch = useAppDispatch();
  const { isAuthenticated, user, loading } = useAppSelector((state) => state.auth);

  useEffect(() => {
    // 应用启动时验证现有token
    const token = localStorage.getItem('access_token');
    if (token && !user) {
      dispatch(validateToken());
    }
  }, [dispatch, user]);

  // 如果正在验证token，显示加载状态
  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Spin size="large" tip="验证登录状态..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <DashboardLayout>
      <Content style={{ margin: '24px 16px', padding: 24, minHeight: 280 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/intelligent-qa" element={<IntelligentQA />} />
          <Route path="/dataset-management" element={<DatasetManagement />} />
          <Route path="/sample-management" element={<SampleManagement />} />
          <Route path="/llm-prompt-management" element={<LLMPromptManagement />} />
          <Route path="/training-center" element={<TrainingCenter />} />
          <Route path="/training" element={<TrainingManagement />} />
          <Route path="/training-monitor" element={<TrainingMonitor />} />
          <Route path="/models" element={<ModelManagement />} />
          
          {/* 管理员专用路由 */}
          {user?.role === 'admin' && (
            <>
              <Route path="/users" element={<UserManagement />} />
              <Route path="/permissions" element={<PermissionManagement />} />
              <Route path="/settings" element={<SystemSettings />} />
              <Route path="/rag" element={<RAGManagement />} />
              <Route path="/redis" element={<RedisManagement />} />
              <Route path="/trace" element={<TraceManagement />} />
            </>
          )}
          
          {/* 404 重定向 */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Content>
    </DashboardLayout>
  );
}

export default App;