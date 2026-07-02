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
  name?: string;
  egg_type?: string;    // тип яйца (показывается под растущим яйцом)
  egg_url?: string;     // картинка яйца (growing)
  dragon_url?: string;  // взрослый дракон (completed)
}

interface Family {
  id: number;
  name: string;
  total_dragons: number;
  collected: number;
}

function Collection() {
  const { vkUserId, isDemo, loading: bl } = useVkBridge();
  const [families, setFamilies] = useState<Family[]>([]);
  const [selectedFamilyId, setSelectedFamilyId] = useState<number | null>(null);
  const [grid, setGrid] = useState<Cell[]>([]);
  const [total, setTotal] = useState(0);
  const [collected, setCollected] = useState(0);
  const [load, setLoad] = useState(true);
  const [tabOverflow, setTabOverflow] = useState(false);
  const [error, setError] = useState('');
  const [gridWidth, setGridWidth] = useState(0);
  const gridWrapRef = useRef<HTMLDivElement>(null);
  const nav = useNavigate();

  useEffect(() => {
    if (bl || !vkUserId) return;
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
        setTotal(r.data.total_dragons);
        setCollected(r.data.total_collected);
      });
  }, [vkUserId, selectedFamilyId, bl]);

  useEffect(() => {
    const el = document.getElementById('family-tabs');
    if (el && el.scrollWidth > el.clientWidth) setTabOverflow(true);
  }, [families]);

  useLayoutEffect(() => {
    const measure = () => {
      if (gridWrapRef.current) setGridWidth(gridWrapRef.current.clientWidth);
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

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
  const familyGrid = grid;
  const familyTotal = selectedFamily?.total_dragons ?? total;
  const familyCollected = selectedFamily?.collected ?? collected;
  const growingCount = grid.filter((c) => c.status === 'growing').length;

  const mx = Math.max(...familyGrid.map((c) => c.x), -1) + 1;
  const my = Math.max(...familyGrid.map((c) => c.y), -1) + 1;
  const map: Record<string, Cell> = {};
  familyGrid.forEach((c) => { map[`${c.x},${c.y}`] = c; });
  const rows: Cell[][] = [];
  for (let y = 0; y < my; y++) {
    const r: Cell[] = [];
    for (let x = 0; x < mx; x++) {
      r.push(map[`${x},${y}`] || { x, y, dragon_id: null, status: 'locked', progress_pct: 0 });
    }
    rows.push(r);
  }

  // Адаптивный размер ячейки: вписываемся в ширину миниаппа,
  // но держим ячейки крупными. Если не влезает — разрешаем горизонтальный скролл.
  const GAP = 4;
  const available = gridWidth || 360;
  const fitByWidth = Math.floor((available + GAP) / (mx + GAP));
  const cellSize = Math.max(96, Math.min(150, fitByWidth));

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
              padding: '3px 4px', background: 'rgba(21,15,26,0.78)',
              fontSize: Math.max(11, cellSize * 0.1), color: 'var(--accent-gold-light)', textAlign: 'center',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600,
            }}>
              {c.name || '⭐'}
            </div>
          </div>
        );
      }
      return <span style={{ fontWeight: 700, color: 'var(--accent-gold-light)', fontSize: cellSize * 0.3 }}>{c.name?.charAt(0) || '⭐'}</span>;
    }

    if (c.status === 'growing') {
      return (
        <div style={{
          width: '100%', height: '100%', display: 'flex',
          flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          padding: Math.max(4, cellSize * 0.06), gap: cellSize * 0.03,
        }}>
          {c.egg_url ? (
            <img src={mediaUrl(c.egg_url)} alt="" style={{
              width: '60%', height: '52%', objectFit: 'contain',
              opacity: 0.85,
            }} />
          ) : (
            <span style={{ fontSize: cellSize * 0.42, opacity: 0.85 }}>🥚</span>
          )}
          {/* тип яйца — мелкий чёрный текст */}
          {c.egg_type && (
            <div style={{
              fontSize: Math.max(10, cellSize * 0.095), color: '#1a1a1a', textAlign: 'center',
              fontWeight: 600, lineHeight: 1.1,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              width: '100%',
            }}>
              {c.egg_type}
            </div>
          )}
          <div style={{ width: '86%' }}>
            <div style={{
              width: '100%', height: Math.max(5, cellSize * 0.06), background: 'rgba(21,15,26,0.55)',
              borderRadius: cellSize * 0.03, overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', width: `${c.progress_pct}%`,
                background: 'linear-gradient(90deg, var(--ember), var(--fire), var(--molten))',
                borderRadius: cellSize * 0.03, transition: 'width 0.5s',
              }} />
            </div>
            <div style={{ fontSize: Math.max(10, cellSize * 0.1), color: 'var(--accent-gold)', textAlign: 'center', marginTop: 2, fontWeight: 700 }}>
              {c.progress_pct}%
            </div>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '12px 8px' }}>
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
        <div style={{
          marginBottom: 12, position: 'relative',
        }}>
          <div
            id="family-tabs"
            style={{
              display: 'flex', gap: 6, overflowX: 'auto', padding: '0 4px 8px',
              scrollbarWidth: 'none', msOverflowStyle: 'none',
              WebkitOverflowScrolling: 'touch',
            }}
          >
            {families.map((fam) => (
              <button
                key={fam.id}
                onClick={() => setSelectedFamilyId(fam.id)}
                className={selectedFamilyId === fam.id ? 'lair-btn' : 'lair-btn lair-btn-outline'}
                style={{
                  flexShrink: 0, padding: '6px 16px', fontSize: 13,
                  letterSpacing: 0.5, whiteSpace: 'nowrap',
                }}
              >
                {fam.name}
              </button>
            ))}
          </div>
          {tabOverflow && (
            <div style={{
              position: 'absolute', right: 0, top: 0, bottom: 0, width: 32,
              background: 'linear-gradient(90deg, transparent, var(--coal))',
              pointerEvents: 'none',
            }} />
          )}
        </div>
      )}

      <div className="lair-card" style={{ textAlign: 'center', marginBottom: 12, padding: '12px 20px' }}>
        <div style={{ fontSize: 15, color: 'var(--accent-gold-light)' }}>
          {selectedFamily?.name || 'Коллекция'}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
          Собрано: {familyCollected} из {familyTotal}
          {growingCount > 0 && <span style={{ marginLeft: 8, color: 'var(--accent-gold)' }}>🌱 {growingCount} в процессе</span>}
        </div>
      </div>

      {rows.length > 0 ? (
        <div ref={gridWrapRef} style={{ width: '100%', overflowX: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none', WebkitOverflowScrolling: 'touch' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: GAP, alignItems: 'center', width: 'fit-content', minWidth: '100%' }}>
          {rows.map((r, ri) => (
            <div key={ri} style={{ display: 'flex', gap: GAP }}>
              {r.map((c) => (
                <div
                  key={`${c.x},${c.y}`}
                  onClick={() => handleCellClick(c)}
                  className="lair-grid-cell"
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

      <style>{`.dragon-skeleton-card{width:280px;height:280px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shim 1.5s infinite}@keyframes shim{0%,100%{opacity:.4}50%{opacity:.7}}`}</style>
    </div>
  );
}

export default Collection;
