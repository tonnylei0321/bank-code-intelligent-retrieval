import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from 'antd';

import { useAppSelector } from './hooks/redux';
import LoginPage from './pages/LoginPage';
import DashboardLayout from './components/Layout/DashboardLayout';
import Dashboard from './pages/Dashboard';
import DataManagement from './pages/DataManagement';
import TrainingManagement from './pages/TrainingManagement';
import TrainingMonitor from './pages/TrainingMonitor';
import ModelManagement from './pages/ModelManagement';
import QAInterface from './pages/QAInterface';
import UserManagement from './pages/UserManagement';
import SystemSettings from './pages/SystemSettings';

import './App.css';

const { Content } = Layout;

function App() {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <DashboardLayout>
      <Content style={{ margin: '24px 16px', padding: 24, minHeight: 280 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/data" element={<DataManagement />} />
          <Route path="/training" element={<TrainingManagement />} />
          <Route path="/training-monitor" element={<TrainingMonitor />} />
          <Route path="/models" element={<ModelManagement />} />
          <Route path="/qa" element={<QAInterface />} />
          
          {/* 管理员专用路由 */}
          {user?.role === 'admin' && (
            <>
              <Route path="/users" element={<UserManagement />} />
              <Route path="/settings" element={<SystemSettings />} />
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