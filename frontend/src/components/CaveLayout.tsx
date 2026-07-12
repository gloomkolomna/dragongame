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
        position: 'sticky', top: 'calc(44px + var(--vk-inset-top, 0px))', zIndex: 19,
        background: 'var(--coal, #150f1a)',
      }}>
        {CAVE_TABS.map((t) => {
          const isActive = loc.pathname === t.path;
          return (
            <button
              key={t.path}
              onClick={() => nav(t.path)}
              className={isActive ? 'lair-btn' : 'lair-btn lair-btn-outline'}
              style={{
                flex: 1, minWidth: 0, padding: '6px 3px', fontSize: 11,
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                letterSpacing: 0, textTransform: 'none',
              }}
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
