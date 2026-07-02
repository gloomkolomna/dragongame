import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Dragon {
  id: number; name: string; rarity: number; egg_type: string;
  steps_count: number; description: string; egg_path: string;
  dragon_path: string; is_active: boolean; family_id: number | null;
}
interface Family { id: number; name: string; }
interface Step {
  id: number; dragon_id: number; step_number: number;
  magic_action: string; task_description: string; hint: string;
}

function DragonForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const navigate = useNavigate();
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [rarity, setRarity] = useState(1);
  const [eggType, setEggType] = useState('');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [silhouetteFile, setSilhouetteFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');
  const [silhouettePreview, setSilhouettePreview] = useState('');
  const [families, setFamilies] = useState<Family[]>([]);
  const [familyId, setFamilyId] = useState<number | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);

  useEffect(() => {
    client.get('/admin/families').then((r) => setFamilies(r.data));
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    Promise.all([
      client.get(`/admin/dragons/${id}`),
      client.get(`/admin/dragons/${id}/steps`),
    ]).then(([d, s]) => {
      const dr: Dragon = d.data;
      setName(dr.name); setRarity(dr.rarity); setEggType(dr.egg_type);
      setDescription(dr.description); setIsActive(dr.is_active);
      setFamilyId(dr.family_id ?? null);
      if (dr.egg_path) setImagePreview(`/dragons/api/static/images/${dr.egg_path}?t=${Date.now()}`);
      if (dr.dragon_path) setSilhouettePreview(`/dragons/api/static/images/${dr.dragon_path}?t=${Date.now()}`);
      setSteps(s.data);
    }).finally(() => setLoading(false));
  }, [id]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>, setFile: (f: File | null) => void, setPrev: (s: string) => void) => {
    const file = e.target.files?.[0];
    if (file) { setFile(file); setPrev(URL.createObjectURL(file)); }
  };

  const handleSubmit = async () => {
    setSaving(true); setError('');
    if (!familyId) { setError('Выберите семейство / союз — это обязательно'); setSaving(false); return; }
    try {
      const form = new FormData();
      form.append('name', name);
      form.append('rarity', String(rarity));
      form.append('egg_type', eggType);
      form.append('description', description);
      form.append('is_active', String(isActive));
      form.append('family_id', String(familyId));
      if (imageFile) form.append('image', imageFile);
      if (silhouetteFile) form.append('silhouette', silhouetteFile);
      if (steps.length > 0) {
        form.append('steps', JSON.stringify(steps.map((s, i) => ({ ...s, step_number: i + 1 }))));
      }
      if (isEdit) {
        await client.put(`/admin/dragons/${id}`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await client.post('/admin/dragons', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      navigate('/admin/dragons');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaving(false); }
  };

  const addStep = () => setSteps([...steps, { id: 0, dragon_id: Number(id) || 0, step_number: steps.length + 1, magic_action: '', task_description: '', hint: '' }]);
  const removeStep = (i: number) => setSteps(steps.filter((_, idx) => idx !== i));
  const updStep = (i: number, f: keyof Step, v: string) => {
    const s = [...steps];
    (s[i] as any)[f] = v;
    setSteps(s);
  };

  if (loading) return <div className="lair-content"><div className="dragon-skeleton-card" style={{ height: 400 }} /></div>;

  return (
    <>
      <div className="lair-header">
        <h2>{isEdit ? 'Редактирование' : 'Создание дракона'}</h2>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: '#d47474', fontSize: 13 }}>{error}</div>}

        <div className="lair-card" style={{ maxWidth: 600 }}>
          <div className="lair-form-group">
            <label className="lair-label">Название (скрыто от игрока до финала)</label>
            <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ледяной Ветер" />
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Редкость</label>
            <select className="lair-select" value={rarity} onChange={(e) => setRarity(Number(e.target.value))}>
              <option value={1}>Обычный</option>
              <option value={2}>Редкий</option>
              <option value={3}>Эпический</option>
              <option value={4}>Легендарный</option>
            </select>
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Семейство / Союз *</label>
            <select className="lair-select" value={familyId ?? ''} onChange={(e) => setFamilyId(e.target.value ? Number(e.target.value) : null)}>
              {!familyId && <option value="">— выберите —</option>}
              {families.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Тип яйца</label>
            <input className="lair-input" value={eggType} onChange={(e) => setEggType(e.target.value)} placeholder="голубое с ледяными узорами" />
          </div>

          <div className="lair-form-group">
            <label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание для финальной карточки дракона" />
          </div>

          <div className="lair-form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="lair-label">Яйцо</label>
              <label className="lair-file">
                <input type="file" accept="image/*" style={{ display: 'none' }}
                       onChange={(e) => handleImageChange(e, setImageFile, setImagePreview)} />
                {imageFile ? imageFile.name : 'Выбрать файл...'}
              </label>
              {imagePreview && <img src={imagePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 160, marginTop: 8, borderRadius: 'var(--radius-sm)' }} />}
            </div>
            <div>
              <label className="lair-label">Дракон</label>
              <label className="lair-file">
                <input type="file" accept="image/*" style={{ display: 'none' }}
                       onChange={(e) => handleImageChange(e, setSilhouetteFile, setSilhouettePreview)} />
                {silhouetteFile ? silhouetteFile.name : 'Выбрать файл...'}
              </label>
              {silhouettePreview && <img src={silhouettePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 160, marginTop: 8, borderRadius: 'var(--radius-sm)', opacity: 0.6 }} />}
            </div>
          </div>

          <div className="lair-form-group">
            <label className="lair-checkbox">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Активен (доступен для игры)
            </label>
          </div>

          <div className="lair-form-group" style={{ borderTop: '1px solid var(--bronze)', paddingTop: 16, marginTop: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <label className="lair-label" style={{ marginBottom: 0 }}>Шаги выращивания ({steps.length})</label>
              <button type="button" className="lair-btn lair-btn-sm" onClick={addStep}>+ Шаг</button>
            </div>
            {steps.map((s, i) => (
              <div key={i} style={{
                padding: '10px 12px', marginBottom: 8,
                background: 'rgba(30,20,42,0.4)', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--bronze)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ color: 'var(--accent-gold-light)', fontSize: 13, fontWeight: 600 }}>Шаг {i + 1}</span>
                  <button type="button" className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => removeStep(i)}>🗑</button>
                </div>
                <input className="lair-input" style={{ marginBottom: 6, fontSize: 13, padding: '6px 10px' }}
                       value={s.magic_action} onChange={(e) => updStep(i, 'magic_action', e.target.value)}
                       placeholder="Магическое действие (Положи яйцо на снег)" />
                <textarea className="lair-textarea" style={{ marginBottom: 6, fontSize: 13, minHeight: 50, padding: '6px 10px' }}
                          value={s.task_description} onChange={(e) => updStep(i, 'task_description', e.target.value)}
                          placeholder="Задание по вышивке" />
                <input className="lair-input" style={{ fontSize: 12, padding: '5px 8px' }}
                       value={s.hint} onChange={(e) => updStep(i, 'hint', e.target.value)}
                       placeholder="Подсказка (опционально)" />
              </div>
            ))}
            {steps.length === 0 && (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 12 }}>
                Нажми «+ Шаг» чтобы добавить шаги выращивания
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={handleSubmit}>
              {saving ? 'Сохранение...' : isEdit ? '💾 Сохранить' : '🐣 Создать'}
            </button>
            <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/dragons')}>Отмена</button>
          </div>
        </div>
      </div>

      <style>{`.dragon-skeleton-card{height:400px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
    </>
  );
}

export default DragonForm;
