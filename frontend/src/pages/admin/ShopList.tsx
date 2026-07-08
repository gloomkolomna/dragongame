import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import client from '../../api/client';

interface ShopItem {
  id: number; name: string; description: string; cost_stitches: number;
  image_path: string; sort_order: number; is_active: boolean;
}

function ShopList() {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [load, setLoad] = useState(true);
  const nav = useNavigate();

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
        <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
          {load ? <div className="lair-skeleton" /> : (
            <table className="lair-table">
              <thead><tr><th style={{ width: 44 }}></th><th>Название</th><th>Описание</th><th>Цена</th><th style={{ width: 50 }}>Акт.</th><th style={{ width: 120 }}></th></tr></thead>
              <tbody>{items.map((it) => (
                <tr key={it.id} className="clickable" onClick={() => nav(`/admin/shop/${it.id}/edit`)}>
                  <td>{it.image_path ? <img src={`/dragons/api/static/images/${it.image_path}`} alt="" style={{ width: 30, height: 30, objectFit: 'contain' }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} /> : '—'}</td>
                  <td style={{ fontWeight: 600 }}>{it.name}</td>
                  <td style={{ color: 'var(--parchment-dim)', fontSize: 13 }}>{it.description}</td>
                  <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{it.cost_stitches} ✚</td>
                  <td>{it.is_active ? '✅' : '❌'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="lair-btn lair-btn-sm lair-btn-outline" onClick={(e) => { e.stopPropagation(); nav(`/admin/shop/${it.id}/edit`); }}>✎</button>
                      <button className="lair-btn lair-btn-sm lair-btn-danger" onClick={(e) => { e.stopPropagation(); del(it.id); }}>✕</button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 16 }}>Товаров пока нет</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

export default ShopList;
