import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface Cell {
  x: number;
  y: number;
  dragon_id: number | null;
  status: string;
  progress_pct: number;
  completed_steps: number;
  steps_count: number;
  name?: string;
  egg_type?: string;
  egg_url?: string;
  dragon_url?: string;
  next_step_available_at?: string;
}

interface Family {
  id: number;
  name: string;
  description: string;
  color: string;
  image_path: string;
  total_dragons: number;
  collected: number;
}

const GAP = 4;

function Collection() {
  const { vkUserId, isDemo, loading: bl } = useVkBridge();
  const [families, setFamilies] = useState<Family[]>([]);
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | null>(null);
  const [grid, setGrid] = useState<Cell[]>([]);
  const [load, setLoad] = useState(true);
  const [error, setError] = useState('');
  const [gridWidth, setGridWidth] = useState(0);
  const [modalImg, setModalImg] = useState<string | null>(null);
  const gridWrapRef = useRef<HTMLDivElement>(null);
  const nav = useNavigate();

  useEffect(() => {
    if (bl) return;
    if (!vkUserId) { setLoad(false); return; }
    client.get(`/collection/${vkUserId}/families`)
      .then((r) => {
        setFamilies(r.data);
        if (r.data.length > 0) setSelectedFamilyId(r.data[0].id);
        setError('');
      })
      .catch(() => setError('Не удалось загрузить данные. Проверьте, запущен ли сервер.'))
      .finally(() => setLoad(false));
  }, [vkUserId, bl]);

  useEffect(() => {
    if (bl || !vkUserId || !selectedFamilyId) return;
    client.get(`/collection/${vkUserId}`, { params: { family_id: selectedFamilyId } })
      .then((r) => {
        setGrid(r.data.grid);
      });
  }, [vkUserId, selectedFamilyId, bl]);

  useLayoutEffect(() => {
    const measure = () => {
      if (gridWrapRef.current) setGridWidth(gridWrapRef.current.clientWidth);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [grid.length]);

  if (bl || load) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
      <div className="dragon-skeleton-card" style={{ width: 280, height: 280 }} />
    </div>
  );

  if (!vkUserId) return (
    <div style={{ maxWidth: 400, margin: '60px auto', textAlign: 'center' }}>
      <div className="lair-card" style={{ padding: 24 }}>
        <div style={{ fontSize: 40, marginBottom: 8 }}>🐉</div>
        <p style={{ color: 'var(--text-secondary)' }}>
          Откройте приложение через VK, чтобы увидеть свою коллекцию драконов.
        </p>
      </div>
    </div>
  );

  if (error) return (
    <div style={{ maxWidth: 400, margin: '60px auto', textAlign: 'center' }}>
      <div className="lair-card" style={{ padding: 24 }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>⚠</div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>{error}</p>
        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          Бэкенд: <code style={{ background: 'rgba(21,15,26,0.5)', padding: '2px 6px', borderRadius: 4 }}>http://127.0.0.1:8001/api/</code>
        </p>
      </div>
    </div>
  );

  const selectedFamily = families.find((f) => f.id === selectedFamilyId);
  const famColor = selectedFamily?.color || 'var(--accent-gold-light)';
  const familyGrid = grid;

  const mx = Math.max(...familyGrid.map((c) => c.x), -1) + 1;
  const my = Math.max(...familyGrid.map((c) => c.y), -1) + 1;
  const map: Record<string, Cell> = {};
  familyGrid.forEach((c) => { map[`${c.x},${c.y}`] = c; });
  const rows: Cell[][] = [];
  for (let y = 0; y < my; y++) {
    const r: Cell[] = [];
    for (let x = 0; x < mx; x++) {
      r.push(map[`${x},${y}`] || { x, y, dragon_id: null, status: 'locked', progress_pct: 0, completed_steps: 0, steps_count: 5 });
    }
    rows.push(r);
  }

  const available = gridWidth || 360;
  const fitByWidth = (available - (mx - 1) * GAP) / mx;
  const cellSize = Math.max(140, Math.min(200, fitByWidth));
  const gridTotalWidth = mx * cellSize + (mx - 1) * GAP;
  const gridNeedsScroll = gridTotalWidth > available + 1;

  const handleCellClick = (cell: Cell) => {
    if (cell.status !== 'locked' && cell.dragon_id) {
      nav(`/dragon/${cell.dragon_id}`);
    }
  };

  const renderCellContent = (c: Cell) => {
    if (c.status === 'completed') {
      if (c.dragon_url) {
        return (
          <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            <img src={mediaUrl(c.dragon_url)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              padding: '4px 6px', background: 'rgba(21,15,26,0.78)',
              fontSize: 18, color: famColor, textAlign: 'center',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
            }} title={c.name}>
              {c.name || '⭐'}
            </div>
          </div>
        );
      }
      return <span style={{ fontWeight: 700, color: famColor, fontSize: 18 }}>{c.name?.charAt(0) || '⭐'}</span>;
    }

    if (c.status === 'growing') {
      return (
        <div style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
          {c.egg_url ? (
            <img src={mediaUrl(c.egg_url)} alt="" style={{
              width: '100%', height: '100%', objectFit: 'cover', opacity: 0.85,
            }} />
          ) : (
            <span style={{ fontSize: cellSize * 0.5, opacity: 0.85, display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>🥚</span>
          )}
          {(() => {
            const hasTimeout = !!c.next_step_available_at && c.completed_steps > 0;
            const total = c.steps_count || 5;
            const prev_completed = hasTimeout ? Math.max(0, c.completed_steps - 1) : c.completed_steps;
            const prev_pct = Math.round((prev_completed / total) * 100);
            const extra_pct = hasTimeout ? Math.round((1 / total) * 100) : 0;

            return (
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0,
                padding: '4px 6px 4px',
                background: 'linear-gradient(rgba(21,15,26,0.85) 40%, transparent)',
              }}>
                <div style={{ position: 'relative' }}>
                  <div style={{ width: '100%', height: Math.max(6, cellSize * 0.07), background: 'rgba(21,15,26,0.55)', borderRadius: cellSize * 0.04, overflow: 'hidden', display: 'flex' }}>
                    <div style={{
                      height: '100%',
                      width: `${prev_pct}%`,
                      background: `linear-gradient(90deg, ${famColor}88, ${famColor})`,
                      borderRadius: `${cellSize * 0.04}px 0 0 ${cellSize * 0.04}px`,
                      transition: 'width 0.5s',
                      flexShrink: 0,
                    }} />
                    {hasTimeout && extra_pct > 0 && (
                      <div style={{
                        height: '100%',
                        width: `${extra_pct}%`,
                        background: `linear-gradient(90deg, ${famColor}88, ${famColor})`,
                        opacity: 0.3,
                        transition: 'width 0.5s',
                        flexShrink: 0,
                      }} />
                    )}
                  </div>
                  {hasTimeout && extra_pct > 0 && (
                    <div style={{
                      position: 'absolute',
                      left: `${prev_pct}%`,
                      width: `${extra_pct}%`,
                      top: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      pointerEvents: 'none',
                    }}>
                      <span className="hourglass-flip" style={{
                        fontSize: Math.max(8, cellSize * 0.065),
                        lineHeight: 1,
                        display: 'inline-block',
                      }}>
                        ⏳
                      </span>
                    </div>
                  )}
                  <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    pointerEvents: 'none',
                  }}>
                    <span style={{
                      fontSize: Math.max(12, cellSize * 0.12), color: famColor,
                      fontWeight: 700,
                      textShadow: '0 1px 3px rgba(0,0,0,0.7)',
                    }}>
                      {c.completed_steps}/{total}
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
          {c.egg_type && (
            <div style={{
              position: 'absolute', bottom: 0, left: 0, right: 0,
              padding: '4px 6px', background: 'rgba(21,15,26,0.78)',
              fontSize: 18, color: famColor, textAlign: 'center',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
            }} title={c.egg_type}>
              {c.egg_type}
            </div>
          )}
        </div>
      );
    }

    return <span style={{ color: 'var(--text-muted)', fontSize: cellSize * 0.4 }}>?</span>;
  };

  return (
    <div style={{ padding: '12px 8px' }}>
      {isDemo && (
        <div style={{
          marginBottom: 8, padding: 6, textAlign: 'center',
          background: 'rgba(153,102,255,0.1)', border: '1px solid rgba(153,102,255,0.3)',
          borderRadius: 8, fontSize: 12, color: 'var(--text-muted)',
        }}>
          ⚠ Демо-режим — данные для vk_id={vkUserId}
        </div>
      )}
      {families.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div
            id="family-tabs"            style={{
              display: 'flex', flexWrap: 'wrap', gap: 6, padding: '0 4px 8px',
            }}
          >
              {families.map((fam) => {
                const isActive = selectedFamilyId === fam.id;
                return (
              <button
                key={fam.id}
                onClick={() => setSelectedFamilyId(fam.id)}
                className={isActive ? 'lair-btn' : 'lair-btn lair-btn-outline'}
                style={{
                  padding: '8px 20px', fontSize: 15,
                  letterSpacing: 0.5, whiteSpace: 'nowrap',
                  ...(isActive && fam.color ? {
                    background: fam.color,
                    borderColor: fam.color,
                    color: '#fff',
                  } : {}),
                }}
              >
                {fam.name}
              </button>
                );
              })}
          </div>
        </div>
      )}

      <div className="lair-card" style={{
        marginBottom: 12, padding: '12px 20px', position: 'relative', overflow: 'hidden',
        background: selectedFamily?.color
          ? `linear-gradient(135deg, ${selectedFamily.color}33 0%, ${selectedFamily.color}11 100%)`
          : undefined,
        borderColor: selectedFamily?.color ? `${selectedFamily.color}66` : undefined,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {selectedFamily?.image_path && (
            <img src={mediaUrl(selectedFamily.image_path)} alt=""
                 onClick={(e) => { e.stopPropagation(); setModalImg(mediaUrl(selectedFamily.image_path)); }}
                 style={{ width: 52, height: 52, objectFit: 'contain', flexShrink: 0, cursor: 'pointer', borderRadius: 4 }} />
          )}
          <div>
            <div style={{ fontSize: 20, color: selectedFamily?.color || 'var(--accent-gold-light)', fontWeight: 600, marginBottom: 2 }}>
              {selectedFamily?.name || 'Коллекция'}
            </div>
            {selectedFamily?.description && (
              <div style={{ fontSize: 14, color: selectedFamily?.color || 'var(--parchment-dim)', lineHeight: 1.5 }}>
                {selectedFamily.description}
              </div>
            )}
          </div>
        </div>
      </div>

      {rows.length > 0 ? (
        <div style={{ position: 'relative' }}>
        <div ref={gridWrapRef} style={{
          width: '100%',
          overflowX: gridNeedsScroll ? 'auto' : 'hidden',
          WebkitOverflowScrolling: 'touch',
          paddingBottom: gridNeedsScroll ? 6 : 0,
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: GAP, alignItems: 'center', width: 'fit-content', minWidth: '100%' }}>
          {rows.map((r, ri) => (
            <div key={ri} style={{ display: 'flex', gap: GAP }}>
              {r.map((c) => (
                <div
                  key={`${c.x},${c.y}`}
                  onClick={() => handleCellClick(c)}
                  className="lair-grid-cell"
                  title={c.name || c.egg_type || ''}
                  style={{
                    width: cellSize, height: cellSize, padding: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    cursor: c.status !== 'locked' ? 'pointer' : 'default',
                    overflow: 'hidden',
                    background: c.status === 'completed' ? 'var(--success-bg)' :
                      c.status === 'growing' ? 'var(--warning-bg)' : 'var(--bg-card)',
                    borderColor: c.status === 'completed' ? 'rgba(58,138,101,0.4)' :
                      c.status === 'growing' ? 'rgba(201,138,42,0.4)' : undefined,
                  }}
                >
                  {renderCellContent(c)}
                </div>
              ))}
            </div>
          ))}
          </div>
        </div>
        {gridNeedsScroll && (
          <div style={{
            position: 'absolute', right: 0, top: 0, bottom: 0, width: 32,
            background: 'linear-gradient(90deg, transparent, var(--coal))',
            pointerEvents: 'none',
          }} />
        )}
        </div>
      ) : (
        <div className="lair-card" style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>🐉</div>
          <p style={{ color: 'var(--text-secondary)' }}>
            {families.length === 0
              ? 'Коллекция пока пуста'
              : 'Сетка для этого семейства ещё не создана'}
          </p>
        </div>
      )}

      {modalImg && (
        <div onClick={() => setModalImg(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={modalImg} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8, boxShadow: '0 0 60px rgba(153,102,255,0.3)' }} />
          <button onClick={() => setModalImg(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}

      <style>{`.dragon-skeleton-card{width:280px;height:280px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shim 1.5s infinite}@keyframes shim{0%,100%{opacity:.4}50%{opacity:.7}}.hourglass-flip{animation:hg 3s ease-in-out infinite}@keyframes hg{0%{transform:rotateY(0)}45%{transform:rotateY(0)}55%{transform:rotateY(180deg)}100%{transform:rotateY(180deg)}}`}</style>
    </div>
  );
}

export default Collection;
