import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

interface ShopItem {
  id: number; name: string; description: string; cost_stitches: number;
  image_path: string; sort_order: number; is_active: boolean; is_optional: boolean;
  dragon_names: string[];
}

const COLUMNS: Column<ShopItem>[] = [
  { key: 'image', label: '', width: 44 },
  { key: 'name', label: 'Название', value: (i) => i.name, filter: 'text' },
  { key: 'description', label: 'Описание', value: (i) => i.description, filter: 'text' },
  { key: 'dragon', label: 'Дракон', value: (i) => (i.dragon_names || []).join(', '), filterValues: (i) => i.dragon_names || [], filter: 'select' },
  { key: 'cost', label: 'Цена', value: (i) => String(i.cost_stitches), sortValue: (i) => i.cost_stitches },
  { key: 'optional', label: 'Обязат.', value: (i) => (i.is_optional ? 'Необязательный' : 'Обязательный'), filter: 'select' },
  { key: 'active', label: 'Акт.', value: (i) => (i.is_active ? 'Активен' : 'Скрыт'), filter: 'select', width: 90 },
  { key: 'actions', label: '', width: 120 },
];

function ShopList() {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();
  const t = useTableControls(items, COLUMNS);

  const reload = () => client.get('/admin/shop-items').then((r) => setItems(r.data)).finally(() => setLoad(false));
  useEffect(() => { reload(); }, []);

  const del = async (id: number) => {
    if (!window.confirm('Удалить товар?')) return;
    await client.delete(`/admin/shop-items/${id}`);
    setItems((prev) => prev.filter((x) => x.id !== id));
  };

  return (
    <>
      <div className="lair-header">
        <h2>🛒 Магазин</h2>
        <button className="lair-btn" style={{ marginLeft: 'auto' }} onClick={() => nav('/admin/shop/new')}>+ Создать</button>
      </div>
      <div className="lair-content">
        <TableToolbar controls={t} />
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          {load ? <div className="lair-skeleton" /> : (
            <table className="lair-table">
              <DataTableHead controls={t} allRows={items} />
              <tbody>{t.rows.map((it) => (
                <tr key={it.id} className="clickable" onClick={() => nav(`/admin/shop/${it.id}/edit`)}>
                  <td>{it.image_path ? <img src={`/dragons/api/static/images/${it.image_path}`} alt="" style={{ width: 30, height: 30, objectFit: 'contain' }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} /> : '—'}</td>
                  <td style={{ fontWeight: 600 }}>{it.name}</td>
                  <td style={{ color: 'var(--parchment-dim)', fontSize: 13 }}>{it.description}</td>
                  <td style={{ fontSize: 13 }}>{(it.dragon_names || []).length ? it.dragon_names.join(', ') : '—'}</td>
                  <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{it.cost_stitches} ✚</td>
                  <td style={{ fontSize: 13 }}>{it.is_optional ? '⏭ необяз.' : '✅ обяз.'}</td>
                  <td>{it.is_active ? '✅' : '❌'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); nav(`/admin/shop/${it.id}/edit`); }}>✎</button>
                      <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={(e) => { e.stopPropagation(); del(it.id); }}>✕</button>
                    </div>
                  </td>
                </tr>
              ))}
              {t.rows.length === 0 && <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Ничего не найдено</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default ShopList;
