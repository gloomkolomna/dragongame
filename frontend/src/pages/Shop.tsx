import { useEffect, useState } from 'react';
import { useVkBridge } from '../context/VkBridgeContext';
import client from '../api/client';
import { mediaUrl } from '../api/media';

interface Item { id: number; name: string; description: string; cost_stitches: number; image_path: string; is_consumable: boolean; is_optional: boolean; owned: boolean; }
interface InvItem { id: number; name: string; description: string; image_path: string; quantity: number; }

function Shop() {
  const { vkUserId, loading: bl } = useVkBridge();
  const [items, setItems] = useState<Item[]>([]);
  const [stageKey, setStageKey] = useState<string | null>(null);
  const [inventory, setInventory] = useState<InvItem[]>([]);
  const [balance, setBalance] = useState(0);
  const [load, setLoad] = useState(true);

  useEffect(() => {
    if (bl || !vkUserId) { setLoad(false); return; }
    Promise.all([
      client.get(`/collection/${vkUserId}/shop`),
      client.get(`/collection/${vkUserId}/inventory`),
      client.get(`/collection/${vkUserId}/balance`),
    ]).then(([s, inv, bal]) => {
      setItems(s.data.items);
      setStageKey(s.data.stage_key);
      setInventory(inv.data);
      setBalance(bal.data.stitches_balance);
    }).catch(() => {}).finally(() => setLoad(false));
  }, [vkUserId, bl]);

  if (bl || load) return <div style={{ padding: 40, textAlign: 'center' }}><div className="lair-skeleton" style={{ height: 160 }} /></div>;

  return (
    <div style={{ padding: '12px 10px', maxWidth: 560, margin: '0 auto' }}>
      <div className="lair-card" style={{ marginBottom: 12, textAlign: 'center' }}>
        <div style={{ fontSize: 18, color: 'var(--gold)', fontWeight: 600 }}>✚ Копилка: {balance}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Покупка товаров — в боте.</div>
      </div>

      <div className="lair-card" style={{ marginBottom: 12 }}>
        <h4 style={{ color: 'var(--gold)', marginTop: 0 }}>🛒 Товары стадии</h4>
        {!stageKey ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Магазин откроется с эпическим драконом.</div>
        ) : items.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>На этой стадии пока нет товаров.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {items.map((it) => (
              <div key={it.id} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: 8, borderRadius: 8, background: 'var(--bg-card)' }}>
                {it.image_path && <img src={mediaUrl(it.image_path)} alt="" style={{ width: 44, height: 44, objectFit: 'contain', borderRadius: 6 }} />}
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600 }}>{it.name} {it.owned && '✅'}</div>
                  {it.description && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{it.description}</div>}
                </div>
                <div style={{ color: 'var(--gold)', fontWeight: 600 }}>{it.cost_stitches}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="lair-card">
        <h4 style={{ color: 'var(--gold)', marginTop: 0 }}>🎒 Инвентарь</h4>
        {inventory.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Пусто.</div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {inventory.map((it) => (
              <span key={it.id} className="lair-badge">{it.name}{it.quantity > 1 ? ` ×${it.quantity}` : ''}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Shop;
