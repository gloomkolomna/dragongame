import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';

interface Cell { x: number; y: number; dragon_id: number | null; status: string; progress_pct: number; name?: string; image_url?: string; }

function Collection() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [grid, setGrid] = useState<Cell[]>([]);
  const [total, setTotal] = useState(0);
  const [collected, setCollected] = useState(0);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();

  useEffect(() => { if (bl || !vkUserId) return; client.get(`/collection/${vkUserId}`).then((r) => { setGrid(r.data.grid); setTotal(r.data.total_dragons); setCollected(r.data.total_collected); }).finally(() => setLoad(false)); }, [vkUserId, bl]);

  if (bl || load) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="dragon-skeleton-card" style={{ width: 280, height: 280 }} /></div>;

  const mx = Math.max(...grid.map((c) => c.x), 0) + 1;
  const my = Math.max(...grid.map((c) => c.y), 0) + 1;
  const map: Record<string, Cell> = {}; grid.forEach((c) => { map[`${c.x},${c.y}`] = c; });
  const rows: Cell[][] = [];
  for (let y = 0; y < my; y++) { const r: Cell[] = []; for (let x = 0; x < mx; x++) r.push(map[`${x},${y}`] || { x, y, dragon_id: null, status: 'locked', progress_pct: 0 }); rows.push(r); }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: '20px 12px' }}>
      <div className="lair-card" style={{ textAlign: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: '0 0 4px', color: 'var(--accent-gold-light)', fontSize: 20 }}>🐉 Моя коллекция</h1>
        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 14 }}>Собрано: {collected} из {total}</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {rows.map((r, ri) => (
          <div key={ri} style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
            {r.map((c) => (
              <div key={`${c.x},${c.y}`}
                   onClick={() => { if (c.status !== 'locked') nav(`/dragon/${c.dragon_id}`); }}
                   className="lair-grid-cell"
                   style={{
                     width: 56, height: 56, padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                     cursor: c.status !== 'locked' ? 'pointer' : 'default', overflow: 'hidden',
                     background: c.status === 'completed' ? 'var(--success-bg)' : c.status === 'growing' ? 'var(--warning-bg)' : 'var(--bg-card)',
                     borderColor: c.status === 'completed' ? 'rgba(58,138,101,0.4)' : c.status === 'growing' ? 'rgba(201,138,42,0.4)' : undefined,
                   }}>
                {c.status === 'completed' && c.image_url && <img src={c.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                {c.status === 'completed' && !c.image_url && <span style={{ fontWeight: 700, color: 'var(--accent-gold-light)' }}>{c.name?.charAt(0) || '⭐'}</span>}
                {c.status === 'growing' && <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-gold)' }}>{c.progress_pct}%</span>}
                {c.status === 'locked' && <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>?</span>}
              </div>
            ))}
          </div>
        ))}
      </div>
      <style>{`.dragon-skeleton-card{width:280px;height:280px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shim 1.5s infinite}@keyframes shim{0%,100%{opacity:.4}50%{opacity:.7}}`}</style>
    </div>
  );
}

export default Collection;
