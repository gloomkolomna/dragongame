import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import client from '../../api/client';

interface Cell { id: number; cell_x: number; cell_y: number; dragon_id: number | null; }
interface Dragon { id: number; name: string; rarity: number; family_id: number | null; egg_path: string; dragon_path: string; }
interface Family { id: number; name: string; }

function GridEditor() {
  const [families, setFamilies] = useState<Family[]>([]);
  const [familyId, setFamilyId] = useState<number | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [dragons, setDragons] = useState<Dragon[]>([]);
  const [initLoad, setInitLoad] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [cols, setCols] = useState(10);
  const [rows, setRows] = useState(5);
  const [modalImg, setModalImg] = useState<string | null>(null);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const fid = searchParams.get('family_id');
    if (fid) setFamilyId(Number(fid));
  }, [searchParams]);

  useEffect(() => { client.get('/admin/families').then((r) => setFamilies(r.data)); }, []);

  const fetchData = useCallback(async (isInit = false) => {
    if (!familyId) return;
    if (isInit) setInitLoad(true);
    try {
      if (!isInit) setUpdating(true);
      const [g, d] = await Promise.all([
        client.get('/admin/grid', { params: { family_id: familyId } }),
        client.get('/admin/dragons'),
      ]);
      const gridData: Cell[] = g.data;
      setCells(gridData);
      setDragons(d.data);
      if (gridData.length > 0) {
        setCols(Math.max(...gridData.map((c) => c.cell_x)) + 1);
        setRows(Math.max(...gridData.map((c) => c.cell_y)) + 1);
      }
    } catch (e) {
      console.error('Grid fetch error:', e);
    } finally {
      setInitLoad(false);
      setUpdating(false);
    }
  }, [familyId]);

  useEffect(() => { if (familyId) fetchData(true); }, [familyId, fetchData]);

  const resizeGrid = async (newCols: number, newRows: number) => {
    if (newCols < 1 || newRows < 1 || !familyId) return;
    try {
      await client.post('/admin/grid/resize', null, { params: { family_id: familyId, columns: newCols, rows: newRows } });
      await fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка изменения размера');
    }
  };
  const createGrid = async () => {
    if (!familyId) return;
    try {
      await client.post('/admin/grid/create', null, { params: { family_id: familyId, columns: cols, rows } });
      await fetchData();
    } catch (e) {
      console.error('Grid create error:', e);
    }
  };

  const assignDragon = useCallback(async (cellId: number, dragonId: number | null) => {
    try {
      if (dragonId === null) {
        await client.delete(`/admin/grid/cell/${cellId}`);
      } else {
        await client.put(`/admin/grid/cell/${cellId}`, null, { params: { dragon_id: dragonId } });
      }
      await fetchData();
    } catch (e) {
      console.error('Assign error:', e);
    }
  }, [fetchData]);

  const assignedIds = new Set(cells.filter((c) => c.dragon_id).map((c) => c.dragon_id));
  const unassigned = dragons.filter((d) => !assignedIds.has(d.id) && (!familyId || d.family_id === familyId));

  if (!familyId) {
    return (
      <>
        <div className="lair-header"><h2>📐 Редактор сетки</h2></div>
        <div className="lair-content">
          <div className="lair-card" style={{ maxWidth: 400, margin: '0 auto', textAlign: 'center' }}>
            <p style={{ color: 'var(--parchment-dim)', marginBottom: 16 }}>Выберите семейство / союз для редактирования сетки</p>
            <select className="lair-select" value="" onChange={(e) => setFamilyId(Number(e.target.value))}>
              <option value="">— выбрать —</option>
              {families.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="lair-header">
        <h2>📐 Редактор сетки</h2>
        <select className="lair-select" style={{ width: 180, marginLeft: 12 }} value={familyId} onChange={(e) => setFamilyId(Number(e.target.value))}>
          {families.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
        </select>
        {cells.length > 0 && (
          <span style={{ marginLeft: 12, color: 'var(--parchment-faded)', fontSize: 12 }}>
            {cells.filter((c) => c.dragon_id).length} / {cells.length} ячеек
            {updating && <span style={{ marginLeft: 8, color: 'var(--gold)' }}>...</span>}
          </span>
        )}
      </div>
      <div className="lair-content">
        {cells.length === 0 ? (
          <div className="lair-card" style={{ textAlign: 'center', maxWidth: 400, margin: '0 auto' }}>
            <p style={{ color: 'var(--parchment-dim)', marginBottom: 20 }}>Сетка для «{families.find((f) => f.id === familyId)?.name}» ещё не создана</p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 16 }}>
              <div>
                <label className="lair-label">Колонок</label>
                <input className="lair-input" type="number" min={1} max={20} value={cols}
                       onChange={(e) => setCols(Math.max(1, Math.min(20, Number(e.target.value))))}
                       style={{ width: 80 }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', paddingTop: 18, color: 'var(--gold)', fontSize: 18, fontWeight: 'bold' }}>×</div>
              <div>
                <label className="lair-label">Строк</label>
                <input className="lair-input" type="number" min={1} max={20} value={rows}
                       onChange={(e) => setRows(Math.max(1, Math.min(20, Number(e.target.value))))}
                       style={{ width: 80 }} />
              </div>
            </div>
            <button className="lair-btn" onClick={createGrid}>
              Создать сетку {cols}×{rows} = {cols * rows} ячеек
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 16 }}>
            <div className="lair-card" style={{ width: 220, flexShrink: 0, maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <h4 style={{ color: 'var(--gold)', margin: 0, fontSize: 14 }}>Неразмещённые</h4>
                <span style={{ fontSize: 12, color: 'var(--parchment-faded)' }}>{unassigned.length}</span>
              </div>
              <div style={{ marginBottom: 12, padding: '8px 0', borderTop: '1px solid var(--bronze)', borderBottom: '1px solid var(--bronze)' }}>
                <div style={{ fontSize: 10, color: 'var(--parchment-faded)', marginBottom: 6, textAlign: 'center' }}>Размер сетки</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: 'var(--parchment-faded)', marginBottom: 2 }}>Колонок: {cols}</div>
                    <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => resizeGrid(cols - 1, rows)}>−</button>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => resizeGrid(cols + 1, rows)}>+</button>
                    </div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: 'var(--parchment-faded)', marginBottom: 2 }}>Строк: {rows}</div>
                    <div style={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => resizeGrid(cols, rows - 1)}>−</button>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => resizeGrid(cols, rows + 1)}>+</button>
                    </div>
                  </div>
                </div>
              </div>
              {unassigned.map((d) => (
                <div key={d.id} draggable onDragStart={(e) => e.dataTransfer.setData('dragonId', String(d.id))}
                     style={{ padding: '6px 8px', marginBottom: 4, cursor: 'grab',
                              background: 'rgba(30,20,42,0.6)', borderRadius: 8, fontSize: 13,
                              color: 'var(--parchment)', border: '1px solid var(--bronze)' }}>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{d.name}</div>
                  <div style={{ color: 'var(--gold)', fontSize: 11, marginBottom: 3 }}>{'⭐'.repeat(d.rarity)}</div>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {d.egg_path && (
                      <img src={`/dragons/api/static/images/${d.egg_path}`} alt="яйцо" onClick={() => setModalImg(`/dragons/api/static/images/${d.egg_path}`)}
                           style={{ width: 30, height: 30, objectFit: 'cover', borderRadius: 3, cursor: 'pointer' }}
                           onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    )}
                    {d.dragon_path && (
                      <img src={`/dragons/api/static/images/${d.dragon_path}`} alt="дракон" onClick={() => setModalImg(`/dragons/api/static/images/${d.dragon_path}`)}
                           style={{ width: 30, height: 30, objectFit: 'cover', borderRadius: 3, cursor: 'pointer' }}
                           onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    )}
                  </div>
                </div>
              ))}
              {unassigned.length === 0 && <p style={{ color: 'var(--parchment-faded)', fontSize: 12 }}>Все драконы размещены</p>}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 250px)`, gap: 3, justifyContent: 'start' }}>
                {cells.map((cell) => {
                  const dragon = dragons.find((d) => d.id === cell.dragon_id);
                  return (
                    <div key={cell.id} className={`lair-grid-cell ${dragon ? 'occupied' : ''}`}
                         style={{ width: 250, minHeight: dragon ? undefined : 80 }}
                         onDragOver={(e) => e.preventDefault()}
                         onDrop={(e) => { e.preventDefault(); const id = Number(e.dataTransfer.getData('dragonId')); if (id) assignDragon(cell.id, id); }}>
                      {dragon ? (
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, marginBottom: 1 }}>
                            <span style={{ fontWeight: 700, fontSize: 16, lineHeight: 1, cursor: 'pointer', color: 'var(--gold)' }}
                                  onClick={() => navigate(`/admin/dragons/${dragon.id}/edit`)}
                                  title="Редактировать дракона">
                              {dragon.name}
                            </span>
                            <span style={{ color: 'var(--gold)', fontSize: 12 }}>{'⭐'.repeat(dragon.rarity)}</span>
                          </div>
                          {dragon.egg_path && (
                            <img src={`/dragons/api/static/images/${dragon.egg_path}`} alt="яйцо" onClick={() => setModalImg(`/dragons/api/static/images/${dragon.egg_path}`)}
                                 style={{ width: '100%', height: 22, objectFit: 'cover', borderRadius: 2, marginBottom: 1, cursor: 'pointer' }}
                                 onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                          )}
                          {dragon.dragon_path && (
                            <img src={`/dragons/api/static/images/${dragon.dragon_path}`} alt="дракон" onClick={() => setModalImg(`/dragons/api/static/images/${dragon.dragon_path}`)}
                                 style={{ width: '100%', height: 250, objectFit: 'contain', borderRadius: 2, marginBottom: 1, cursor: 'pointer' }}
                                 onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                          )}
                          <button className="lair-btn lair-btn-sm lair-btn-danger"
                                  style={{ fontSize: 10, padding: '1px 0', lineHeight: 1 }}
                                  onClick={(e) => { e.stopPropagation(); assignDragon(cell.id, null); }}>✕</button>
                        </div>
                      ) : (
                        <select style={{ width: '100%', padding: '4px', fontSize: 10, background: 'rgba(21,15,26,0.8)', color: 'var(--parchment)', border: '1px solid var(--bronze)', borderRadius: 4, cursor: 'pointer' }}
                                value="" onChange={(e) => { const v = Number(e.target.value); if (v) assignDragon(cell.id, v); }}>
                          <option value="">+</option>
                          {unassigned.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                        </select>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
      {modalImg && (
        <div onClick={() => setModalImg(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={modalImg} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8, boxShadow: '0 0 60px rgba(153,102,255,0.3)' }} />
          <button onClick={() => setModalImg(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </>
  );
}

export default GridEditor;
