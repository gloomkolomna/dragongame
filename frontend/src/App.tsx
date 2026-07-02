import { Routes, Route, Navigate } from 'react-router-dom';

import { VkBridgeProvider } from './context/VkBridgeContext';

import Login from './pages/Login';
import AdminLayout from './pages/AdminLayout';
import Collection from './pages/Collection';
import DragonDetail from './pages/DragonDetail';

import Dashboard from './pages/admin/Dashboard';
import FamiliesList from './pages/admin/FamiliesList';
import FamiliesForm from './pages/admin/FamiliesForm';
import DragonsList from './pages/admin/DragonsList';
import DragonForm from './pages/admin/DragonForm';
import StepsEditor from './pages/admin/StepsEditor';
import GridEditor from './pages/admin/GridEditor';
import PinManager from './pages/admin/PinManager';
import UsersList from './pages/admin/UsersList';

import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <VkBridgeProvider>
      <Routes>
        {/* Mini App — публичные страницы коллекции */}
        <Route path="/" element={<Collection />} />
        <Route path="/dragon/:id" element={<DragonDetail />} />

        {/* Admin — защищённые страницы */}
        <Route path="/admin/login" element={<Login />} />
        <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="families" element={<FamiliesList />} />
          <Route path="families/new" element={<FamiliesForm />} />
          <Route path="families/:id/edit" element={<FamiliesForm />} />
          <Route path="dragons" element={<DragonsList />} />
          <Route path="dragons/new" element={<DragonForm />} />
          <Route path="dragons/:id/edit" element={<DragonForm />} />
          <Route path="dragons/:id/steps" element={<StepsEditor />} />
          <Route path="grid" element={<GridEditor />} />
          <Route path="pins" element={<PinManager />} />
          <Route path="users" element={<UsersList />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </VkBridgeProvider>
  );
}

export default App;
