import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import client from '../../api/client';

interface Stage { id: number; stage_number: number; name: string; }
interface Action { id: number; dragon_id: number; stage_id: number; action_label: string; order_in_cycle: number; task: string; hint: string; crosses_norm: number; image_path: string; timeout_hours: number; timeout_minutes: number; item_ids: number[]; }
interface ShopItem { id: number; name: string; }
interface Species { id: number; name: string; }

function EpicStageEditor() {
  const { stageId } = useParams<{ stageId: string }>();
  const sid = Number(stageId);
  const nav = useNavigate();
  const [stage, setStage] = useState<Stage | null>(null);
  const [items, setItems] = useState<ShopItem[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [species, setSpecies] = useState<Species[]>([]);
  const [did, setDid] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [zoom, setZoom] = useState<string | null>(null);

  const loadActions = () => {
    if (!did) { setActions([]); return Promise.resolve(); }
    return client.get(`/admin/epic/species/${did}/stages/${sid}/actions`).then((r) => setActions(r.data));
  };

  useEffect(() => {
    client.get('/admin/epic/stages').then((r) => setStage(r.data.find((s: Stage) => s.id === sid) || null));
    client.get('/admin/shop-items').then((r) => setItems(r.data));
    client.get('/admin/epic/species').then((r) => {
      setSpecies(r.data);
      setDid((prev) => prev ?? (r.data[0]?.id ?? null));
    });
  }, [sid]);

  useEffect(() => { loadActions(); }, [sid, did]);

  return (
    <>
      <div className="lair-header">
        <button className="lair-btn lair-btn-outline lair-btn-sm" onClick={() => nav('/admin/epic')}>← Назад</button>
        <h2 style={{ marginLeft: 12 }}>⚙ {stage ? `Стадия ${stage.stage_number}: ${stage.name}` : 'Стадия'}</h2>
        <button className="lair-btn lair-btn-outline lair-btn-sm" style={{ marginLeft: 'auto' }}
                onClick={() => nav(`/admin/epic/stages/${sid}/edit`)}>✎ Редактировать этап</button>
      </div>
      <div className="lair-content">
        {error && <div style={{ padding: '8px 12px', marginBottom: 12, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        <div className="lair-card" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <label className="lair-label" style={{ margin: 0 }}>Эпический дракон:</label>
          <select className="lair-input" value={did ?? ''} onChange={(e) => setDid(Number(e.target.value) || null)} style={{ maxWidth: 260 }}>
            {species.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Действия уникальны для каждого дракона</span>
        </div>
        {species.length === 0 ? (
          <div className="lair-card" style={{ color: 'var(--text-muted)', fontSize: 14 }}>Сначала создай эпический вид дракона.</div>
        ) : (
          <ActionsSection did={did} sid={sid} actions={actions} items={items} reload={loadActions} setError={setError} setZoom={setZoom} />
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
                    onClick={() => onToggle(id)}>
                {it.name} ✕
              </span>
            ) : null;
          })}
        </div>
      )}
      <input className="lair-input" type="text" value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="🔍 Поиск товаров…" style={{ marginBottom: 4 }} />
      {items.length > 0 ? (
        <div style={{ maxHeight: 160, overflowY: 'auto', border: '1px solid var(--bronze)', borderRadius: 6, padding: 4 }}>
          {matched.length === 0 && <span style={{ color: 'var(--text-muted)', fontSize: 13, padding: 4 }}>Ничего не найдено</span>}
          {matched.map((i) => (
            <label key={i.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', cursor: 'pointer', borderRadius: 4, background: selected.includes(i.id) ? 'rgba(153,102,255,0.15)' : 'transparent' }}>
              <input type="checkbox" checked={selected.includes(i.id)} onChange={() => onToggle(i.id)} />
              <span style={{ fontSize: 13 }}>{i.name}</span>
            </label>
          ))}
        </div>
      ) : (
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Сначала добавь товары в магазин</span>
      )}
    </div>
  );
}

function ActionsSection({ did, sid, actions, items, reload, setError, setZoom }: any) {
  const [rows, setRows] = useState<Action[]>([]);
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [edit, setEdit] = useState<any>({ action_label: '', task: '', crosses_norm: 1000, hint: '', image_path: '', timeout_hours: 24, timeout_minutes: 0, item_ids: [] as number[] });

  const [label, setLabel] = useState('');
  const [task, setTask] = useState('');
  const [crossesNorm, setCrossesNorm] = useState(1000);
  const [selItems, setSelItems] = useState<number[]>([]);
  const [hint, setHint] = useState('');
  const [addTimeoutH, setAddTimeoutH] = useState(24);
  const [addTimeoutM, setAddTimeoutM] = useState(0);
  const [addImagePath, setAddImagePath] = useState('');

  const uploadImage = async (file: File): Promise<string> => {
    const form = new FormData();
    form.append('image', file);
    const r = await client.post('/admin/upload-image', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return r.data.path;
  };

  useEffect(() => { setRows(actions); }, [actions]);

  const nextOrder = (rows.length ? Math.max(...rows.map((a) => a.order_in_cycle)) : 0) + 1;
  const itemName = (id: number) => items.find((i: ShopItem) => i.id === id)?.name || `#${id}`;
  const toggleAdd = (id: number) => setSelItems((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  const toggleEdit = (id: number) => setEdit((e: any) => ({ ...e, item_ids: e.item_ids.includes(id) ? e.item_ids.filter((x: number) => x !== id) : [...e.item_ids, id] }));

  const add = async () => {
    if (!label.trim()) { setError('Впиши название действия'); return; }
    if (!did) { setError('Выбери эпического дракона'); return; }
    setError('');
    await client.post(`/admin/epic/species/${did}/stages/${sid}/actions`, { action_label: label, task, item_ids: selItems, order_in_cycle: nextOrder, hint, crosses_norm: crossesNorm, image_path: addImagePath, timeout_hours: addTimeoutH, timeout_minutes: addTimeoutM });
    setLabel(''); setTask(''); setHint(''); setSelItems([]); setCrossesNorm(1000); setAddTimeoutH(24); setAddTimeoutM(0); setAddImagePath('');
    reload();
  };
  const del = async (id: number) => { await client.delete(`/admin/epic/actions/${id}`); reload(); };

  const startEdit = (a: Action) => {
    setEditId(a.id);
    setEdit({ action_label: a.action_label, task: a.task || '', crosses_norm: a.crosses_norm, hint: a.hint, image_path: a.image_path || '', timeout_hours: a.timeout_hours ?? 24, timeout_minutes: a.timeout_minutes ?? 0, item_ids: [...(a.item_ids || [])] });
  };
  const saveEdit = async () => {
    if (!edit.action_label.trim()) { setError('Впиши название действия'); return; }
    setError('');
    await client.put(`/admin/epic/actions/${editId}`, {
      action_label: edit.action_label, task: edit.task, crosses_norm: edit.crosses_norm, hint: edit.hint, item_ids: edit.item_ids, image_path: edit.image_path, timeout_hours: edit.timeout_hours, timeout_minutes: edit.timeout_minutes,
    });
    setEditId(null);
    reload();
  };

  const persistOrder = async (list: Action[]) => {
    await Promise.all(list.map((a, i) =>
      a.order_in_cycle === i + 1 ? Promise.resolve() : client.put(`/admin/epic/actions/${a.id}`, { order_in_cycle: i + 1 })
    ));
    reload();
  };
  const onDrop = (targetIdx: number) => {
    if (dragIdx === null || dragIdx === targetIdx) { setDragIdx(null); return; }
    const list = [...rows];
    const [moved] = list.splice(dragIdx, 1);
    list.splice(targetIdx, 0, moved);
    setRows(list);
    setDragIdx(null);
    persistOrder(list);
  };

  return (
    <div className="lair-card">
      <h4 style={{ color: 'var(--gold)', margin: '0 0 4px' }}>Действия ухода (цикл)</h4>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>Действия выполняются по порядку (перетаскивание ⠿). Если указаны товары — игрок нажимает «Использовать» и товары списываются. Если товаров нет — игрок сдаёт крестики (задание + норма). После каждого действия — таймаут.</div>

      {rows.map((a: Action, idx: number) => (
        <div key={a.id}
             draggable={editId === null}
             onDragStart={() => setDragIdx(idx)}
             onDragOver={(e) => e.preventDefault()}
             onDrop={() => onDrop(idx)}
             style={{ padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.05)', opacity: dragIdx === idx ? 0.4 : 1 }}>
          {editId === a.id ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8 }}>
                <input className="lair-input" value={edit.action_label} onChange={(e) => setEdit({ ...edit, action_label: e.target.value })} placeholder="Название" />
                <input className="lair-input" type="text" inputMode="numeric" value={edit.crosses_norm} onChange={(e) => setEdit({ ...edit, crosses_norm: Math.max(1, parseInt(e.target.value, 10) || 1) })} />
              </div>
              {edit.item_ids && edit.item_ids.length > 0 ? (
                <ItemPicker items={items} selected={edit.item_ids} onToggle={toggleEdit} />
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <input className="lair-input" value={edit.task} onChange={(e) => setEdit({ ...edit, task: e.target.value })} placeholder="Задание (текст)" />
                  <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <input className="lair-input" type="text" inputMode="numeric" value={edit.timeout_hours} onChange={(e) => setEdit({ ...edit, timeout_hours: Math.max(0, parseInt(e.target.value, 10) || 0) })} placeholder="ч" style={{ width: '50%' }} />
                    <span style={{ color: 'var(--parchment-dim)', fontSize: 12 }}>ч</span>
                    <input className="lair-input" type="text" inputMode="numeric" value={edit.timeout_minutes} onChange={(e) => setEdit({ ...edit, timeout_minutes: Math.max(0, parseInt(e.target.value, 10) || 0) })} placeholder="мин" style={{ width: '50%' }} />
                    <span style={{ color: 'var(--parchment-dim)', fontSize: 12 }}>мин</span>
                  </div>
                </div>
              )}
              <input className="lair-input" value={edit.hint} onChange={(e) => setEdit({ ...edit, hint: e.target.value })} placeholder="Подсказка (необязательно)" />
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label className="lair-file" style={{ margin: 0 }}><input type="file" accept="image/*" style={{ display: 'none' }} onChange={async (e) => { const f = e.target.files?.[0]; if (f) setEdit({ ...edit, image_path: await uploadImage(f) }); }} />{edit.image_path ? 'Заменить...' : 'Фото...'}</label>
                {edit.image_path && (
                  <img src={`/dragons/api/static/images/${edit.image_path}?t=${Date.now()}`} alt=""
                       onClick={() => setZoom(`/dragons/api/static/images/${edit.image_path}`)}
                       style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                       onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                )}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="lair-btn lair-btn-sm" onClick={saveEdit}>💾 Сохранить</button>
                <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => setEditId(null)}>Отмена</button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ cursor: 'grab', color: 'var(--parchment-faded)' }} title="Перетащить">⠿</span>
              <span style={{ color: 'var(--gold)', width: 28 }}>#{a.order_in_cycle}</span>
              <span style={{ fontWeight: 600, minWidth: 120 }}>{a.action_label}</span>
              {a.item_ids && a.item_ids.length > 0 ? (
                <span style={{ color: 'var(--parchment-dim)', fontSize: 12 }}>
                  📦 {a.item_ids.map(itemName).join(', ')}
                </span>
              ) : (
                <span style={{ color: 'var(--gold)', fontSize: 12 }}>{a.crosses_norm} ✚</span>
              )}
              <span style={{ color: 'var(--parchment-faded)', fontSize: 12 }}>
                ⏳ {a.timeout_hours ?? 24}ч {a.timeout_minutes ?? 0}м
              </span>
              {a.image_path && (
                <img src={`/dragons/api/static/images/${a.image_path}?t=${Date.now()}`} alt=""
                     onClick={() => setZoom(`/dragons/api/static/images/${a.image_path}`)}
                     style={{ width: 36, height: 36, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                     onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
              )}
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={() => startEdit(a)}>✎</button>
                <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={() => del(a.id)}>✕</button>
              </div>
            </div>
          )}
        </div>
      ))}

      <div style={{ borderTop: '1px solid var(--bronze)', paddingTop: 12, marginTop: 12 }}>
        <div style={{ fontWeight: 600, color: 'var(--accent-gold-light)', marginBottom: 8 }}>Добавить действие (порядок #{nextOrder})</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8, marginBottom: 8 }}>
          <div><label className="lair-label">Название (кнопка игроку)</label>
            <input className="lair-input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Кормить" /></div>
        </div>
        <div style={{ marginBottom: 8 }}>
          <label className="lair-label">Нужные товары (можно несколько) — если пусто, действие считается заданием с крестиками</label>
          <ItemPicker items={items} selected={selItems} onToggle={toggleAdd} />
        </div>
        {selItems.length === 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            <div><label className="lair-label">Задание (текст)</label>
              <input className="lair-input" value={task} onChange={(e) => setTask(e.target.value)} placeholder="Вышей узор из 1000 крестиков" /></div>
            <div><label className="lair-label">Норма крестиков</label>
              <input className="lair-input" type="text" inputMode="numeric" value={crossesNorm} onChange={(e) => setCrossesNorm(Math.max(1, parseInt(e.target.value, 10) || 1))} /></div>
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 90px 90px', gap: 8, marginBottom: 8 }}>
          <div><label className="lair-label">Подсказка (необязательно)</label>
            <input className="lair-input" value={hint} onChange={(e) => setHint(e.target.value)} placeholder="💡 Вкусняшка для дракона" /></div>
          <div><label className="lair-label">Таймаут, ч</label>
            <input className="lair-input" type="text" inputMode="numeric" value={addTimeoutH} onChange={(e) => setAddTimeoutH(Math.max(0, parseInt(e.target.value, 10) || 0))} /></div>
          <div><label className="lair-label">мин</label>
            <input className="lair-input" type="text" inputMode="numeric" value={addTimeoutM} onChange={(e) => setAddTimeoutM(Math.max(0, parseInt(e.target.value, 10) || 0))} /></div>
        </div>
        <div style={{ marginBottom: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label className="lair-file" style={{ margin: 0 }}><input type="file" accept="image/*" style={{ display: 'none' }} onChange={async (e) => { const f = e.target.files?.[0]; if (f) setAddImagePath(await uploadImage(f)); }} />{addImagePath ? 'Заменить...' : 'Фото действия...'}</label>
          {addImagePath && (
            <img src={`/dragons/api/static/images/${addImagePath}?t=${Date.now()}`} alt=""
                 onClick={() => setZoom(`/dragons/api/static/images/${addImagePath}`)}
                 style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--bronze)', cursor: 'pointer' }}
                 onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
          )}
        </div>
        <button className="lair-btn" onClick={add}>+ Добавить действие</button>
      </div>
    </div>
  );
}

export default EpicStageEditor;
