import { type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

const CAVE_TABS = [
  { path: '/cave/nest', label: '🥚 Гнездо' },
  { path: '/cave/treasures', label: '💎 Сокровища' },
  { path: '/cave/library', label: '📖 Библиотека' },
  { path: '/cave/shop', label: '🛒 Лавка' },
];

function CaveLayout({ children }: Props) {
  const nav = useNavigate();
  const loc = useLocation();

  return (
    <>
      <div style={{
        display: 'flex', gap: 4, padding: '4px 8px 0',
        position: 'sticky', top: 44, zIndex: 19,
        background: 'var(--coal, #150f1a)',
      }}>
        {CAVE_TABS.map((t) => {
          const isActive = loc.pathname === t.path;
          return (
            <button
              key={t.path}
              onClick={() => nav(t.path)}
              className={isActive ? 'lair-btn' : 'lair-btn lair-btn-outline'}
              style={{ flex: 1, padding: '6px 2px', fontSize: 11, whiteSpace: 'nowrap' }}
            >
              {t.label}
            </button>
          );
        })}
      </div>
      {children}
    </>
  );
}

export default CaveLayout;
