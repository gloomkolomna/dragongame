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

type Tab = 'db' | 'api' | 'requests' | 'payments' | 'donors';

interface PaginatedState<T> {
  items: T[];
  total: number;
  page: number;
}

interface PaymentLogItem {
  id: number;
  vk_id: number | null;
  order_id: number | null;
  action: string;
  login: string;
  out_sum: string;
  inv_id: string;
  test_mode: boolean;
  sig: string;
  receipt_json: string;
  detail: string;
  created_at: string;
}

interface DonorEventItem {
  id: number;
  source_id: number | null;
  vk_id: number | null;
  event_type: string;
  created_at: string;
  synced_at: string;
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
  const [payState, setPayState] = useState<PaginatedState<PaymentLogItem>>({ items: [], total: 0, page: 1 });
  const [payExpanded, setPayExpanded] = useState<number | null>(null);
  const [donorState, setDonorState] = useState<PaginatedState<DonorEventItem>>({ items: [], total: 0, page: 1 });

  const payGroups = useMemo(() => {
    const map = new Map<number, PaymentLogItem[]>();
    for (const l of payState.items) {
      const key = l.order_id ?? 0;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(l);
    }
    return [...map.entries()].sort((a, b) => b[0] - a[0]);
  }, [payState.items]);

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

  const fetchPayLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/payment-logs', { params: { page: p, per_page: perPage } })
      .then((r) => setPayState({ items: r.data.items, total: r.data.total, page: r.data.page }))
      .finally(() => setLoad(false));
  }, []);

  const fetchDonorLogs = useCallback((p: number) => {
    setLoad(true);
    client.get('/admin/logs/donor', { params: { page: p, per_page: perPage } })
      .then((r) => setDonorState({ items: r.data.items, total: r.data.total, page: r.data.page }))
      .finally(() => setLoad(false));
  }, []);

  useEffect(() => { fetchDbLogs(1); }, [fetchDbLogs]);

  const switchTab = (t: Tab) => {
    setTab(t);
    setExpanded(null);
    setPayExpanded(null);
    setFilter('');
    if (t === 'api' && apiState.items.length === 0) fetchApiLogs(1);
    if (t === 'requests' && reqState.items.length === 0) fetchReqLogs(1);
    if (t === 'payments' && payState.items.length === 0) fetchPayLogs(1);
    if (t === 'donors' && donorState.items.length === 0) fetchDonorLogs(1);
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

  const filteredDonor = useMemo(() => {
    let items = [...donorState.items];
    if (filter) { const f = filter.toLowerCase(); items = items.filter((d) => d.event_type.toLowerCase().includes(f) || String(d.vk_id ?? '').includes(f)); }
    return sortedFiltered(items);
  }, [donorState.items, filter, sortKey, sortDir]);

  const cur = tab === 'db' ? dbState : tab === 'api' ? apiState : tab === 'requests' ? reqState : tab === 'donors' ? donorState : payState;
  const totalPages = Math.ceil(cur.total / perPage);
  const formatDate = (s: string) => s ? new Date(s).toLocaleString('ru-RU') : '—';

  const goPage = (p: number) => {
    if (tab === 'db') fetchDbLogs(p);
    else if (tab === 'api') fetchApiLogs(p);
    else if (tab === 'requests') fetchReqLogs(p);
    else if (tab === 'donors') fetchDonorLogs(p);
    else fetchPayLogs(p);
  };

  const clearLogs = async () => {
    if (!window.confirm('Очистить все логи (БД + запросы API)?')) return;
    try {
      await client.post('/admin/logs/clear');
      if (tab === 'db') fetchDbLogs(1);
      else if (tab === 'requests') fetchReqLogs(1);
    } catch (e: any) {
      alert('Ошибка очистки');
    }
  };

  const statusColor = (code: number) => code >= 500 ? 'var(--fire)' : 'var(--ember)';

  return (
    <>
      <div className="lair-header" style={{ flexWrap: 'wrap', gap: 8, paddingBottom: 12 }}>
        <h2 style={{ flexShrink: 0 }}>📋 Логи</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {(['db', 'api', 'requests', 'payments', 'donors'] as Tab[]).map((t) => (
            <button key={t}
              className={tab === t ? 'lair-btn' : 'lair-btn lair-btn-outline'}
              style={{ fontSize: 15 }}
              onClick={() => switchTab(t)}
            >
              {t === 'db' ? 'Логи БД' : t === 'api' ? 'Логи API' : t === 'requests' ? 'Запросы API' : t === 'payments' ? 'Платежи' : 'Донат'}
            </button>
          ))}
          {tab !== 'api' && tab !== 'donors' && (
            <button className="lair-btn lair-btn-danger" style={{ fontSize: 14, marginLeft: 8 }}
                    onClick={clearLogs}>🗑 Очистить</button>
          )}
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
            ) : tab === 'requests' ? (
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
            ) : tab === 'donors' ? (
              <>
                <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
                  Всего: {donorState.total} / показано: {filteredDonor.length}
                </div>
                <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table className="lair-table">
                    <thead>
                      <tr>
                        {['id', 'vk_id', 'event_type', 'created_at', 'synced_at'].map((k) => (
                          <th key={k} onClick={() => handleSort(k)} style={{ cursor: 'pointer' }}>
                            {k === 'id' ? 'ID' : k === 'vk_id' ? 'VK ID' : k === 'event_type' ? 'Событие' : k === 'created_at' ? 'Дата события' : 'Получено'}{sortArrow(k)}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDonor.map((d) => (
                        <tr key={d.id}>
                          <td>{d.id}</td>
                          <td>{d.vk_id ?? '—'}</td>
                          <td><span className="lair-badge">{d.event_type}</span></td>
                          <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(d.created_at)}</td>
                          <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(d.synced_at)}</td>
                        </tr>
                      ))}
                      {filteredDonor.length === 0 && (
                        <tr><td colSpan={5} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Событий доната пока нет</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <>
                <div style={{ marginBottom: 12, color: 'var(--parchment-faded)', fontSize: 14 }}>
                  Заказов: {payGroups.length} / записей: {payState.total}
                </div>
                <div className="lair-card" style={{ padding: 0, overflow: 'hidden' }}>
                  <table className="lair-table">
                    <thead>
                      <tr>
                        <th>Заказ</th>
                        <th>VK ID</th>
                        <th>Сумма</th>
                        <th>Логин</th>
                        <th>Тест</th>
                        <th>Действий</th>
                        <th>Последнее</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payGroups.map(([orderId, logs]) => {
                        const head = logs[0];
                        const actions = logs.map((l) => l.action).join(', ');
                        const lastDate = logs[logs.length - 1].created_at;
                        return (
                          <>
                            <tr key={orderId}
                                onClick={() => setPayExpanded(payExpanded === orderId ? null : orderId)}
                                style={{ cursor: 'pointer' }}>
                              <td style={{ fontWeight: 600 }}>#{orderId}</td>
                              <td>{head.vk_id ?? '—'}</td>
                              <td>{head.out_sum}</td>
                              <td>{head.login}</td>
                              <td>{head.test_mode ? 'Да' : 'Нет'}</td>
                              <td style={{ fontSize: 13 }}>{logs.length}</td>
                              <td style={{ fontSize: 13, color: 'var(--parchment-faded)' }}>{formatDate(lastDate)}</td>
                            </tr>
                            {payExpanded === orderId && (
                              <tr key={`${orderId}-det`}>
                                <td colSpan={7} style={{ padding: '8px 16px', background: 'rgba(0,0,0,0.2)' }}>
                                  <table style={{ width: '100%', fontSize: 12 }}>
                                    <thead>
                                      <tr style={{ color: 'var(--parchment-faded)' }}>
                                        <th style={{ textAlign: 'left', padding: '2px 8px' }}>ID</th>
                                        <th style={{ textAlign: 'left', padding: '2px 8px' }}>Действие</th>
                                        <th style={{ textAlign: 'left', padding: '2px 8px' }}>Sig</th>
                                        <th style={{ textAlign: 'left', padding: '2px 8px' }}>Дата</th>
                                        <th style={{ textAlign: 'left', padding: '2px 8px' }}>Детали</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {logs.map((l) => (
                                        <tr key={l.id}>
                                          <td style={{ padding: '2px 8px' }}>{l.id}</td>
                                          <td style={{ padding: '2px 8px' }}>{l.action}</td>
                                          <td style={{ padding: '2px 8px', fontFamily: 'var(--font-mono)', fontSize: 11, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>{l.sig}</td>
                                          <td style={{ padding: '2px 8px', color: 'var(--parchment-faded)' }}>{formatDate(l.created_at)}</td>
                                          <td style={{ padding: '2px 8px', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{l.detail || '—'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </td>
                              </tr>
                            )}
                          </>
                        );
                      })}
                      {payGroups.length === 0 && (
                        <tr><td colSpan={7} style={{ textAlign: 'center', padding: 32, color: 'var(--parchment-faded)' }}>Логов платежей пока нет</td></tr>
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
