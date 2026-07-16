import { useEffect, useState } from 'react';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

interface PaymentOrder {
  id: number;
  vk_id: number;
  set_id: number | null;
  set_name: string;
  amount_rub: number;
  quantity: number;
  price_per_pin: number;
  robokassa_inv_id: number | null;
  status: string;
  dragon_ids: number[];
  notified: boolean;
  created_at: string;
  completed_at: string | null;
}

const COLUMNS: Column<PaymentOrder>[] = [
  { key: 'id', label: '№', value: (o) => String(o.id), sortValue: (o) => o.id, width: 40 },
  { key: 'vk_id', label: 'VK ID', value: (o) => String(o.vk_id), sortValue: (o) => o.vk_id, filter: 'text' },
  { key: 'set_name', label: 'Набор', value: (o) => o.set_name || `#${o.set_id}`, filter: 'text' },
  { key: 'quantity', label: 'Кол-во', value: (o) => String(o.quantity), sortValue: (o) => o.quantity },
  { key: 'amount', label: 'Сумма', value: (o) => `${(o.amount_rub / 100).toFixed(2)}₽`, sortValue: (o) => o.amount_rub },
  { key: 'price_per_pin', label: 'Цена/PIN', value: (o) => `${(o.price_per_pin / 100).toFixed(2)}₽`, sortValue: (o) => o.price_per_pin },
  { key: 'status', label: 'Статус', value: (o) => (o.status === 'success' ? 'Успех' : o.status === 'pending' ? 'Ожидание' : 'Отказ'), filter: 'select' },
  { key: 'notified', label: 'Уведом.', value: (o) => (o.notified ? 'Да' : 'Нет'), filter: 'select' },
  { key: 'created_at', label: 'Создан', value: (o) => o.created_at?.slice(0, 16).replace('T', ' ') || '—', sortValue: (o) => o.created_at || '' },
  { key: 'completed_at', label: 'Завершён', value: (o) => o.completed_at?.slice(0, 16).replace('T', ' ') || '—', sortValue: (o) => o.completed_at || '' },
];

function FinanceOrders({ hideHeader }: { hideHeader?: boolean }) {
  const [items, setItems] = useState<PaymentOrder[]>([]);
  const [load, setLoad] = useState(true);
  const t = useTableControls(items, COLUMNS);

  const reload = () => client.get('/admin/payment-orders')
    .then((r) => setItems(r.data.items))
    .finally(() => setLoad(false));

  useEffect(() => { reload(); }, []);

  const statusLabel = (s: string) => {
    switch (s) {
      case 'success': return { text: '✅ Успех', color: 'var(--success)' };
      case 'pending': return { text: '⏳ Ожидание', color: 'var(--ember)' };
      case 'fail': return { text: '❌ Отказ', color: 'var(--fire)' };
      default: return { text: s, color: 'var(--parchment-faded)' };
    }
  };

  return (
    <>
      {!hideHeader && <div className="lair-header"><h2>💳 Платежи пользователей</h2></div>}
      <div className="lair-content">
        {load ? <div className="lair-skeleton" /> : (
          <>
            <TableToolbar controls={t} placeholder="🔍 Поиск по VK ID или названию набора..." />
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="lair-table">
                <DataTableHead controls={t} allRows={items} />
                <tbody>
                  {t.rows.map((o) => {
                    const st = statusLabel(o.status);
                    return (
                      <tr key={o.id} style={{ opacity: o.status === 'fail' ? 0.6 : 1 }}>
                        <td>{o.id}</td>
                        <td><a href={`https://vk.ru/id${o.vk_id}`} target="_blank" rel="noreferrer" style={{ color: 'var(--gold)' }}>{o.vk_id}</a></td>
                        <td style={{ fontWeight: 600 }}>{o.set_name || `Набор #${o.set_id}`}</td>
                        <td>{o.quantity}</td>
                        <td style={{ color: 'var(--gold)', fontWeight: 600 }}>{(o.amount_rub / 100).toFixed(2)}₽</td>
                        <td style={{ color: 'var(--parchment-dim)' }}>{(o.price_per_pin / 100).toFixed(2)}₽</td>
                        <td style={{ color: st.color, fontWeight: 600 }}>{st.text}</td>
                        <td>{o.notified ? '✅' : '❌'}</td>
                        <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{o.created_at?.slice(0, 16).replace('T', ' ') || '—'}</td>
                        <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{o.completed_at?.slice(0, 16).replace('T', ' ') || '—'}</td>
                      </tr>
                    );
                  })}
                  {t.rows.length === 0 && <tr><td colSpan={10} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Платежей пока нет</td></tr>}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

export default FinanceOrders;
