import { useEffect, useState } from 'react';
import client from '../../api/client';

function SettingsPage() {
  const [keyword, setKeyword] = useState('');
  const [load, setLoad] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    client.get('/admin/settings')
      .then((r) => setKeyword(r.data.welcome_keyword || ''))
      .finally(() => setLoad(false));
  }, []);

  const save = async () => {
    setSaving(true); setError(''); setSaved(false);
    try {
      const r = await client.put('/admin/settings', { welcome_keyword: keyword });
      setKeyword(r.data.welcome_keyword);
      setSaved(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка');
    } finally {
      setSaving(false);
    }
  };

  if (load) return <div className="lair-content"><div className="lair-skeleton" /></div>;

  return (
    <>
      <div className="lair-header"><h2>⚙ Настройки</h2></div>
      <div className="lair-content">
        {error && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(212,116,160,0.1)', color: '#d474a0', fontSize: 13 }}>{error}</div>}
        {saved && <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(120,200,120,0.12)', color: 'var(--success)', fontSize: 13 }}>Сохранено</div>}
        <div className="lair-card" style={{ maxWidth: 420 }}>
          <div style={{ marginBottom: 16 }}>
            <label className="lair-label">Ключевое слово для входа</label>
            <input
              className="lair-input"
              type="text"
              value={keyword}
              onChange={(e) => { setSaved(false); setKeyword(e.target.value); }}
              placeholder="дождались"
              style={{ width: '100%', fontSize: 18 }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              Бот будет отвечать новым игрокам только после этого слова. Если поле пустое — гейт отключён.
            </div>
          </div>
          <button className="lair-btn" disabled={saving} onClick={save}>{saving ? '...' : 'Сохранить'}</button>
        </div>
      </div>
    </>
  );
}

export default SettingsPage;
