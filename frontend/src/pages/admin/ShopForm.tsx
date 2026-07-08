import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface StageLink { id: number; stage_key: string; item_id: number; }
interface Stage { id: number; stage_number: number; name: string; }

const imgUrl = (p: string) => `/dragons/api/static/images/${p}?t=${Date.now()}`;

function ShopForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = !!id;
  const nav = useNavigate();
  const [load, setLoad] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [cost, setCost] = useState(0);
  const [imagePath, setImagePath] = useState('');
  const [characterEffect, setCharacterEffect] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [isLegendBook, setIsLegendBook] = useState(false);

  const [links, setLinks] = useState<StageLink[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);

  useEffect(() => {
    client.get('/admin/epic/stages').then((r) => setStages(r.data));
    if (!isEdit) return;
    client.get('/admin/shop-items').then((r) => {
      const it = r.data.find((x: any) => x.id === Number(id));
      if (it) { setName(it.name); setDescription(it.description); setCost(it.cost_stitches); setImagePath(it.image_path || ''); setCharacterEffect(it.character_effect || ''); setIsActive(it.is_active); setIsLegendBook(!!it.is_legend_book); }
    }).finally(() => setLoad(false));
    client.get('/admin/stage-shop-items').then((r) => setLinks(r.data.filter((l: StageLink) => l.item_id === Number(id))));
  }, [id]);

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };
  const onImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setImagePath(await uploadImage(file));
  };

  const save = async () => {
    if (!name.trim()) { setError('Название обязательно'); return; }
    setSaving(true); setError('');
    const payload = { name, description, cost_stitches: cost, image_path: imagePath, character_effect: characterEffect, is_active: isActive, is_legend_book: isLegendBook };
    try {
      if (isEdit) await client.put(`/admin/shop-items/${id}`, payload);
      else await client.post('/admin/shop-items', payload);
      nav('/admin/shop');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); }
    finally { setSaving(false); }
  };

  const stageForKey = (key: string): Stage | undefined => {
    const m = key.match(/^epic:(\d+)$/);
    if (!m) return undefined;
    return stages.find((s) => s.stage_number === Number(m[1]));
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>{isEdit ? 'Редактировать товар' : 'Новый товар'}</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ maxWidth: 560 }}>
          <div className="lair-form-group"><label className="lair-label">Название</label>
            <input className="lair-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Питательная смесь" /></div>
          <div className="lair-form-group"><label className="lair-label">Описание</label>
            <textarea className="lair-textarea" value={description} onChange={(e) => setDescription(e.target.value)} /></div>
          <div className="lair-form-group"><label className="lair-label">Цена (крестики)</label>
            <input className="lair-input" type="text" inputMode="numeric" value={cost} onChange={(e) => setCost(parseInt(e.target.value, 10) || 0)} style={{ width: 160 }} /></div>
          <div className="lair-form-group"><label className="lair-label">Влияние на характер (необязательно)</label>
            <input className="lair-input" value={characterEffect} onChange={(e) => setCharacterEffect(e.target.value)} placeholder="например: заботливый, смелый" />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Характер выращенного дракона складывается из купленных за выращивание товаров.</div></div>
          <div className="lair-form-group"><label className="lair-label">Картинка</label>
            <label className="lair-file"><input type="file" accept="image/*" style={{ display: 'none' }} onChange={onImage} />{imagePath ? 'Заменить...' : 'Выбрать файл...'}</label>
            {imagePath && <img src={imgUrl(imagePath)} alt="" style={{ maxWidth: 120, maxHeight: 120, marginTop: 8, borderRadius: 8 }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />}</div>
          <div className="lair-form-group"><label className="lair-checkbox"><input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Активен</label></div>
          <div className="lair-form-group"><label className="lair-checkbox"><input type="checkbox" checked={isLegendBook} onChange={(e) => setIsLegendBook(e.target.checked)} /> 📖 Книга для обучения эпического (выдаётся за завершённую легенду)</label></div>

          {isEdit && (
            <div className="lair-form-group" style={{ borderTop: '1px solid var(--bronze)', paddingTop: 16 }}>
              <label className="lair-label">Привязан к стадиям</label>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Привязка настраивается на странице стадии («Эпические драконы» → стадия → Настроить).</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {links.map((l) => {
                  const st = stageForKey(l.stage_key);
                  return st ? (
                    <button key={l.id} className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => nav(`/admin/epic/stages/${st.id}`)}>
                      Стадия {st.stage_number}: {st.name} →
                    </button>
                  ) : (
                    <span key={l.id} className="lair-badge">{l.stage_key}</span>
                  );
                })}
                {links.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Не привязан ни к одной стадии — не виден игрокам</span>}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : '💾 Сохранить'}</button>
            <button className="lair-btn lair-btn-outline" onClick={() => nav('/admin/shop')}>Отмена</button>
          </div>
        </div>
      </div>
    </>
  );
}

export default ShopForm;
