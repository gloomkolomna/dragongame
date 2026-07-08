import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Fragment {
  id: number; step_number: number; task_description: string; magic_action: string; image_path: string;
  crosses_norm: number; timeout_hours: number; timeout_minutes: number;
}

function LegendEditor() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [dragonName, setDragonName] = useState('');
  const [cover, setCover] = useState('');
  const [fragments, setFragments] = useState<Fragment[]>([]);
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');
  const [zoom, setZoom] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      client.get(`/admin/dragons/${id}`),
      client.get(`/admin/dragons/${id}/legend`),
    ]).then(([d, l]) => {
      setDragonName(d.data.name);
      setCover(l.data.legend_image_path || '');
      setFragments(l.data.fragments || []);
    }).finally(() => setLoad(false));
  }, [id]);

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };

  const onCover = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setCover(await uploadImage(file));
  };
  const onFragImage = async (i: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const path = await uploadImage(file);
    setFragments((prev) => prev.map((f, idx) => idx === i ? { ...f, image_path: path } : f));
  };

  const addFrag = () => setFragments((p) => [...p, { id: 0, step_number: p.length + 1, task_description: '', magic_action: '', image_path: '', crosses_norm: 1000, timeout_hours: 0, timeout_minutes: 0 }]);
  const removeFrag = (i: number) => setFragments((p) => p.filter((_, idx) => idx !== i));
  const upd = (i: number, f: keyof Fragment, v: any) => setFragments((p) => p.map((frag, idx) => idx === i ? { ...frag, [f]: v } : frag));

  const save = async () => {
    setSaving(true); setMsg('');
    try {
      await client.put(`/admin/dragons/${id}/legend`, {
        legend_image_path: cover,
        fragments: fragments.map((f, i) => ({ ...f, step_number: i + 1 })),
      });
      setMsg('Сохранено');
    } catch (e: any) { setMsg(e.response?.data?.detail || 'Ошибка'); }
    finally { setSaving(false); }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav('/admin/dragons')}>← Назад</button>
        <h2 style={{ marginLeft: 12 }}>📜 Легенда: {dragonName}</h2>
      </div>
      <div className="lair-content">
        {msg && <div style={{ padding: '8px 12px', marginBottom: 12, borderRadius: 8, background: 'rgba(120,180,120,0.12)', color: '#8bc34a', fontSize: 13 }}>{msg}</div>}
        <div className="lair-card" style={{ maxWidth: 640 }}>
          <div className="lair-form-group">
            <label className="lair-label">Обложка легенды</label>
            <label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={onCover} />{cover ? 'Заменить...' : 'Выбрать файл...'}</label>
            {cover && <img src={`/dragons/api/static/images/${cover}?t=${Date.now()}`} alt="" onClick={() => setZoom(`/dragons/api/static/images/${cover}`)} style={{ maxWidth: 160, maxHeight: 160, marginTop: 8, borderRadius: 8, cursor: 'pointer' }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '8px 0 12px' }}>
            <label className="lair-label" style={{ marginBottom: 0 }}>Отрывки легенды ({fragments.length})</label>
            <button type="button" className="lair-btn lair-btn-sm" onClick={addFrag}>+ Отрывок</button>
          </div>

          {fragments.map((f, i) => (
            <div key={i} style={{ padding: '10px 12px', marginBottom: 8, background: 'rgba(30,20,42,0.4)', borderRadius: 8, border: '1px solid var(--bronze)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ color: 'var(--accent-gold-light)', fontWeight: 600 }}>Отрывок {i + 1}</span>
                <button type="button" className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => removeFrag(i)}>🗑</button>
              </div>
              <textarea className="lair-textarea" value={f.task_description} onChange={(e) => upd(i, 'task_description', e.target.value)} placeholder="Текст отрывка легенды" style={{ marginBottom: 6 }} />
              <textarea className="lair-textarea" value={f.magic_action} onChange={(e) => upd(i, 'magic_action', e.target.value)} placeholder="Задание (что нужно вышить)" style={{ marginBottom: 6 }} />
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <label className="lair-file" style={{ margin: 0 }}><input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => onFragImage(i, e)} />{f.image_path ? 'Заменить фото...' : 'Фото...'}</label>
                {f.image_path && (
                  <img src={`/dragons/api/static/images/${f.image_path}?t=${Date.now()}`} alt=""
                       onClick={() => setZoom(`/dragons/api/static/images/${f.image_path}`)}
                       style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                       onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                )}
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Норма:</span>
                <input className="lair-input" type="text" inputMode="numeric" value={f.crosses_norm} onChange={(e) => upd(i, 'crosses_norm', Math.max(1, parseInt(e.target.value, 10) || 1))} style={{ width: 80 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Таймаут:</span>
                <input className="lair-input" type="text" inputMode="numeric" value={f.timeout_hours} onChange={(e) => upd(i, 'timeout_hours', Math.max(0, parseInt(e.target.value, 10) || 0))} style={{ width: 60 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>ч</span>
                <input className="lair-input" type="text" inputMode="numeric" value={f.timeout_minutes} onChange={(e) => upd(i, 'timeout_minutes', Math.max(0, Math.min(59, parseInt(e.target.value, 10) || 0)))} style={{ width: 60 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>мин</span>
              </div>
            </div>
          ))}
          {fragments.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 14, textAlign: 'center', padding: 12 }}>Нажми «+ Отрывок» чтобы добавить части легенды</div>}

          <button className="lair-btn" disabled={saving} onClick={save} style={{ marginTop: 8 }}>{saving ? '...' : '💾 Сохранить легенду'}</button>
        </div>
      </div>
      {zoom && (
        <div onClick={() => setZoom(null)}
             style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          <img src={zoom} alt="" onClick={(e) => e.stopPropagation()}
               style={{ maxWidth: '90vw', maxHeight: '90vh', objectFit: 'contain', borderRadius: 8, boxShadow: '0 0 60px rgba(153,102,255,0.3)' }} />
          <button onClick={() => setZoom(null)}
                  style={{ position: 'absolute', top: 16, right: 16, background: 'none', border: 'none', color: '#fff', fontSize: 32, cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>
      )}
    </>
  );
}

export default LegendEditor;
