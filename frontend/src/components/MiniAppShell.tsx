import { type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

interface Props {
  children: ReactNode;
}

const TABS = [
  { path: '/', label: '🥚 Мой бестиарий' },
  { path: '/cave/nest', label: '🏔 Пещера дракона' },
];

function MiniAppShell({ children }: Props) {
  const nav = useNavigate();
  const loc = useLocation();
  const active = TABS.find((t) => t.path === loc.pathname)?.path
    ?? (loc.pathname.startsWith('/dragon') ? '/' : loc.pathname);

  return (
    <>
      <div style={{
        display: 'flex', gap: 6, padding: '8px 8px 0',
        paddingTop: 'calc(8px + var(--vk-inset-top, 0px))',
        position: 'sticky', top: 0, zIndex: 20, background: 'var(--coal, #150f1a)',
      }}>
        {TABS.map((t) => (
          <button
            key={t.path}
            onClick={() => nav(t.path)}
            className={active === t.path ? 'lair-btn' : 'lair-btn lair-btn-outline'}
            style={{
              flex: 1, minWidth: 0, padding: '8px 4px', fontSize: 12,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}
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
