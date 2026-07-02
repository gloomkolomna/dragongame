import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

function FamiliesForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const nav = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [sortOrder, setSortOrder] = useState(0);
  const [load, setLoad] = useState(isEdit);

  useEffect(() => {
    if (!isEdit) return;
    client.get('/admin/families').then((r) => {
      const f = r.data.find((x: any) => x.id === Number(id));
      if (f) { setName(f.name); setDescription(f.description); setSortOrder(f.sort_order); }
    }).finally(() => setLoad(false));
  }, [id]);

  const save = async () => {
    if (!name.trim()) { setError('Название обязательно'); return; }
    setSaving(true); setError('');
    try {
      const body = { name, description, sort_order: sortOrder };
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
      <div className="lair-header"><h2>{isEdit ? 'Редактировать' : 'Новое'} семейство</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ maxWidth: 500 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Название</label>
            <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Огненные" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Краткое описание семейства" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Порядок</label>
            <input className="lair-input" type="number" value={sortOrder} onChange={(e) => setSortOrder(Number(e.target.value))} style={{ width: 100 }} />
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
