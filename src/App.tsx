import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RoleProtectedRoute } from './components/RoleProtectedRoute';
import { Layout } from './components/Layout';

import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Tenders } from './pages/Tenders';
import { DocumentUpload } from './pages/DocumentUpload';
import { AIMatching } from './pages/AIMatching';
import {
  TenderDetail, Profile, Analytics, Users,
  Organizations, Subscriptions, SupportView
} from './pages/Placeholders';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Navigate to="/login" replace />} />


          {/* Protected Routes Wrapper */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              {/* Common Routes */}
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/profile" element={<Profile />} />

              {/* USER / ADMIN1 specific */}
              <Route path="/tenders" element={
                <RoleProtectedRoute allowedRoles={['USER', 'ADMIN1']}>
                  <Tenders />
                </RoleProtectedRoute>
              } />

              <Route path="/tenders/:id" element={
                <RoleProtectedRoute allowedRoles={['USER', 'ADMIN1']}>
                  <TenderDetail />
                </RoleProtectedRoute>
              } />

              <Route path="/upload" element={
                <RoleProtectedRoute allowedRoles={['USER', 'ADMIN1']}>
                  <DocumentUpload />
                </RoleProtectedRoute>
              } />

              <Route path="/match" element={
                <RoleProtectedRoute allowedRoles={['USER', 'ADMIN1']}>
                  <AIMatching />
                </RoleProtectedRoute>
              } />

              {/* ADMIN1 specific */}
              <Route path="/analytics" element={
                <RoleProtectedRoute allowedRoles={['ADMIN1']}>
                  <Analytics />
                </RoleProtectedRoute>
              } />

              <Route path="/users" element={
                <RoleProtectedRoute allowedRoles={['ADMIN1']}>
                  <Users />
                </RoleProtectedRoute>
              } />

              {/* SUPERADMIN specific */}
              <Route path="/admin/organizations" element={
                <RoleProtectedRoute allowedRoles={['SUPERADMIN']}>
                  <Organizations />
                </RoleProtectedRoute>
              } />

              <Route path="/admin/subscriptions" element={
                <RoleProtectedRoute allowedRoles={['SUPERADMIN']}>
                  <Subscriptions />
                </RoleProtectedRoute>
              } />

              {/* CUSTOMER_SUPPORT specific */}
              <Route path="/support/view/:orgId" element={
                <RoleProtectedRoute allowedRoles={['CUSTOMER_SUPPORT']}>
                  <SupportView />
                </RoleProtectedRoute>
              } />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
