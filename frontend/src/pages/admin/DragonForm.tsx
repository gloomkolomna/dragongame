import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Dragon {
  id: number; name: string; rarity: number; egg_type: string;
  steps_count: number; description: string; image_path: string;
  silhouette_path: string; is_active: boolean; family_id: number | null;
}
interface Family { id: number; name: string; }

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

  useEffect(() => {
    client.get('/admin/families').then((r) => setFamilies(r.data));
  }, []);

  useEffect(() => {
    if (!isEdit) return;
    client.get(`/admin/dragons/${id}`).then((r) => {
      const d: Dragon = r.data;
      setName(d.name); setRarity(d.rarity); setEggType(d.egg_type);
      setDescription(d.description); setIsActive(d.is_active);
      setFamilyId(d.family_id ?? null);
      if (d.image_path) setImagePreview(`/dragons/api/static/images/${d.image_path}?t=${Date.now()}`);
      if (d.silhouette_path) setSilhouettePreview(`/dragons/api/static/images/${d.silhouette_path}?t=${Date.now()}`);
    }).finally(() => setLoading(false));
  }, [id]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>, setFile: (f: File | null) => void, setPrev: (s: string) => void) => {
    const file = e.target.files?.[0];
    if (file) { setFile(file); setPrev(URL.createObjectURL(file)); }
  };

  const handleSubmit = async () => {
    setSaving(true); setError('');
    try {
      const form = new FormData();
      form.append('name', name);
      form.append('rarity', String(rarity));
      form.append('egg_type', eggType);
      form.append('description', description);
      form.append('is_active', String(isActive));
      if (familyId !== null) form.append('family_id', String(familyId));
      if (imageFile) form.append('image', imageFile);
      if (silhouetteFile) form.append('silhouette', silhouetteFile);
      if (isEdit) {
        await client.put(`/admin/dragons/${id}`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      } else {
        await client.post('/admin/dragons', form, { headers: { 'Content-Type': 'multipart/form-data' } });
      }
      navigate('/admin/dragons');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaving(false); }
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
            <label className="lair-label">Семейство</label>
            <select className="lair-select" value={familyId ?? ''} onChange={(e) => setFamilyId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">Без семейства</option>
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
              <label className="lair-label">Изображение</label>
              <label className="lair-file">
                <input type="file" accept="image/*" style={{ display: 'none' }}
                       onChange={(e) => handleImageChange(e, setImageFile, setImagePreview)} />
                {imageFile ? imageFile.name : 'Выбрать файл...'}
              </label>
              {imagePreview && <img src={imagePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 160, marginTop: 8, borderRadius: 'var(--radius-sm)' }} />}
            </div>
            <div>
              <label className="lair-label">Силуэт</label>
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
