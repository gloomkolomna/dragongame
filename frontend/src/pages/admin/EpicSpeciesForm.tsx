import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Step {
  id: number; dragon_id: number; step_number: number;
  magic_action: string; task_description: string; hint: string;
  timeout_hours: number; timeout_minutes: number; crosses_norm: number;
}

function EpicSpeciesForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [eggType, setEggType] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    if (!isEdit) return;
    Promise.all([
      client.get(`/admin/dragons/${id}`),
      client.get(`/admin/dragons/${id}/steps`),
    ]).then(([d, s]) => {
      const dr = d.data;
      setName(dr.name); setEggType(dr.egg_type); setDescription(dr.description); setIsActive(dr.is_active);
      if (dr.egg_path) setImagePreview(`/dragons/api/static/images/${dr.egg_path}?t=${Date.now()}`);
      setSteps(s.data);
    }).finally(() => setLoading(false));
  }, [id]);

  const onImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setImageFile(file); setImagePreview(URL.createObjectURL(file)); }
  };

  const handleSubmit = async () => {
    if (!name.trim()) { setError('Имя вида обязательно'); return; }
    setSaving(true); setError('');
    try {
      const form = new FormData();
      form.append('name', name);
      form.append('rarity', '1');
      form.append('egg_type', eggType);
      form.append('description', description);
      form.append('is_active', String(isActive));
      form.append('is_epic', 'true');
      if (imageFile) form.append('image', imageFile);
      if (steps.length > 0) {
        form.append('steps', JSON.stringify(steps.map((s, i) => ({ ...s, step_number: i + 1 }))));
      }
      if (isEdit) {
        await client.put(`/admin/dragons/${id}`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await client.post('/admin/dragons', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      navigate('/admin/epic');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaving(false); }
  };

  const addStep = () => setSteps((prev) => [...prev, { id: 0, dragon_id: Number(id) || 0, step_number: prev.length + 1, magic_action: '', task_description: '', hint: '', timeout_hours: 0, timeout_minutes: 0, crosses_norm: 1000 }]);
  const removeStep = (i: number) => setSteps((prev) => prev.filter((_, idx) => idx !== i));
  const updStep = (i: number, f: keyof Step, v: string) => {
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

  if (loading) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => navigate('/admin/epic')}>← Назад</button>
        <h2 style={{ marginLeft: 12 }}>{isEdit ? 'Редактирование' : 'Создание'} эпического вида</h2>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: '#d47474', fontSize: 14 }}>{error}</div>}
        <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 'var(--radius-sm)', background: 'rgba(155,111,199,0.15)', color: 'var(--accent-gold-light)', fontSize: 14 }}>
          🥚 Эпический вырастает из яйца по этим шагам. После вылупления бот предложит дать имя, и начнутся стадии ухода.
        </div>

        <div className="lair-card" style={{ maxWidth: 600 }}>
          <div className="lair-form-group">
            <label className="lair-label">Имя вида</label>
            <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Туманный дракончик" />
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Тип яйца (Эпическое)</label>
            <input className="lair-input" value={eggType} onChange={(e) => setEggType(e.target.value)} placeholder="серебристое с искрами" />
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание вида" />
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Картинка яйца</label>
            <label className="lair-file">
              <input type="file" accept="image/*" style={{ display: 'none' }} onChange={onImage} />
              {imageFile ? imageFile.name : 'Выбрать файл...'}
            </label>
            {imagePreview && <img src={imagePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 180, marginTop: 8, borderRadius: 'var(--radius-sm)' }} />}
          </div>

          <div className="lair-form-group">
            <label className="lair-checkbox">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Активен (может выпадать игрокам)
            </label>
          </div>

          <div className="lair-form-group" style={{ borderTop: '1px solid var(--bronze)', paddingTop: 16, marginTop: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <label className="lair-label" style={{ marginBottom: 0 }}>Шаги выращивания яйца ({steps.length})</label>
              <button type="button" className="lair-btn lair-btn-sm" onClick={addStep}>+ Шаг</button>
            </div>
            {steps.map((s, i) => (
              <div key={i} style={{ padding: '10px 12px', marginBottom: 8, background: 'rgba(30,20,42,0.4)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--bronze)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ color: 'var(--accent-gold-light)', fontSize: 14, fontWeight: 600 }}>Шаг {i + 1}</span>
                  <button type="button" className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => removeStep(i)}>🗑</button>
                </div>
                <input className="lair-input" style={{ marginBottom: 6, fontSize: 28, padding: '7px 10px' }}
                       value={s.magic_action} onChange={(e) => updStep(i, 'magic_action', e.target.value)}
                       placeholder="Магическое действие" />
                <textarea className="lair-textarea" style={{ marginBottom: 6, fontSize: 28, minHeight: 50, padding: '7px 10px' }}
                          value={s.task_description} onChange={(e) => updStep(i, 'task_description', e.target.value)}
                          placeholder="Задание по вышивке" />
                <input className="lair-input" style={{ fontSize: 26, padding: '6px 8px' }}
                       value={s.hint} onChange={(e) => updStep(i, 'hint', e.target.value)}
                       placeholder="Подсказка (опционально)" />
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 6 }}>
                  <input className="lair-input" type="text" inputMode="numeric" value={s.timeout_hours}
                         onChange={(e) => updStep(i, 'timeout_hours', e.target.value)}
                         style={{ width: 60, fontSize: 26, padding: '6px 8px' }} placeholder="0" />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>ч</span>
                  <input className="lair-input" type="text" inputMode="numeric" value={s.timeout_minutes}
                         onChange={(e) => updStep(i, 'timeout_minutes', e.target.value)}
                         style={{ width: 60, fontSize: 26, padding: '6px 8px' }} placeholder="0" />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>мин</span>
                  <span style={{ marginLeft: 12, color: 'var(--text-muted)', fontSize: 12 }}>Норма:</span>
                  <input className="lair-input" type="text" inputMode="numeric" value={s.crosses_norm}
                         onChange={(e) => updStep(i, 'crosses_norm', e.target.value)}
                         style={{ width: 80, fontSize: 26, padding: '6px 8px' }} placeholder="1000" />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>крест.</span>
                </div>
              </div>
            ))}
            {steps.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: 14, textAlign: 'center', padding: 12 }}>
                Нажми «+ Шаг» чтобы добавить шаги выращивания яйца
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={handleSubmit}>
              {saving ? 'Сохранение...' : isEdit ? '💾 Сохранить' : '🥚 Создать вид'}
            </button>
            <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/epic')}>Отмена</button>
          </div>
        </div>
      </div>
    </>
  );
}

export default EpicSpeciesForm;
