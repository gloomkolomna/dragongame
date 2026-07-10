import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Treasure {
  id: number; name: string; description: string; image_path: string;
  dragon_id: number | null; family_id: number | null; is_active: boolean;
}

function FamilyTreasureForm() {
  const { id } = useParams<{ id: string }>();
  const fid = Number(id);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [familyName, setFamilyName] = useState('');
  const [treasure, setTreasure] = useState<Treasure | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');

  useEffect(() => {
    Promise.all([
      client.get('/admin/families'),
      client.get('/admin/treasures'),
    ]).then(([fams, treas]) => {
      const fam = fams.data.find((f: any) => f.id === fid);
      if (fam) setFamilyName(fam.name);
      const t = treas.data.find((t: Treasure) => t.family_id === fid);
      if (t) {
        setTreasure(t);
        setName(t.name);
        setDescription(t.description);
        if (t.image_path) setImagePreview(`/dragons${t.image_path}?t=${Date.now()}`);
      }
    }).finally(() => setLoading(false));
  }, [fid]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setImageFile(file); setImagePreview(URL.createObjectURL(file)); }
  };

  const handleSubmit = async () => {
    setSaving(true); setError('');
    try {
      const form = new FormData();
      form.append('name', name);
      form.append('description', description);
      if (imageFile) form.append('image', imageFile);
      await client.post(`/admin/families/${fid}/treasure`, form, { headers: { 'Content-Type': 'multipart/form-data' } });
      navigate('/admin/treasures');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка сохранения'); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!treasure) return;
    if (!confirm('Удалить сокровище?')) return;
    try { await client.delete(`/admin/treasures/${treasure.id}`); navigate('/admin/treasures'); }
    catch (e: any) { setError(e.response?.data?.detail || 'Ошибка удаления'); }
  };

  if (loading) return <div className="lair-content"><div className="dragon-skeleton-card" style={{ height: 300 }} /></div>;

  return (
    <>
      <div className="lair-header"><h2>💎 Сокровище семейства «{familyName}»</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 'var(--radius-sm)', background: 'var(--danger-bg)', color: '#d47474', fontSize: 14 }}>{error}</div>}
        <div className="lair-card" style={{ maxWidth: 600 }}>
          <div className="lair-form-group"><label className="lair-label">Название</label><input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Кристалл Мороза" /></div>
          <div className="lair-form-group"><label className="lair-label">Описание</label><textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Описание сокровища" /></div>
          <div className="lair-form-group"><label className="lair-label">Фото</label><label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleImageChange} />{imageFile ? imageFile.name : 'Выбрать файл...'}</label>{imagePreview && <img src={imagePreview} alt="" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} style={{ maxWidth: '100%', maxHeight: 180, marginTop: 8, borderRadius: 'var(--radius-sm)' }} />}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={handleSubmit}>{saving ? 'Сохранение...' : '💾 Сохранить'}</button>
            {treasure && <button className="lair-btn lair-btn-danger" disabled={saving} onClick={handleDelete}>🗑 Удалить</button>}
            <button className="lair-btn lair-btn-outline" onClick={() => navigate('/admin/treasures')}>Отмена</button>
          </div>
        </div>
      </div>
      <style>{`.dragon-skeleton-card{height:300px;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);animation:shimmer 1.5s infinite}@keyframes shimmer{0%{opacity:.4}50%{opacity:.7}100%{opacity:.4}}`}</style>
    </>
  );
}

export default FamilyTreasureForm;
