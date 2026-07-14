import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import DragonLogo from '../components/DragonLogo';
import SaveToast from '../components/SaveToast';

const NAV_ITEMS = [
  { path: '/admin/dashboard', label: 'Дашборд', icon: '📊' },
  { path: '/admin/families', label: 'Семейства / Союзы', icon: '📂' },
  { path: '/admin/dragons', label: 'Драконы', icon: '🐲' },
  { path: '/admin/treasures', label: 'Сокровища', icon: '💎' },
  { path: '/admin/epic', label: 'Эпические драконы', icon: '🐲' },
  { path: '/admin/shop', label: 'Магазин', icon: '🛒' },
  { path: '/admin/character-axes', label: 'Черты характера', icon: '🎭' },
  { path: '/admin/finance', label: 'Финансы', icon: '💳' },
  { path: '/admin/grid', label: 'Сетка', icon: '📐' },
  { path: '/admin/users', label: 'Игроки', icon: '👥' },
  { path: '/admin/suspicious', label: 'Подозрительные', icon: '⚠' },
  { path: '/admin/intro', label: 'Вступительная история', icon: '📖' },
  { path: '/admin/logs', label: 'Логи', icon: '📋' },
];

function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  const handleNav = (path: string) => {
    navigate(path);
  };

  const sidebar = (
    <div className="lair-sidebar" style={{ width: 250, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '20px 16px', textAlign: 'center', borderBottom: '1px solid var(--bronze)' }}>
        <div style={{ marginBottom: 4, display: 'flex', justifyContent: 'center' }}>
          <DragonLogo width={72} height={72} />
        </div>
        <div style={{ fontFamily: 'var(--font-title)', fontSize: 16, fontWeight: 700, color: 'var(--gold)', letterSpacing: 1 }}>
          Гнездо Дракона
        </div>
      </div>

      <nav style={{ flex: 1, padding: '12px 0', overflowY: 'auto' }}>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.path}
            className={`lair-nav-item ${location.pathname.startsWith(item.path) ? 'active' : ''}`}
            onClick={() => handleNav(item.path)}
          >
            <span style={{ fontSize: 18 }}>{item.icon}</span>
            {item.label}
          </div>
        ))}
      </nav>

      <div style={{ padding: '14px 16px', borderTop: '1px solid var(--bronze)' }}>
        <div style={{ fontSize: 13, color: 'var(--parchment-faded)', marginBottom: 8, fontFamily: 'var(--font-body)' }}>
          {user?.vk_id || '—'}
        </div>
        <button className="lair-btn lair-btn-outline lair-btn-sm" style={{ width: '100%' }} onClick={logout}>
          Выйти
        </button>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {sidebarOpen && (
        <div className="lair-sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      <div className={`lair-sidebar-wrapper ${sidebarOpen ? 'open' : ''}`}>
        {sidebar}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <div className="lair-mobile-topbar">
          <button
            className="lair-hamburger"
            onClick={() => setSidebarOpen(true)}
            aria-label="Меню"
          >
            <span />
            <span />
            <span />
          </button>
          <span className="lair-mobile-topbar-title">Гнездо Дракона</span>
          <div className="lair-mobile-topbar-spacer" />
        </div>

        <div style={{ flex: 1 }}>
          <Outlet />
        </div>
      </div>

      <SaveToast />
    </div>
  );
}

export default AdminLayout;
