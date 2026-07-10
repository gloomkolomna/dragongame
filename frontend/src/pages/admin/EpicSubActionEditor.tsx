import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Axis { id: number; positive_label: string; negative_label: string; }
interface ShopItem { id: number; name: string; }
interface SubAction {
  id: number; action_id: number; label: string; description: string;
  order_in_sub: number; image_path: string; character_axis_id: number | null;
  item_ids: number[]; steps: SubStep[]; outcomes: Outcome[];
}
interface SubStep {
  id: number; step_label: string; order: number; task: string; hint: string;
  crosses_norm: number; image_path: string; timeout_hours: number; timeout_minutes: number;
}
interface Outcome {
  id: number; polarity: string; label: string; moodlet_title: string; moodlet_text: string; image_path: string;
}

function EpicSubActionEditor() {
  const { stageId, actionId, subId } = useParams<{ stageId: string; actionId: string; subId: string }>();
  const sid = Number(stageId);
  const aid = Number(actionId);
  const suid = Number(subId);
  const nav = useNavigate();

  const [sa, setSa] = useState<SubAction | null>(null);
  const [items, setItems] = useState<ShopItem[]>([]);
  const [axes, setAxes] = useState<Axis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [editLabel, setEditLabel] = useState('');
  const [editAxisId, setEditAxisId] = useState<number | null>(null);

  const load = () => {
    client.get('/admin/epic/species').then((r) => {
      if (!r.data.length) { setLoading(false); return; }
      const did = r.data[0].id;
      client.get(`/admin/epic/species/${did}/stages/${sid}/actions`).then((rr) => {
        const action = rr.data.find((a: any) => a.id === aid);
        if (action?.sub_actions) {
          const found = action.sub_actions.find((s: any) => s.id === suid);
          if (found) {
            setSa(found);
            setEditLabel(found.label);
            setEditAxisId(found.character_axis_id ?? null);
          }
        }
        setLoading(false);
      });
    });
  };

  useEffect(() => {
    client.get('/admin/shop-items').then((r) => setItems(r.data));
    client.get('/admin/character-axes').then((r) => setAxes(r.data)).catch(() => {});
    load();
  }, [sid, aid, suid]);

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };

  const saveMeta = () => {
    if (!editLabel.trim()) { setError('Впиши название'); return; }
    client.put(`/admin/epic/sub-actions/${suid}`, { label: editLabel, character_axis_id: editAxisId })
      .then(() => load())
      .catch((e: any) => setError(e.response?.data?.detail || 'Ошибка'));
  };

  if (loading) return <div className="lair-content"><div className="lair-skeleton" /></div>;
  if (!sa) return <div className="lair-content"><div className="lair-card"><p>Поддействие не найдено.</p></div></div>;

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav(`/admin/epic/stages/${sid}/actions/${aid}`)}>← К действию</button>
        <h2 style={{ marginLeft: 12 }}>⚙ Поддействие «{sa.label}»</h2>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '8px 12px', marginBottom: 12, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}

        <div className="lair-card" style={{ maxWidth: 640, marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label className="lair-label">Название</label>
              <input className="lair-input" value={editLabel} onChange={(e) => setEditLabel(e.target.value)} />
            </div>
            <div style={{ width: 180 }}>
              <label className="lair-label">Характер</label>
              <select className="lair-input" value={editAxisId ?? ''}
                      onChange={(e) => setEditAxisId(e.target.value ? Number(e.target.value) : null)}>
                <option value="">Без характера</option>
                {axes.map((ax) => <option key={ax.id} value={ax.id}>{ax.positive_label} ⇄ {ax.negative_label}</option>)}
              </select>
            </div>
            <button className="lair-btn" onClick={saveMeta}>💾 Сохранить</button>
          </div>

          <div style={{ marginBottom: 10 }}>
            <ItemPicker subActionId={suid} currentIds={sa.item_ids || []} items={items} reload={load} />
          </div>
        </div>

        <div className="lair-card" style={{ maxWidth: 640, marginBottom: 16 }}>
          <h3 style={{ color: 'var(--gold)', margin: '0 0 8px' }}>Шаги вышивки</h3>
          <StepsEditor subActionId={suid} steps={sa.steps || []} reload={load} uploadImage={uploadImage} />
        </div>

        <div className="lair-card" style={{ maxWidth: 640 }}>
          <h3 style={{ color: 'var(--gold)', margin: '0 0 8px' }}>Исходы</h3>
          <OutcomesEditor subActionId={suid} outcomes={sa.outcomes || []} reload={load} uploadImage={uploadImage} />
        </div>
      </div>
    </>
  );
}

function ItemPicker({ subActionId, currentIds, items, reload }: any) {
  const [q, setQ] = useState('');
  const [sel, setSel] = useState<number[]>(currentIds || []);
  const matched = items.filter((i: ShopItem) => i.name.toLowerCase().includes(q.toLowerCase()));

  useEffect(() => { setSel(currentIds || []); }, [currentIds]);

  const toggle = async (id: number) => {
    const next = sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id];
    setSel(next);
    await client.put(`/admin/epic/sub-actions/${subActionId}`, { item_ids: next });
    reload();
  };

  return (
    <div>
      <label className="lair-label">Требуемые товары</label>
      {sel.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
          {sel.map((id: number) => { const it = items.find((x: ShopItem) => x.id === id); return it ? (
            <span key={id} className="lair-badge" onClick={() => toggle(id)} style={{ cursor: 'pointer', background: 'var(--accent-dark)' }}>{it.name} ✕</span>
          ) : null; })}
        </div>
      )}
      <input className="lair-input" type="text" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="🔍 Поиск товаров…" style={{ marginBottom: 4 }} />
      <div style={{ maxHeight: 160, overflowY: 'auto', border: '1px solid var(--bronze)', borderRadius: 6, padding: 4 }}>
        {matched.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 13, padding: 4 }}>Ничего не найдено</span>}
        {matched.map((i: ShopItem) => (
          <label key={i.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', cursor: 'pointer', fontSize: 13, borderRadius: 4, background: sel.includes(i.id) ? 'rgba(153,102,255,0.15)' : 'transparent' }}>
            <input type="checkbox" checked={sel.includes(i.id)} onChange={() => toggle(i.id)} />
            {i.name}
          </label>
        ))}
      </div>
    </div>
  );
}

function StepsEditor({ subActionId, steps, reload, uploadImage }: any) {
  const addStep = async () => {
    await client.post(`/admin/epic/sub-actions/${subActionId}/steps`, { step_label: 'Новый шаг', order: steps.length + 1, crosses_norm: 1000, timeout_hours: 24, timeout_minutes: 0 });
    reload();
  };
  const delStep = async (id: number) => { await client.delete(`/admin/epic/sub-actions/steps/${id}`); reload(); };

  return (
    <div>
      {steps.map((s: SubStep) => (
        <StepCard key={s.id} step={s} reload={reload} delStep={delStep} uploadImage={uploadImage} />
      ))}
      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={addStep} style={{ marginTop: 8 }}>+ Добавить шаг</button>
    </div>
  );
}

function StepCard({ step, reload, delStep, uploadImage }: any) {
  const [label, setLabel] = useState(step.step_label);
  const [task, setTask] = useState(step.task || '');
  const [hint, setHint] = useState(step.hint || '');
  const [norm, setNorm] = useState(step.crosses_norm);
  const [th, setTh] = useState(step.timeout_hours ?? 24);
  const [tm, setTm] = useState(step.timeout_minutes ?? 0);
  const [imagePath, setImagePath] = useState(step.image_path || '');

  const save = () => {
    client.put(`/admin/epic/sub-actions/steps/${step.id}`, {
      step_label: label, task, hint, crosses_norm: Math.max(1, norm),
      timeout_hours: th, timeout_minutes: tm, image_path: imagePath,
    }).then(() => reload());
  };

  return (
    <div style={{ marginBottom: 10, padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 6, border: '1px solid rgba(180,150,100,0.15)' }}>
      <div style={{ fontSize: 12, color: 'var(--gold)', marginBottom: 6 }}>Шаг #{step.order}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px 70px 70px', gap: 6, marginBottom: 6 }}>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>Название</label>
          <input className="lair-input" value={label} onChange={(e) => setLabel(e.target.value)} onBlur={save} style={{ height: 28, fontSize: 12 }} />
        </div>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>Норма</label>
          <input className="lair-input" type="text" inputMode="numeric" value={norm}
                 onChange={(e) => setNorm(Math.max(1, parseInt(e.target.value, 10) || 1))} onBlur={save}
                 style={{ height: 28, fontSize: 12 }} />
        </div>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>Таймаут ч</label>
          <input className="lair-input" type="text" inputMode="numeric" value={th}
                 onChange={(e) => setTh(Math.max(0, parseInt(e.target.value, 10) || 0))} onBlur={save}
                 style={{ height: 28, fontSize: 12 }} />
        </div>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>мин</label>
          <input className="lair-input" type="text" inputMode="numeric" value={tm}
                 onChange={(e) => setTm(Math.max(0, parseInt(e.target.value, 10) || 0))} onBlur={save}
                 style={{ height: 28, fontSize: 12 }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 6 }}>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>Задание</label>
          <input className="lair-input" value={task} onChange={(e) => setTask(e.target.value)} onBlur={save} placeholder="Текст задания" style={{ height: 28, fontSize: 12 }} />
        </div>
        <div>
          <label className="lair-label" style={{ fontSize: 11 }}>Подсказка</label>
          <input className="lair-input" value={hint} onChange={(e) => setHint(e.target.value)} onBlur={save} placeholder="💡 Подсказка" style={{ height: 28, fontSize: 12 }} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <label className="lair-file" style={{ margin: 0, fontSize: 11 }}>
          <input type="file" accept="image/*" style={{ display: 'none' }}
                 onChange={async (e) => { const f = e.target.files?.[0]; if (f) { const p = await uploadImage(f); setImagePath(p); client.put(`/admin/epic/sub-actions/steps/${step.id}`, { image_path: p }).then(() => reload()); } }} />
          {imagePath ? '🖼 Заменить' : '🖼 Фото шага'}
        </label>
        {imagePath && (
          <img src={`/dragons/api/static/images/${imagePath}?t=${Date.now()}`} alt=""
               style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--bronze)', cursor: 'pointer' }}
               onClick={() => window.open(`/dragons/api/static/images/${imagePath}`, '_blank')}
               onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        )}
        <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => delStep(step.id)} style={{ marginLeft: 'auto', fontSize: 11 }}>✕ Удалить</button>
      </div>
    </div>
  );
}

function OutcomesEditor({ subActionId, outcomes, reload, uploadImage }: any) {
  const updateOutcome = async (id: number, data: any) => { await client.put(`/admin/epic/sub-actions/outcomes/${id}`, data); reload(); };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {outcomes.map((o: Outcome) => (
        <div key={o.id} style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 6, border: '1px solid rgba(180,150,100,0.15)' }}>
          <div style={{ fontSize: 13, color: o.polarity === 'positive' ? '#6fcf97' : '#d474a0', marginBottom: 8, fontWeight: 600 }}>
            {o.polarity === 'positive' ? '🌟 Положительный исход' : '💔 Отрицательный исход'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            <div>
              <label className="lair-label" style={{ fontSize: 11 }}>Заголовок мудлета</label>
              <input className="lair-input" defaultValue={o.moodlet_title}
                     onBlur={(e) => updateOutcome(o.id, { moodlet_title: e.target.value })}
                     placeholder="Например: Поймал рыбку!" style={{ height: 32, fontSize: 13 }} />
            </div>
            <div>
              <label className="lair-label" style={{ fontSize: 11 }}>Текст мудлета</label>
              <input className="lair-input" defaultValue={o.moodlet_text}
                     onBlur={(e) => updateOutcome(o.id, { moodlet_text: e.target.value })}
                     placeholder="Описание того, что произошло" style={{ height: 32, fontSize: 13 }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label className="lair-file" style={{ margin: 0, fontSize: 12 }}>
              <input type="file" accept="image/*" style={{ display: 'none' }}
                     onChange={async (e) => { const f = e.target.files?.[0]; if (f) { const p = await uploadImage(f); updateOutcome(o.id, { image_path: p }); } }} />
              {o.image_path ? '🖼 Заменить картинку' : '🖼 Добавить картинку'}
            </label>
            {o.image_path && (
              <img src={`/dragons/api/static/images/${o.image_path}?t=${Date.now()}`} alt=""
                   style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                   onClick={() => window.open(`/dragons/api/static/images/${o.image_path}`, '_blank')}
                   onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default EpicSubActionEditor;
