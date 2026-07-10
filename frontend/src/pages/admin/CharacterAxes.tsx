import { useEffect, useState } from 'react';
import client from '../../api/client';

interface Axis {
  id: number;
  positive_label: string;
  negative_label: string;
  sort_order: number;
  is_active: boolean;
}

function CharacterAxes() {
  const [axes, setAxes] = useState<Axis[]>([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [newAxis, setNewAxis] = useState({ positive_label: '', negative_label: '' });
  const [editData, setEditData] = useState({ positive_label: '', negative_label: '', sort_order: 0, is_active: true });
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const load = () => {
    client.get('/admin/character-axes').then((r) => { setAxes(r.data); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  const nextOrder = (axes.length ? Math.max(...axes.map((a) => a.sort_order)) : 0) + 1;

  const create = async () => {
    if (!newAxis.positive_label.trim() || !newAxis.negative_label.trim()) return;
    await client.post('/admin/character-axes', { ...newAxis, is_active: true });
    setNewAxis({ positive_label: '', negative_label: '' });
    load();
  };

  const startEdit = (a: Axis) => {
    setEditId(a.id);
    setEditData({ positive_label: a.positive_label, negative_label: a.negative_label, sort_order: a.sort_order, is_active: a.is_active });
  };

  const saveEdit = async () => {
    if (!editId) return;
    await client.put(`/admin/character-axes/${editId}`, editData);
    setEditId(null);
    load();
  };

  const del = async (id: number) => {
    if (!confirm('Удалить ось?')) return;
    await client.delete(`/admin/character-axes/${id}`);
    load();
  };

  const persistOrder = async (list: Axis[]) => {
    await Promise.all(list.map((a, i) =>
      client.put(`/admin/character-axes/${a.id}`, { sort_order: i + 1 })
    ));
    load();
  };

  const onDrop = (targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) { setDragIdx(null); return; }
    const list = [...axes];
    const [moved] = list.splice(dragIdx, 1);
    list.splice(targetIdx, 0, moved);
    setAxes(list);
    setDragIdx(null);
    persistOrder(list);
  };

  if (loading) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>🎭 Черты характера</h2></div>
      <div className="lair-content">
        <div className="lair-card" style={{ maxWidth: 640, marginBottom: 24 }}>
          <h3 style={{ marginTop: 0 }}>Новая ось (порядок #{nextOrder})</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div className="lair-form-group" style={{ flex: 1, minWidth: 140 }}>
              <label className="lair-label">Положительная</label>
              <input className="lair-input" value={newAxis.positive_label} onChange={(e) => setNewAxis({ ...newAxis, positive_label: e.target.value })} placeholder="Добрый" />
            </div>
            <div className="lair-form-group" style={{ flex: 1, minWidth: 140 }}>
              <label className="lair-label">Отрицательная</label>
              <input className="lair-input" value={newAxis.negative_label} onChange={(e) => setNewAxis({ ...newAxis, negative_label: e.target.value })} placeholder="Злой" />
            </div>
            <button className="lair-btn" onClick={create}>➕ Добавить</button>
          </div>
        </div>

        {axes.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Нет осей характера.</p>}

        {axes.map((a, idx) => (
          <div key={a.id}
               draggable={editId === null}
               onDragStart={() => setDragIdx(idx)}
               onDragOver={(e) => e.preventDefault()}
               onDrop={() => onDrop(idx)}
               className="lair-card"
               style={{ maxWidth: 640, marginBottom: 12, opacity: dragIdx === idx ? 0.4 : 1, cursor: editId === null ? 'grab' : 'default' }}>
            {editId === a.id ? (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div className="lair-form-group" style={{ flex: 1, minWidth: 120 }}>
                  <label className="lair-label">Положительная</label>
                  <input className="lair-input" value={editData.positive_label} onChange={(e) => setEditData({ ...editData, positive_label: e.target.value })} />
                </div>
                <div className="lair-form-group" style={{ flex: 1, minWidth: 120 }}>
                  <label className="lair-label">Отрицательная</label>
                  <input className="lair-input" value={editData.negative_label} onChange={(e) => setEditData({ ...editData, negative_label: e.target.value })} />
                </div>
                <div className="lair-form-group">
                  <label className="lair-checkbox"><input type="checkbox" checked={editData.is_active} onChange={(e) => setEditData({ ...editData, is_active: e.target.checked })} /> Активна</label>
                </div>
                <button className="lair-btn" onClick={saveEdit}>💾</button>
                <button className="lair-btn lair-btn-outline" onClick={() => setEditId(null)}>Отмена</button>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--parchment-faded)', fontSize: 14 }} title="Перетащить для смены порядка">⠿ #{a.sort_order}</span>
                  <strong>{a.positive_label}</strong> ⇄ <strong>{a.negative_label}</strong>
                  {!a.is_active && <span className="lair-badge" style={{ marginLeft: 4 }}>неактивна</span>}
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => startEdit(a)}>✏️</button>
                  <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => del(a.id)} style={{ color: '#d474a0' }}>🗑</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export default CharacterAxes;
