import { type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

const TABS = [
  { path: '/', label: '🥚 Бестиарий' },
  { path: '/cave', label: '💎 Пещера' },
  { path: '/library', label: '📖 Библиотека' },
  { path: '/nest', label: '🐉 Гнездо' },
  { path: '/shop', label: '🛒 Лавка' },
];

function MiniAppShell({ children }: Props) {
  const nav = useNavigate();
  const loc = useLocation();
  const active = TABS.find((t) => t.path === loc.pathname)?.path
    ?? (loc.pathname.startsWith('/dragon') ? '/' : loc.pathname);

  return (
    <>
      <div style={{ display: 'flex', gap: 6, padding: '8px 8px 0', position: 'sticky', top: 0, zIndex: 20, background: 'var(--coal, #150f1a)' }}>
        {TABS.map((t) => (
          <button
            key={t.path}
            onClick={() => nav(t.path)}
            className={active === t.path ? 'lair-btn' : 'lair-btn lair-btn-outline'}
            style={{ flex: 1, padding: '8px 2px', fontSize: 12, whiteSpace: 'nowrap' }}
          >
            {t.label}
          </button>
        ))}
      </div>
      {children}
    </>
  );
}

export default MiniAppShell;
