import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Action { id: number; dragon_id: number; stage_id: number; action_label: string; order_in_cycle: number; task: string; hint: string; crosses_norm: number; image_path: string; action_type: string; timeout_hours: number; timeout_minutes: number; item_ids: number[]; random_outcome?: boolean; character_axis_id?: number | null; description?: string; confirm_button_label?: string; outcomes?: Outcome[]; sub_actions?: SubAction[]; }
interface ShopItem { id: number; name: string; }
interface Axis { id: number; positive_label: string; negative_label: string; }
interface SubAction { id: number; label: string; description: string; order_in_sub: number; image_path: string; character_axis_id: number | null; item_ids: number[]; steps: SubStep[]; outcomes: Outcome[]; }
interface SubStep { id: number; step_label: string; order: number; task: string; hint: string; crosses_norm: number; image_path: string; timeout_hours: number; timeout_minutes: number; }
interface Outcome { id: number; polarity: string; label: string; moodlet_title: string; moodlet_text: string; image_path: string; }

function EpicActionEditor() {
  const { stageId, actionId } = useParams<{ stageId: string; actionId: string }>();
  const sid = Number(stageId);
  const aid = Number(actionId);
  const nav = useNavigate();
  const didRef = useRef<number | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [items, setItems] = useState<ShopItem[]>([]);
  const [axes, setAxes] = useState<Axis[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [edit, setEdit] = useState({ action_label: '', task: '', crosses_norm: 1000, hint: '', image_path: '', action_type: 'simple', timeout_hours: 24, timeout_minutes: 0, item_ids: [] as number[], random_outcome: true, character_axis_id: null as number | null, description: '', confirm_button_label: '' });

  useEffect(() => {
    client.get('/admin/shop-items').then((r) => setItems(r.data));
    client.get('/admin/character-axes').then((r) => setAxes(r.data)).catch(() => {});
    loadAction();
  }, [aid, sid]);

  const loadAction = () => {
    const fetchActions = (did: number) => {
      client.get(`/admin/epic/species/${did}/stages/${sid}/actions`).then((rr) => {
        const a = rr.data.find((x: Action) => x.id === aid);
        if (a) {
          didRef.current = a.dragon_id;
          setAction(a);
          setEdit({
            action_label: a.action_label, task: a.task || '', crosses_norm: a.crosses_norm, hint: a.hint || '',
            image_path: a.image_path || '', action_type: a.action_type || 'simple',
            timeout_hours: a.timeout_hours ?? 24, timeout_minutes: a.timeout_minutes ?? 0,
            item_ids: [...(a.item_ids || [])],
            random_outcome: a.random_outcome ?? true, character_axis_id: a.character_axis_id ?? null,
            description: a.description || '', confirm_button_label: a.confirm_button_label || '',
          });
        }
        setLoading(false);
      });
    };

    if (didRef.current) {
      fetchActions(didRef.current);
      return;
    }
    client.get('/admin/epic/species').then((r) => {
      if (!r.data.length) { setLoading(false); return; }
      fetchActions(r.data[0].id);
    });
  };

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };

  const save = async () => {
    if (!edit.action_label.trim()) { setError('Впиши название'); return; }
    setSaving(true); setError('');
    try {
      await client.put(`/admin/epic/actions/${aid}`, edit);
      nav(`/admin/epic/stages/${sid}`);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка сохранения');
    } finally { setSaving(false); }
  };

  const toggleItem = (id: number) => setEdit((e) => ({ ...e, item_ids: e.item_ids.includes(id) ? e.item_ids.filter((x) => x !== id) : [...e.item_ids, id] }));

  const saveOutcomeMeta = async (data: any) => {
    try {
      await client.put(`/admin/epic/actions/${aid}`, data);
      loadAction();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  if (loading) return <div className="lair-content"><div className="lair-skeleton" /></div>;
  if (!action) return <div className="lair-content"><div className="lair-card"><p>Действие не найдено.</p><button className="lair-btn lair-btn-outline" onClick={() => nav(`/admin/epic/stages/${sid}`)}>← К стадии</button></div></div>;

  const isComposite = edit.action_type === 'composite';

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav(`/admin/epic/stages/${sid}`)}>← К стадии</button>
        <h2 style={{ marginLeft: 12 }}>⚙ Действие «{action.action_label}»</h2>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '8px 12px', marginBottom: 12, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}

        <div className="lair-card" style={{ maxWidth: 700, marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <label className="lair-label">Название действия</label>
              <input className="lair-input" value={edit.action_label} onChange={(e) => setEdit({ ...edit, action_label: e.target.value })} />
            </div>
            <div style={{ width: 180 }}>
              <label className="lair-label">Тип</label>
              <select className="lair-input" value={edit.action_type} onChange={(e) => setEdit({ ...edit, action_type: e.target.value })}>
                <option value="simple">Простое (normal/x2)</option>
                <option value="composite">Составное (выбор→шаги→исход)</option>
              </select>
            </div>
          </div>

          {!isComposite && (
            <>
              <div style={{ marginBottom: 12 }}>
                <label className="lair-label">Нужные товары (если пусто — задание с крестиками)</label>
                <ItemPicker items={items} selected={edit.item_ids} onToggle={toggleItem} />
              </div>
              {edit.item_ids.length === 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  <div>
                    <label className="lair-label">Задание (текст)</label>
                    <input className="lair-input" value={edit.task} onChange={(e) => setEdit({ ...edit, task: e.target.value })} placeholder="Вышей узор" />
                  </div>
                  <div>
                    <label className="lair-label">Норма крестиков</label>
                    <input className="lair-input" type="text" inputMode="numeric" value={edit.crosses_norm}
                           onChange={(e) => setEdit({ ...edit, crosses_norm: Math.max(1, parseInt(e.target.value, 10) || 1) })} />
                  </div>
                </div>
              )}
              {edit.item_ids.length > 0 && (
                <>
                  <div style={{ marginBottom: 12 }}>
                    <label className="lair-label">Описание (показывается на экране подтверждения списания товара)</label>
                    <textarea className="lair-textarea" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })}
                              placeholder="Например: Ты насыпаешь корм в миску и малыш с аппетитом ест…" style={{ minHeight: 70 }} />
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <label className="lair-label">Надпись на кнопке подтверждения</label>
                    <input className="lair-input" value={edit.confirm_button_label} onChange={(e) => setEdit({ ...edit, confirm_button_label: e.target.value })}
                           placeholder="🎒 Использовать" />
                  </div>
                </>
              )}
            </>
          )}

          <div style={{ marginBottom: 12 }}>
            <label className="lair-label">Подсказка</label>
            <input className="lair-input" value={edit.hint} onChange={(e) => setEdit({ ...edit, hint: e.target.value })} placeholder="💡 Подсказка игроку" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '90px 90px 1fr', gap: 8, marginBottom: 12 }}>
            <div>
              <label className="lair-label">Таймаут, ч</label>
              <input className="lair-input" type="text" inputMode="numeric" value={edit.timeout_hours}
                     onChange={(e) => setEdit({ ...edit, timeout_hours: Math.max(0, parseInt(e.target.value, 10) || 0) })} />
            </div>
            <div>
              <label className="lair-label">мин</label>
              <input className="lair-input" type="text" inputMode="numeric" value={edit.timeout_minutes}
                     onChange={(e) => setEdit({ ...edit, timeout_minutes: Math.max(0, parseInt(e.target.value, 10) || 0) })} />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <label className="lair-file" style={{ margin: 0 }}>
                <input type="file" accept="image/*" style={{ display: 'none' }}
                       onChange={async (e) => { const f = e.target.files?.[0]; if (f) setEdit({ ...edit, image_path: await uploadImage(f) }); }} />
                {edit.image_path ? 'Заменить фото' : '📷 Фото действия'}
              </label>
              {edit.image_path && (
                <img src={`/dragons/api/static/images/${edit.image_path}?t=${Date.now()}`} alt=""
                     style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', marginLeft: 10, cursor: 'pointer' }}
                     onClick={() => window.open(`/dragons/api/static/images/${edit.image_path}`, '_blank')}
                     onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
              )}
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : '💾 Сохранить'}</button>
            <button className="lair-btn lair-btn-outline" onClick={() => nav(`/admin/epic/stages/${sid}`)}>Отмена</button>
          </div>
        </div>

        {isComposite && action.sub_actions !== undefined && (
          <div className="lair-card" style={{ maxWidth: 700 }}>
            <h3 style={{ color: 'var(--gold)', margin: '0 0 8px' }}>Поддействия</h3>
            <SubActionsEditor actionId={aid} subActions={action.sub_actions || []} axes={axes} reload={loadAction} setError={setError} sid={sid} aid={aid} />
          </div>
        )}

        {!isComposite && (
          <div className="lair-card" style={{ maxWidth: 700 }}>
            <h3 style={{ color: 'var(--gold)', margin: '0 0 8px' }}>Исход (мудлет характера)</h3>
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', flexWrap: 'wrap', marginBottom: 10 }}>
              <div style={{ width: 220 }}>
                <label className="lair-label">Ось характера</label>
                <select className="lair-input" value={edit.character_axis_id ?? ''}
                        onChange={(e) => { const v = e.target.value ? Number(e.target.value) : null; setEdit({ ...edit, character_axis_id: v }); saveOutcomeMeta({ character_axis_id: v }); }}>
                  <option value="">Без характера</option>
                  {axes.map((ax) => <option key={ax.id} value={ax.id}>{ax.positive_label} ⇄ {ax.negative_label}</option>)}
                </select>
              </div>
              <label className="lair-checkbox">
                <input type="checkbox" checked={edit.random_outcome}
                       onChange={(e) => { setEdit({ ...edit, random_outcome: e.target.checked }); saveOutcomeMeta({ random_outcome: e.target.checked }); }} />
                🎲 Случайный исход
              </label>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
              {edit.random_outcome
                ? 'Один из двух исходов выбирается случайно (с учётом характера).'
                : 'Выбирается исход, у которого загружена картинка. Если оба пустые — исход не показывается.'}
            </div>
            <ActionOutcomesEditor outcomes={action.outcomes || []} reload={loadAction} uploadImage={uploadImage} />
          </div>
        )}
      </div>
    </>
  );
}

function ItemPicker({ items, selected, onToggle }: { items: ShopItem[]; selected: number[]; onToggle: (id: number) => void }) {
  const [q, setQ] = useState('');
  const matched = items.filter((i) => i.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      {selected.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
          {selected.map((id) => {
            const it = items.find((x) => x.id === id);
            return it ? (
              <span key={id} className="lair-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'pointer', background: 'var(--accent-dark)' }}
                    onClick={() => onToggle(id)}>{it.name} ✕</span>
            ) : null;
          })}
        </div>
      )}
      <input className="lair-input" type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍 Поиск товаров…" style={{ marginBottom: 4 }} />
      <div style={{ maxHeight: 160, overflowY: 'auto', border: '1px solid var(--bronze)', borderRadius: 6, padding: 4 }}>
        {matched.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 13, padding: 4 }}>Ничего не найдено</span>}
        {matched.map((i) => (
          <label key={i.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', cursor: 'pointer', borderRadius: 4, background: selected.includes(i.id) ? 'rgba(153,102,255,0.15)' : 'transparent' }}>
            <input type="checkbox" checked={selected.includes(i.id)} onChange={() => onToggle(i.id)} />
            <span style={{ fontSize: 13 }}>{i.name}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function SubActionsEditor({ actionId, subActions, axes, reload, setError, sid, aid }: any) {
  const nav = useNavigate();
  const [subLabel, setSubLabel] = useState('');
  const [subAxisId, setSubAxisId] = useState<number | null>(null);

  const addSub = async () => {
    if (!subLabel.trim()) { setError('Впиши название'); return; }
    setError('');
    await client.post(`/admin/epic/actions/${actionId}/sub-actions`, { label: subLabel, character_axis_id: subAxisId, order_in_sub: subActions.length + 1 });
    setSubLabel(''); setSubAxisId(null);
    reload();
  };

  const delSub = async (id: number) => {
    if (!confirm('Удалить поддействие и все его шаги/исходы?')) return;
    await client.delete(`/admin/epic/sub-actions/${id}`);
    reload();
  };

  const axisName = (axisId: number | null) => {
    if (!axisId) return '—';
    return axes.find((ax: Axis) => ax.id === axisId)?.positive_label || '—';
  };

  return (
    <div>
      {subActions.map((sa: SubAction) => (
        <div key={sa.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ color: 'var(--gold)', width: 24, fontSize: 13 }}>#{sa.order_in_sub}</span>
          <span style={{ fontWeight: 600, flex: 1, fontSize: 14 }}>{sa.label}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 100 }}>🎭 {axisName(sa.character_axis_id)}</span>
          <span style={{ fontSize: 12, color: 'var(--parchment-dim)' }}>{sa.steps?.length || 0} шагов</span>
          <button className="lair-btn lair-btn-sm lair-btn-outline"
                  onClick={() => nav(`/admin/epic/stages/${sid}/actions/${aid}/sub-actions/${sa.id}`)}
                  style={{ fontSize: 12 }}>✏ Редактировать</button>
          <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => delSub(sa.id)} style={{ fontSize: 11 }}>✕</button>
        </div>
      ))}
      {subActions.length === 0 && <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Нет поддействий.</div>}
      <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', flexWrap: 'wrap', borderTop: '1px solid var(--bronze)', paddingTop: 10, marginTop: 4 }}>
        <input className="lair-input" value={subLabel} onChange={(e) => setSubLabel(e.target.value)} placeholder="Название поддействия" style={{ flex: 1, minWidth: 160 }} />
        <select className="lair-input" value={subAxisId ?? ''} onChange={(e) => setSubAxisId(e.target.value ? Number(e.target.value) : null)} style={{ width: 170, fontSize: 12 }}>
          <option value="">Без характера</option>
          {axes.map((ax: Axis) => <option key={ax.id} value={ax.id}>{ax.positive_label} ⇄ {ax.negative_label}</option>)}
        </select>
        <button className="lair-btn" onClick={addSub}>+ Добавить</button>
      </div>
    </div>
  );
}

function ActionOutcomesEditor({ outcomes, reload, uploadImage }: any) {
  const updateOutcome = async (id: number, data: any) => { await client.put(`/admin/epic/actions/outcomes/${id}`, data); reload(); };

  if (!outcomes || outcomes.length === 0) {
    return <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Исходы появятся после сохранения действия.</div>;
  }

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
                     placeholder="Например: Сыт и счастлив!" style={{ height: 32, fontSize: 13 }} />
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

export default EpicActionEditor;