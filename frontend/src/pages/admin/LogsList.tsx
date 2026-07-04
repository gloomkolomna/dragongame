import { useEffect, useState, useCallback, useMemo } from 'react';
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

interface ApiRequestItem {
  id: number;
  method: string;
  path: string;
  status_code: number;
  client_ip: string;
  created_at: string;
}

type Tab = 'db' | 'api' | 'requests';

interface PaginatedState<T> {
  items: T[];
  total: number;
  page: number;
}

function LogsList() {
  const [tab, setTab] = useState<Tab>('db');
  const [load, setLoad] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [filter, setFilter] = useState('');
  const [sortKey, setSortKey] = useState('');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const perPage = 50;

  const [dbState, setDbState] = useState<PaginatedState<ErrorLog>>({ items: [], total: 0, page: 1 });
  const [apiState, setApiState] = useState<PaginatedState<string>>({ items: [], total: 0, page: 1 });
  const [reqState, setReqState] = useState<PaginatedState<ApiRequestItem>>({ items: [], total: 0, page: 1 });

  const fetchDbLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs', { params: { page: p, per_page: perPage } })
      .then((r) => setDbState({ items: r.data.logs, total: r.data.total, page: r.data.page }))
      .finally(() => setLoad(false));
  }, []);

  const fetchApiLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs/api', { params: { page: p, per_page: perPage } })
      .then((r) => setApiState({ items: r.data.lines, total: r.data.total, page: r.data.page }))
      .finally(() => setLoad(false));
  }, []);

  const fetchReqLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs/api-requests', { params: { page: p, per_page: perPage } })
      .then((r) => setReqState({ items: r.data.items, total: r.data.total, page: r.data.page }))
      .finally(() => setLoad(false));
  }, []);

  useEffect(() => { fetchDbLogs(1); }, [fetchDbLogs]);

  const switchTab = (t: Tab) => {
    setTab(t);
    setExpanded(null);
    setFilter('');
    if (t === 'api' && apiState.items.length === 0) fetchApiLogs(1);
    if (t === 'requests' && reqState.items.length === 0) fetchReqLogs(1);
  };

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const sortArrow = (key: string) => sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  const filteredApi = useMemo(() => {
    if (!filter) return apiState.items;
    const f = filter.toLowerCase();
    return apiState.items.filter((l) => l.toLowerCase().includes(f));
  }, [apiState.items, filter]);

  const sortedFiltered = <T extends Record<string, any>>(items: T[]): T[] => {
    const result = [...items];
    if (sortKey && items.length > 0 && sortKey in items[0]) {
      result.sort((a, b) => {
        const va = String(a[sortKey] || '');
        const vb = String(b[sortKey] || '');
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      });
    }
    return result;
  };

  const filteredDb = useMemo(() => {
    let items = [...dbState.items];
    if (filter) { const f = filter.toLowerCase(); items = items.filter((l) => l.message.toLowerCase().includes(f) || l.error_type.toLowerCase().includes(f) || l.source.toLowerCase().includes(f)); }
    return sortedFiltered(items);
  }, [dbState.items, filter, sortKey, sortDir]);

  const filteredReq = useMemo(() => {
    let items = [...reqState.items];
    if (filter) { const f = filter.toLowerCase(); items = items.filter((r) => r.method.toLowerCase().includes(f) || r.path.toLowerCase().includes(f) || String(r.status_code).includes(f) || r.client_ip.includes(f)); }
    return sortedFiltered(items);
  }, [reqState.items, filter, sortKey, sortDir]);

  const cur = tab === 'db' ? dbState : tab === 'api' ? apiState : reqState;
  const totalPages = Math.ceil(cur.total / perPage);
  const formatDate = (s: string) => s ? new Date(s).toLocaleString('ru-RU') : '—';

  const goPage = (p: number) => {
    if (tab === 'db') fetchDbLogs(p);
    else if (tab === 'api') fetchApiLogs(p);
    else fetchReqLogs(p);
  };

  const statusColor = (code: number) => code >= 500 ? 'var(--fire)' : 'var(--ember)';

  return (
    <>
      <div className="lair-header" style={{ flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
        <h2 style={{ flexShrink: 0 }}>📋 Логи</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {(['db', 'api', 'requests'] as Tab[]).map((t) => (
            <button key={t}
              className={tab === t ? 'lair-btn' : 'lair-btn lair-btn-outline'}
              style={{ fontSize: 15 }}
              onClick={() => switchTab(t)}
            >
              {t === 'db' ? 'Логи БД' : t === 'api' ? 'Логи API' : 'Запросы API'}
            </button>
          ))}
        </div>
      </div>
      <div className="lair-content">
        {load ? (
          <div className="lair-skeleton" />
        ) : (
          <>
            {tab !== 'api' && (
              <input className="lair-input" placeholder="Фильтр..." value={filter}
                     onChange={(e) => setFilter(e.target.value)}
                     style={{ marginBottom: 12, maxWidth: 300, fontSize: 16, padding: '8px 12px' }} />
            )}
            {tab === 'db' ? (
              <>
                <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
                  Всего: {dbState.total} / показано: {filteredDb.length}
                </div>
                <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table className="lair-table">
                    <thead>
                      <tr>
                        {['id', 'source', 'error_type', 'message', 'user_id', 'created_at'].map((k) => (
                          <th key={k} onClick={() => handleSort(k)} style={{ cursor: 'pointer' }}>
                            {k === 'id' ? 'ID' : k === 'source' ? 'Источник' : k === 'error_type' ? 'Тип' : k === 'message' ? 'Сообщение' : k === 'user_id' ? 'VK ID' : 'Дата'}{sortArrow(k)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDb.map((log) => (
                        <>
                          <tr key={log.id} className="clickable"
                              onClick={() => setExpanded(expanded === log.id ? null : log.id)}
                              style={{ cursor: 'pointer' }}>
                            <td>{log.id}</td>
                            <td><span className="lair-badge">{log.source}</span></td>
                            <td style={{ color: 'var(--fire)', fontSize: 13 }}>{log.error_type}</td>
                            <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.message}</td>
                            <td>{log.user_id ?? '—'}</td>
                            <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(log.created_at)}</td>
                          </tr>
                          {expanded === log.id && (
                            <tr key={`${log.id}-tb`}>
                              <td colSpan={6} style={{ padding: 12, background: 'rgba(0,0,0,0.3)' }}>
                                <pre style={{ margin: 0, fontSize: 12, color: 'var(--parchment-dim)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 400, overflowY: 'auto' }}>{log.traceback_text || log.message}</pre>
                              </td>
                            </tr>
                          )}
                        </>
                      ))}
                      {filteredDb.length === 0 && (
                        <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Ничего не найдено</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            ) : tab === 'api' ? (
              <>
                <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
                  Строк в логе: {apiState.total}
                </div>
                <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
                  {filteredApi.length > 0 ? (
                    <pre style={{ margin: 0, padding: '16px 20px', fontSize: 13, lineHeight: 1.6, color: 'var(--parchment-dim)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', maxHeight: 'calc(100vh - 320px)', overflowY: 'auto', fontFamily: 'var(--font-mono)' }}>
                      {filteredApi.map((line, i) => (
                        <div key={i} style={{ color: line.includes('Error') || line.includes('Traceback') || line.includes('ERROR') ? 'var(--fire)' : line.includes('WARN') || line.includes('warning') ? 'var(--ember)' : undefined }}>{line.trimEnd()}</div>
                      ))}
                    </pre>
                  ) : (
                    <div style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Лог-файл пуст или недоступен</div>
                  )}
                </div>
              </>
            ) : (
              <>
                <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
                  Всего: {reqState.total} / показано: {filteredReq.length}
                </div>
                <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table className="lair-table">
                    <thead>
                      <tr>
                        {['id', 'method', 'path', 'status_code', 'client_ip', 'created_at'].map((k) => (
                          <th key={k} onClick={() => handleSort(k)} style={{ cursor: 'pointer' }}>
                            {k === 'id' ? 'ID' : k === 'method' ? 'Метод' : k === 'path' ? 'Путь' : k === 'status_code' ? 'Статус' : k === 'client_ip' ? 'IP' : 'Дата'}{sortArrow(k)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredReq.map((r) => (
                        <tr key={r.id}>
                          <td>{r.id}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}>{r.method}</td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.path}</td>
                          <td style={{ color: statusColor(r.status_code), fontWeight: 700 }}>{r.status_code}</td>
                          <td style={{ fontSize: 13, color: 'var(--parchment-dim)' }}>{r.client_ip}</td>
                          <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(r.created_at)}</td>
                        </tr>
                      ))}
                      {filteredReq.length === 0 && (
                        <tr><td colSpan={6} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Ошибочных запросов нет</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
                <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={cur.page <= 1}
                        onClick={() => goPage(cur.page - 1)}>← Назад</button>
                <span style={{ color: 'var(--parchment-dim)', fontSize: 14, padding: '4px 12px' }}>{cur.page} / {totalPages}</span>
                <button className="lair-btn lair-btn-sm lair-btn-outline" disabled={cur.page >= totalPages}
                        onClick={() => goPage(cur.page + 1)}>Вперёд →</button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}

export default LogsList;
