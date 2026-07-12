import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

function EpicStageForm() {
  const { stageId, dragonId } = useParams<{ stageId: string; dragonId: string }>();
  const isEdit = !!stageId;
  const nav = useNavigate();
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [dragon, setDragon] = useState<number | null>(dragonId ? Number(dragonId) : null);
  const [stageNumber, setStageNumber] = useState(1);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cycles, setCycles] = useState(3);
  const [imageStart, setImageStart] = useState('');
  const [imageEnd, setImageEnd] = useState('');

  useEffect(() => {
    if (isEdit) {
      client.get('/admin/epic/stages').then((r) => {
        const s = r.data.find((x: any) => x.id === Number(stageId));
        if (s) {
          setDragon(s.dragon_id);
          setStageNumber(s.stage_number); setName(s.name); setDescription(s.description);
          setCycles(s.cycles_count); setImageStart(s.image_start || ''); setImageEnd(s.image_end || '');
        }
      }).finally(() => setLoad(false));
    } else {
      const did = dragonId ? Number(dragonId) : null;
      setDragon(did);
      client.get('/admin/epic/stages', { params: did ? { dragon_id: did } : {} }).then((r) => {
        const maxNum = r.data.length ? Math.max(...r.data.map((x: any) => x.stage_number)) : 0;
        setStageNumber(maxNum + 1);
      }).finally(() => setLoad(false));
    }
  }, [stageId, dragonId]);

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };
  const onImageStart = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setImageStart(await uploadImage(file));
  };
  const onImageEnd = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setImageEnd(await uploadImage(file));
  };

  const save = async () => {
    if (!name.trim()) { setError('Название стадии обязательно'); return; }
    if (!isEdit && !dragon) { setError('Не указан эпический дракон'); return; }
    setSaving(true); setError('');
    const payload: any = { stage_number: stageNumber, name, description, cycles_count: cycles, image_start: imageStart, image_end: imageEnd };
    try {
      if (isEdit) await client.put(`/admin/epic/stages/${stageId}`, payload);
      else await client.post('/admin/epic/stages', { ...payload, dragon_id: dragon });
      nav('/admin/epic');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); }
    finally { setSaving(false); }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav('/admin/epic')}>← Назад</button>
        <h2 style={{ marginLeft: 12 }}>{isEdit ? 'Редактировать стадию' : 'Новая стадия'}</h2>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ maxWidth: 560 }}>
          <div className="lair-form-group" style={{ display: 'grid', gridTemplateColumns: '90px 1fr', gap: 8 }}>
            <div><label className="lair-label">№</label>
              <input className="lair-input" type="text" inputMode="numeric" value={stageNumber} onChange={(e) => setStageNumber(parseInt(e.target.value, 10) || 0)} /></div>
            <div><label className="lair-label">Название</label>
              <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Вылупленное чудо" /></div>
          </div>
          <div className="lair-form-group"><label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} /></div>
          <div className="lair-form-group" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="lair-label">Картинка — начало стадии</label>
              <label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={onImageStart} />{imageStart ? 'Заменить...' : 'Выбрать файл...'}</label>
              {imageStart && <img src={`/dragons/api/static/images/${imageStart}?t=${Date.now()}`} alt="" style={{ maxWidth: '100%', maxHeight: 150, marginTop: 8, borderRadius: 8 }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}
            </div>
            <div>
              <label className="lair-label">Картинка — финал стадии</label>
              <label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={onImageEnd} />{imageEnd ? 'Заменить...' : 'Выбрать файл...'}</label>
              {imageEnd && <img src={`/dragons/api/static/images/${imageEnd}?t=${Date.now()}`} alt="" style={{ maxWidth: '100%', maxHeight: 150, marginTop: 8, borderRadius: 8 }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}
            </div>
          </div>
          <div className="lair-form-group" style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
            <div><label className="lair-label">Циклы</label>
              <input className="lair-input" type="text" inputMode="numeric" value={cycles} onChange={(e) => setCycles(parseInt(e.target.value, 10) || 1)} /></div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : '💾 Сохранить'}</button>
            <button className="lair-btn lair-btn-outline" onClick={() => nav('/admin/epic')}>Отмена</button>
          </div>
          {isEdit && (
            <div style={{ marginTop: 16, borderTop: '1px solid var(--bronze)', paddingTop: 12 }}>
              <button className="lair-btn lair-btn-outline" onClick={() => nav(`/admin/epic/stages/${stageId}`)}>⚙ Действия и выборы стадии</button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default EpicStageForm;
