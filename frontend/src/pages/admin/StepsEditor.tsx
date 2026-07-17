import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Step { id: number; dragon_id: number; step_number: number; magic_action: string; task_description: string; hint: string; timeout_hours: number; timeout_minutes: number; crosses_norm: number; image_path: string; }

function StepsEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dragonName, setDragonName] = useState('');
  const [zoom, setZoom] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      client.get(`/admin/dragons/${id}`),
      client.get(`/admin/dragons/${id}/steps`),
    ]).then(([d, s]) => {
      setDragonName(d.data.name || `#${id}`);
      setSteps(s.data);
    }).finally(() => setLoading(false));
  }, [id]);

  const upd = (i: number, f: keyof Step, v: string) => {
    setSteps((prev) => {
      const s = [...prev];
      if (f === 'timeout_hours' || f === 'timeout_minutes' || f === 'crosses_norm') {
        let val = v === '' ? (f === 'crosses_norm' ? 1000 : 0) : parseInt(v, 10) || 0;
        if (f === 'timeout_minutes') val = Math.max(0, Math.min(59, val));
        if (f === 'crosses_norm') val = Math.max(1, val);
        (s[i] as any)[f] = val;
      } else {
        (s[i] as any)[f] = v;
      }
      return s;
    });
  };

  const move = (i: number, d: -1 | 1) => {
    setSteps((prev) => {
      const n = i + d;
      if (n < 0 || n >= prev.length) return prev;
      const s = [...prev];
      [s[i], s[n]] = [s[n], s[i]];
      return s;
    });
  };

  const add = () => setSteps((prev) => [...prev, { id: 0, dragon_id: Number(id), step_number: prev.length + 1, magic_action: '', task_description: '', hint: '', timeout_hours: 0, timeout_minutes: 0, crosses_norm: 1000, image_path: '' }]);

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };

  const onFragImage = async (i: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const path = await uploadImage(file);
    setSteps((prev) => prev.map((s, idx) => idx === i ? { ...s, image_path: path } : s));
  };

  const remove = (i: number) => setSteps((prev) => prev.filter((_, idx) => idx !== i));

  const save = async () => {
    setSaving(true);
    try {
      await client.put(`/admin/dragons/${id}/steps`, {
        steps: steps.map((s, i) => ({ ...s, step_number: i + 1 })),
      });
      navigate('/admin/dragons');
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="lair-content"><div className="dragon-skeleton-card" style={{ height: 400 }} /></div>;

  return (
    <>
      <div className="lair-header">
        <h2>📝 Шаги: {dragonName}</h2>
        <span style={{ color: 'var(--text-muted)', fontSize: 14, marginLeft: 8 }}>{steps.length} шагов</span>
      </div>
      <div className="lair-content">
        {steps.map((s, i) => (
          <div key={i} className="lair-card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <strong style={{ color: 'var(--accent-gold-light)', fontSize: 16 }}>Шаг {i + 1}</strong>
              <div style={{ display: 'flex', gap: 4 }}>
                <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
                <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={i === steps.length - 1} onClick={() => move(i, 1)}>↓</button>
                <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => remove(i)}>🗑</button>
              </div>
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Магическое действие</label>
              <input className="lair-input" value={s.magic_action} onChange={(e) => upd(i, 'magic_action', e.target.value)} placeholder="Положи яйцо на снег" />
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Задание по вышивке</label>
              <textarea className="lair-textarea" value={s.task_description} onChange={(e) => upd(i, 'task_description', e.target.value)} placeholder="Вышей 300 стежков белыми/голубыми нитками" />
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Подсказка (опционально)</label>
              <input className="lair-input" value={s.hint} onChange={(e) => upd(i, 'hint', e.target.value)} placeholder="Подойдёт любой зимний сюжет" />
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Ожидание перед след. шагом</label>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input className="lair-input" type="text" inputMode="numeric" value={s.timeout_hours}
                       onChange={(e) => upd(i, 'timeout_hours', e.target.value)}
                       style={{ width: 80 }} placeholder="0" />
                <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>ч</span>
                <input className="lair-input" type="text" inputMode="numeric" value={s.timeout_minutes}
                       onChange={(e) => upd(i, 'timeout_minutes', e.target.value)}
                       style={{ width: 80 }} placeholder="0" />
                <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>мин</span>
                {s.timeout_hours === 0 && s.timeout_minutes === 0 && (
                  <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 4 }}>Без ожидания</span>
                )}
              </div>
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Норма стежков</label>
              <input className="lair-input" type="text" inputMode="numeric" value={s.crosses_norm}
                     onChange={(e) => upd(i, 'crosses_norm', e.target.value)}
                     style={{ width: 120 }} placeholder="1000" />
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Изображение шага (опционально)</label>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label className="lair-file" style={{ margin: 0 }}><input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => onFragImage(i, e)} />{s.image_path ? 'Заменить...' : 'Выбрать файл...'}</label>
                {s.image_path && (
                  <img src={`/dragons/api/static/images/${s.image_path}?t=${Date.now()}`} alt=""
                       onClick={() => setZoom(`/dragons/api/static/images/${s.image_path}`)}
                       style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                       onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                )}
              </div>
            </div>
          </div>
        ))}
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="lair-btn" onClick={add}>+ Добавить шаг</button>
          <button className="lair-btn" disabled={saving} onClick={save}>💾 Сохранить</button>
          <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/dragons')}>← К драконам</button>
        </div>
      </div>
      <style>{`.dragon-skeleton-card{height:400px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
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

export default StepsEditor;
