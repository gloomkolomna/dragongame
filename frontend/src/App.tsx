import { Routes, Route, Navigate } from 'react-router-dom';

import { VkBridgeProvider } from './context/VkBridgeContext';
import MiniAppShell from './components/MiniAppShell';
import CaveLayout from './components/CaveLayout';

import Login from './pages/Login';
import AdminLayout from './pages/AdminLayout';
import Collection from './pages/Collection';
import DragonDetail from './pages/DragonDetail';
import Nest from './pages/Nest';
import Treasures from './pages/Treasures';
import Library from './pages/Library';
import Shop from './pages/Shop';

import Dashboard from './pages/admin/Dashboard';
import FamiliesList from './pages/admin/FamiliesList';
import FamiliesForm from './pages/admin/FamiliesForm';
import DragonsList from './pages/admin/DragonsList';
import DragonForm from './pages/admin/DragonForm';
import TreasureForm from './pages/admin/TreasureForm';
import FamilyTreasureForm from './pages/admin/FamilyTreasureForm';
import TreasureCreate from './pages/admin/TreasureCreate';
import TreasuresList from './pages/admin/TreasuresList';
import StepsEditor from './pages/admin/StepsEditor';
import LegendEditor from './pages/admin/LegendEditor';
import GridEditor from './pages/admin/GridEditor';
import ShopList from './pages/admin/ShopList';
import ShopForm from './pages/admin/ShopForm';
import FinancePage from './pages/admin/FinancePage';
import EpicDragons from './pages/admin/EpicDragons';
import EpicSpeciesForm from './pages/admin/EpicSpeciesForm';
import EpicStageForm from './pages/admin/EpicStageForm';
import EpicStageEditor from './pages/admin/EpicStageEditor';
import EpicStagesList from './pages/admin/EpicStagesList';
import EpicActionEditor from './pages/admin/EpicActionEditor';
import EpicSubActionEditor from './pages/admin/EpicSubActionEditor';
import CharacterAxes from './pages/admin/CharacterAxes';
import UsersList from './pages/admin/UsersList';
import UserDragonProgress from './pages/admin/UserDragonProgress';
import LogsList from './pages/admin/LogsList';
import SuspiciousList from './pages/admin/SuspiciousList';
import IntroChaptersList from './pages/admin/IntroChaptersList';
import RewardConfigs from './pages/admin/RewardConfigs';
import ReservationsList from './pages/admin/ReservationsList';

import ProtectedRoute from './components/ProtectedRoute';

function App() {
  return (
    <VkBridgeProvider>
      <Routes>
        {/* Mini App — публичные страницы коллекции */}
        <Route
          path="/"
          element={
            <MiniAppShell>
              <Collection />
            </MiniAppShell>
          }
        />
        <Route
          path="/dragon/:id"
          element={
            <MiniAppShell>
              <DragonDetail />
            </MiniAppShell>
          }
        />

        {/* Пещера дракона — подразделы с CaveLayout */}
        <Route
          path="/cave/nest"
          element={
            <MiniAppShell>
              <CaveLayout>
                <Nest />
              </CaveLayout>
            </MiniAppShell>
          }
        />
        <Route
          path="/cave/treasures"
          element={
            <MiniAppShell>
              <CaveLayout>
                <Treasures />
              </CaveLayout>
            </MiniAppShell>
          }
        />
        <Route
          path="/cave/library"
          element={
            <MiniAppShell>
              <CaveLayout>
                <Library />
              </CaveLayout>
            </MiniAppShell>
          }
        />
        <Route
          path="/cave/shop"
          element={
            <MiniAppShell>
              <CaveLayout>
                <Shop />
              </CaveLayout>
            </MiniAppShell>
          }
        />

        {/* Redirects для старых путей */}
        <Route path="/cave" element={<Navigate to="/cave/nest" replace />} />
        <Route path="/nest" element={<Navigate to="/cave/nest" replace />} />
        <Route path="/library" element={<Navigate to="/cave/library" replace />} />
        <Route path="/shop" element={<Navigate to="/cave/shop" replace />} />

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
          <Route path="dragons/:id/legend" element={<LegendEditor />} />
          <Route path="dragons/:id/treasure" element={<TreasureForm />} />
          <Route path="families/:id/treasure" element={<FamilyTreasureForm />} />
          <Route path="treasures/new" element={<TreasureCreate />} />
          <Route path="treasures" element={<TreasuresList />} />
          <Route path="grid" element={<GridEditor />} />
          <Route path="shop" element={<ShopList />} />
          <Route path="shop/new" element={<ShopForm />} />
          <Route path="shop/:id/edit" element={<ShopForm />} />
          <Route path="finance" element={<FinancePage />} />
          <Route path="epic" element={<EpicDragons />} />
          <Route path="epic/species/new" element={<EpicSpeciesForm />} />
          <Route path="epic/species/:id/edit" element={<EpicSpeciesForm />} />
          <Route path="epic/species/:dragonId/stages" element={<EpicStagesList />} />
          <Route path="epic/species/:dragonId/stages/new" element={<EpicStageForm />} />
          <Route path="epic/stages/:stageId/edit" element={<EpicStageForm />} />
          <Route path="epic/stages/:stageId" element={<EpicStageEditor />} />
          <Route path="epic/stages/:stageId/actions/:actionId" element={<EpicActionEditor />} />
          <Route path="epic/stages/:stageId/actions/:actionId/sub-actions/:subId" element={<EpicSubActionEditor />} />
          <Route path="character-axes" element={<CharacterAxes />} />
          <Route path="users" element={<UsersList />} />
          <Route path="users/:vkId/dragons/:dragonId/progress" element={<UserDragonProgress />} />
          <Route path="suspicious" element={<SuspiciousList />} />
          <Route path="intro" element={<IntroChaptersList />} />
          <Route path="logs" element={<LogsList />} />
          <Route path="rewards" element={<RewardConfigs />} />
          <Route path="reservations" element={<ReservationsList />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </VkBridgeProvider>
  );
}

export default App;
