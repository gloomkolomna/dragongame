import { useEffect, useState, useCallback } from 'react';
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

type Tab = 'db' | 'api';

interface ApiLogState {
  lines: string[];
  total: number;
  page: number;
}

function LogsList() {
  const [tab, setTab] = useState<Tab>('db');
  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [load, setLoad] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const perPage = 50;

  const [api, setApi] = useState<ApiLogState>({ lines: [], total: 0, page: 1 });

  const fetchDbLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs', { params: { page: p, per_page: perPage } })
      .then((r) => {
        setLogs(r.data.logs);
        setTotal(r.data.total);
        setPage(r.data.page);
      })
      .finally(() => setLoad(false));
  }, []);

  const fetchApiLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs/api', { params: { page: p, per_page: perPage } })
      .then((r) => {
        setApi({ lines: r.data.lines, total: r.data.total, page: r.data.page });
      })
      .finally(() => setLoad(false));
  }, []);

  useEffect(() => { fetchDbLogs(1); }, [fetchDbLogs]);

  const switchTab = (t: Tab) => {
    setTab(t);
    setExpanded(null);
    if (t === 'api' && api.lines.length === 0) fetchApiLogs(1);
  };

  const totalPages = Math.ceil((tab === 'db' ? total : api.total) / perPage);
  const formatDate = (s: string) => s ? new Date(s).toLocaleString('ru-RU') : '—';

  const goPage = (p: number) => {
    if (tab === 'db') fetchDbLogs(p);
    else fetchApiLogs(p);
  };

  return (
    <>
      <div className="lair-header" style={{ flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
        <h2 style={{ flexShrink: 0 }}>📋 Логи</h2>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            className={tab === 'db' ? 'lair-btn' : 'lair-btn lair-btn-outline'}
            style={{ fontSize: 15 }}
            onClick={() => switchTab('db')}
          >
            Логи БД
          </button>
          <button
            className={tab === 'api' ? 'lair-btn' : 'lair-btn lair-btn-outline'}
            style={{ fontSize: 15 }}
            onClick={() => switchTab('api')}
          >
            Логи API
          </button>
        </div>
      </div>
      <div className="lair-content">
        {load ? (
          <div className="lair-skeleton" />
        ) : tab === 'db' ? (
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
          </>
        ) : (
          <>
            <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
              Строк в логе: {api.total}
            </div>
            <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
              {api.lines.length > 0 ? (
                <pre style={{
                  margin: 0, padding: '16px 20px',
                  fontSize: 13, lineHeight: 1.6,
                  color: 'var(--parchment-dim)', whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all', maxHeight: 'calc(100vh - 320px)',
                  overflowY: 'auto', fontFamily: 'var(--font-mono)',
                }}>
                  {api.lines.map((line, i) => (
                    <div key={i} style={{
                      color: line.includes('Error') || line.includes('Traceback') || line.includes('ERROR') ? 'var(--fire)' :
                             line.includes('WARN') || line.includes('warning') ? 'var(--ember)' : undefined,
                    }}>
                      {line.trimEnd()}
                    </div>
                  ))}
                </pre>
              ) : (
                <div style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>
                  Лог-файл пуст или недоступен
                </div>
              )}
            </div>
          </>
        )}
        {totalPages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
            <button
              className="lair-btn lair-btn-sm lair-btn-outline"
              disabled={(tab === 'db' ? page : api.page) <= 1}
              onClick={() => goPage((tab === 'db' ? page : api.page) - 1)}
            >← Назад</button>
            <span style={{ color: 'var(--parchment-dim)', fontSize: 14, padding: '4px 12px' }}>
              {tab === 'db' ? page : api.page} / {totalPages}
            </span>
            <button
              className="lair-btn lair-btn-sm lair-btn-outline"
              disabled={(tab === 'db' ? page : api.page) >= totalPages}
              onClick={() => goPage((tab === 'db' ? page : api.page) + 1)}
            >Вперёд →</button>
          </div>
        )}
      </div>
    </>
  );
}

export default LogsList;
