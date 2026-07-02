import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface Step { id: number; dragon_id: number; step_number: number; magic_action: string; task_description: string; hint: string; }

function StepsEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dragonName, setDragonName] = useState('');

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
    const s = [...steps];
    (s[i] as any)[f] = v;
    setSteps(s);
  };

  const move = (i: number, d: -1 | 1) => {
    const n = i + d;
    if (n < 0 || n >= steps.length) return;
    const s = [...steps];
    [s[i], s[n]] = [s[n], s[i]];
    setSteps(s);
  };

  const add = () => setSteps([...steps, { id: 0, dragon_id: Number(id), step_number: steps.length + 1, magic_action: '', task_description: '', hint: '' }]);

  const remove = (i: number) => setSteps(steps.filter((_, idx) => idx !== i));

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
        <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>{steps.length} шагов</span>
      </div>
      <div className="lair-content">
        {steps.map((s, i) => (
          <div key={i} className="lair-card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <strong style={{ color: 'var(--accent-gold-light)', fontSize: 15 }}>Шаг {i + 1}</strong>
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
              <textarea className="lair-textarea" value={s.task_description} onChange={(e) => upd(i, 'task_description', e.target.value)} placeholder="Вышей 300 крестиков белыми/голубыми нитками" />
            </div>
            <div className="lair-form-group">
              <label className="lair-label">Подсказка (опционально)</label>
              <input className="lair-input" value={s.hint} onChange={(e) => upd(i, 'hint', e.target.value)} placeholder="Подойдёт любой зимний сюжет" />
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
    </>
  );
}

export default StepsEditor;
