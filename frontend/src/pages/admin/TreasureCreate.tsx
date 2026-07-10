import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface AvailableDragon { id: number; name: string; egg_type: string; }
interface AvailableFamily { id: number; name: string; color: string; }

function TreasureCreate() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [mode, setMode] = useState<'dragon' | 'family'>('dragon');
  const [dragons, setDragons] = useState<AvailableDragon[]>([]);
  const [families, setFamilies] = useState<AvailableFamily[]>([]);
  const [dragonId, setDragonId] = useState<number | ''>('');
  const [familyId, setFamilyId] = useState<number | ''>('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');

  useEffect(() => {
    Promise.all([
      client.get('/admin/treasures/available-dragons'),
      client.get('/admin/treasures/available-families'),
    ]).then(([dr, fr]) => {
      setDragons(dr.data);
      setFamilies(fr.data);
    }).finally(() => setLoading(false));
  }, []);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setImageFile(file); setImagePreview(URL.createObjectURL(file)); }
  };

  const canSave = (mode === 'dragon' ? dragonId !== '' : familyId !== '') && name.trim() !== '' && !saving;

  const handleSubmit = async () => {
    if (!canSave) return;
    setSaving(true); setError('');
    try {
      const form = new FormData();
      form.append('name', name);
      form.append('description', description);
      if (imageFile) form.append('image', imageFile);
      const url = mode === 'dragon'
        ? `/admin/dragons/${dragonId}/treasure`
        : `/admin/families/${familyId}/treasure`;
      await client.post(url, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      navigate('/admin/treasures');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="lair-content"><div className="dragon-skeleton-card" style={{ height: 300 }} /></div>;

  const available = mode === 'dragon' ? dragons : families;

  return (
    <>
      <div className="lair-header"><h2>💎 Новое сокровище</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: '#d47474', fontSize: 14 }}>{error}</div>}

        <div className="lair-card" style={{ maxWidth: 600 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button className={mode === 'dragon' ? 'lair-btn' : 'lair-btn lair-btn-outline'} onClick={() => setMode('dragon')}>🐲 За дракона</button>
            <button className={mode === 'family' ? 'lair-btn' : 'lair-btn lair-btn-outline'} onClick={() => setMode('family')}>🏛 За семейство</button>
          </div>

          {available.length === 0 ? (
            <>
              <p style={{ color: 'var(--text-secondary)' }}>Нет доступных {mode === 'dragon' ? 'редких драконов' : 'семейств'} без сокровища.</p>
              <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/treasures')}>← К сокровищам</button>
            </>
          ) : (
            <>
              <div className="lair-form-group">
                <label className="lair-label">{mode === 'dragon' ? 'Редкий дракон' : 'Семейство'}</label>
                {mode === 'dragon' ? (
                  <select className="lair-input" value={dragonId} onChange={(e) => setDragonId(Number(e.target.value))}>
                    <option value="" disabled>— выберите дракона —</option>
                    {dragons.map((d) => <option key={d.id} value={d.id}>{d.name}{d.egg_type ? ` (${d.egg_type})` : ''}</option>)}
                  </select>
                ) : (
                  <select className="lair-input" value={familyId} onChange={(e) => setFamilyId(Number(e.target.value))}>
                    <option value="" disabled>— выберите семейство —</option>
                    {families.map((f) => <option key={f.id} value={f.id}> {f.name}</option>)}
                  </select>
                )}
              </div>

              <div className="lair-form-group"><label className="lair-label">Название</label><input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Кристалл Мороза" /></div>
              <div className="lair-form-group"><label className="lair-label">Описание</label><textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание сокровища" /></div>
              <div className="lair-form-group"><label className="lair-label">Фото</label><label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleImageChange} />{imageFile ? imageFile.name : 'Выбрать файл...'}</label>{imagePreview && <img src={imagePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 180, marginTop: 8, borderRadius: 'var(--radius-sm)' }} />}</div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button className="lair-btn" disabled={!canSave} onClick={handleSubmit}>{saving ? 'Сохранение...' : '💾 Сохранить'}</button>
                <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/treasures')}>Отмена</button>
              </div>
            </>
          )}
        </div>
      </div>
      <style>{`.dragon-skeleton-card{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
    </>
  );
}

export default TreasureCreate;
