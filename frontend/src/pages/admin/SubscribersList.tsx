import { useState, useCallback } from 'react';
import client from '../../api/client';
import { useTableControls, type Column } from '../../components/admin/useTableControls';
import { DataTableHead, TableToolbar } from '../../components/admin/DataTable';

const GROUP_ID = 239999455;

interface SubItem {
  vk_id: number;
  first_name: string;
  last_name: string;
  kind: string;
}

interface AbsentData {
  subscribers_total: number;
  not_written_total: number;
  no_dragons_total: number;
  items: SubItem[];
}

const KIND_LABELS: Record<string, string> = {
  not_written: 'Не писали боту',
  no_dragons: 'База: 0 драконов',
};

const COLUMNS: Column<SubItem>[] = [
  { key: 'kind', label: 'Статус', value: (r) => KIND_LABELS[r.kind] || r.kind, filter: 'select', options: ['Не писали боту', 'База: 0 драконов'] },
  { key: 'name', label: 'ФИО', value: (r) => [r.first_name, r.last_name].filter(Boolean).join(' '), filter: 'text' },
  { key: 'vk_id', label: 'VK ID', value: (r) => String(r.vk_id), sortValue: (r) => r.vk_id, filter: 'text' },
  { key: 'chat', label: 'Чат' },
];

function SubscribersList() {
  const [data, setData] = useState<AbsentData | null>(null);
  const [load, setLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const t = useTableControls(data?.items ?? [], COLUMNS);

  const request = useCallback(() => {
    setLoad(true);
    setError(null);
    client.get('/admin/subscribers/absent', { timeout: 60000 })
      .then((r) => setData(r.data))
      .catch((e: any) => setError(e?.response?.data?.detail || 'Не удалось получить список из VK'))
      .finally(() => setLoad(false));
  }, []);

  const fullName = (r: SubItem) => [r.first_name, r.last_name].filter(Boolean).join(' ') || `id${r.vk_id}`;

  return (
    <>
      <div className="lair-header"><h2>👥 Подписчики группы</h2></div>
      <div className="lair-content">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <button className="lair-btn" onClick={request} disabled={load} style={{ minWidth: 180 }}>
            {load ? 'Запрос...' : data ? '🔄 Обновить' : 'Запросить'}
          </button>
          {data && !load && (
            <span style={{ color: 'var(--parchment-faded)', fontSize: 14 }}>
              Подписчиков: {data.subscribers_total} · Не писали боту: {data.not_written_total} · В базе без драконов: {data.no_dragons_total}
            </span>
          )}
        </div>
        {error && (
          <div className="lair-card" style={{ borderLeft: '3px solid var(--fire)', color: '#d474a0', fontWeight: 600, marginBottom: 16 }}>
            {error}
          </div>
        )}
        {load ? (
          <div className="lair-skeleton" />
        ) : data ? (
          <>
            <TableToolbar controls={t} />
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <div className="lair-table-responsive">
                <table className="lair-table">
                  <DataTableHead controls={t} allRows={data.items} />
                  <tbody>
                    {t.rows.map((r) => (
                      <tr key={r.vk_id}>
                        <td style={{ whiteSpace: 'nowrap', fontWeight: 600, color: r.kind === 'not_written' ? '#d474a0' : 'var(--gold)' }}>
                          {KIND_LABELS[r.kind] || r.kind}
                        </td>
                        <td style={{ fontWeight: 600 }}>
                          <a href={`https://vk.ru/id${r.vk_id}`} target="_blank" rel="noreferrer" style={{ color: 'var(--gold)' }}>
                            {fullName(r)}
                          </a>
                        </td>
                        <td>{r.vk_id}</td>
                        <td>
                          <a href={`https://vk.ru/gim${GROUP_ID}?sel=${r.vk_id}`} target="_blank" rel="noreferrer" className="lair-btn lair-btn-sm lair-btn-outline">
                            💬 Чат
                          </a>
                        </td>
                      </tr>
                    ))}
                    {t.rows.length === 0 && (
                      <tr><td colSpan={4} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Все подписчики играют 🎉</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          !error && (
            <div className="lair-card" style={{ color: 'var(--parchment-faded)' }}>
              Нажмите «Запросить», чтобы получить текущих подписчиков группы из VK и сравнить с базой игроков.
            </div>
          )
        )}
      </div>
    </>
  );
}

export default SubscribersList;
