import { useEffect, useState } from 'react';
import client from '../../api/client';

interface ErrorLog {
  id: number;
  source: string;
  error_type: string;
  message: string;
  traceback_text: string;
  user_id: number | null;
  created_at: string;
}

function LogsList() {
  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [load, setLoad] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const perPage = 50;

  const fetchLogs = (p: number) => {
    setLoad(true);
    client.get('/admin/logs', { params: { page: p, per_page: perPage } })
      .then((r) => {
        setLogs(r.data.logs);
        setTotal(r.data.total);
        setPage(r.data.page);
      })
      .finally(() => setLoad(false));
  };

  useEffect(() => { fetchLogs(1); }, []);

  const totalPages = Math.ceil(total / perPage);
  const formatDate = (s: string) => s ? new Date(s).toLocaleString('ru-RU') : '—';

  return (
    <>
      <div className="lair-header"><h2>📋 Логи ошибок</h2></div>
      <div className="lair-content">
        {load ? (
          <div className="lair-skeleton" />
        ) : (
          <>
            <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
              Всего: {total}
            </div>
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="lair-table">
                <thead>
                  <tr>
                    <th style={{ width: 50 }}>ID</th>
                    <th style={{ width: 70 }}>Источник</th>
                    <th style={{ width: 100 }}>Тип</th>
                    <th>Сообщение</th>
                    <th style={{ width: 80 }}>VK ID</th>
                    <th style={{ width: 140 }}>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <>
                      <tr
                        key={log.id}
                        className="clickable"
                        onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td>{log.id}</td>
                        <td><span className="lair-badge">{log.source}</span></td>
                        <td style={{ color: 'var(--fire)', fontSize: 13 }}>{log.error_type}</td>
                        <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {log.message}
                        </td>
                        <td>{log.user_id ?? '—'}</td>
                        <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(log.created_at)}</td>
                      </tr>
                      {expanded === log.id && (
                        <tr key={`${log.id}-tb`}>
                          <td colSpan={6} style={{ padding: 12, background: 'rgba(0,0,0,0.3)' }}>
                            <pre style={{ margin: 0, fontSize: 12, color: 'var(--parchment-dim)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 400, overflowY: 'auto' }}>
                              {log.traceback_text || log.message}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Ошибок нет</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
                <button
                  className="lair-btn lair-btn-sm lair-btn-outline"
                  disabled={page <= 1}
                  onClick={() => fetchLogs(page - 1)}
                >← Назад</button>
                <span style={{ color: 'var(--parchment-dim)', fontSize: 14, padding: '4px 12px' }}>
                  {page} / {totalPages}
                </span>
                <button
                  className="lair-btn lair-btn-sm lair-btn-outline"
                  disabled={page >= totalPages}
                  onClick={() => fetchLogs(page + 1)}
                >Вперёд →</button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

export default LogsList;
