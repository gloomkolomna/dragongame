import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

const PRESET_COLORS = [
  '#e81416', '#ff4500', '#ff7f2a', '#ffa500', '#ffb830',
  '#ffe135', '#ccff00', '#8bc34a', '#32cd32', '#228b22',
  '#00ced1', '#00bcd4', '#03a9f4', '#2196f3', '#1e90ff',
  '#4169e1', '#6a5acd', '#7b68ee', '#9b6fc7', '#9966ff',
  '#b366ff', '#cc66ff', '#da70d6', '#ff69b4', '#ff1493',
  '#e91e63', '#f44336', '#c94a4a', '#8b2f2f', '#795548',
  '#8d6e63', '#a1887f', '#9e9e9e', '#78909c', '#607d8b',
];

function FamiliesForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const nav = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sortOrder, setSortOrder] = useState(0);
  const [color, setColor] = useState('#9b6fc7');
  const [load, setLoad] = useState(isEdit);

  useEffect(() => {
    if (!isEdit) return;
    client.get('/admin/families').then((r) => {
      const f = r.data.find((x: any) => x.id === Number(id));
      if (f) { setName(f.name); setDescription(f.description); setSortOrder(f.sort_order); setColor(f.color || '#9b6fc7'); }
    }).finally(() => setLoad(false));
  }, [id]);

  const save = async () => {
    if (!name.trim()) { setError('Название обязательно'); return; }
    setSaving(true); setError('');
    try {
      const body = { name, description, sort_order: sortOrder, color };
      if (isEdit) {
        await client.put(`/admin/families/${id}`, body);
      } else {
        await client.post('/admin/families', body);
      }
      nav('/admin/families');
    } catch (e: any) { setError(e?.response?.data?.detail || 'Ошибка'); }
    finally { setSaving(false); }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>{isEdit ? 'Редактировать' : 'Новое'} семейство / союз</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ maxWidth: 520 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Название</label>
            <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Огненные" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Краткое описание семейства / союза" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Цвет</label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
              <label style={{ position: 'relative', cursor: 'pointer', width: 44, height: 44, borderRadius: 10, background: color, border: '2px solid var(--bronze)', flexShrink: 0, overflow: 'hidden' }}>
                <input type="color" value={color} onChange={(e) => setColor(e.target.value)}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0, cursor: 'pointer' }} />
              </label>
              <input className="lair-input" value={color} onChange={(e) => setColor(e.target.value)} style={{ width: 110, fontSize: 16, fontFamily: 'var(--font-mono)' }} placeholder="#9b6fc7" />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {PRESET_COLORS.map((c) => (
                <div key={c}
                     onClick={() => setColor(c)}
                     style={{
                       width: 24, height: 24, borderRadius: 5, background: c, cursor: 'pointer',
                       border: color === c ? '3px solid var(--gold)' : '2px solid var(--bronze)',
                       transition: 'border 0.15s',
                     }}
                     title={c} />
              ))}
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Порядок</label>
            <input className="lair-input" type="text" inputMode="numeric" value={sortOrder} onChange={(e) => setSortOrder(Number(e.target.value))} style={{ width: 100 }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : 'Сохранить'}</button>
            <button className="lair-btn lair-btn-outline" onClick={() => nav('/admin/families')}>Отмена</button>
          </div>
        </div>
      </div>
    </>
  );
}

export default FamiliesForm;
