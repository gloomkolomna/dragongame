import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import DragonLogo from '../components/DragonLogo';
import client from '../api/client';

function Login() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [devLoading, setDevLoading] = useState(false);
  const [devLoginEnabled, setDevLoginEnabled] = useState(false);
  const { setToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    client.get('/auth/config').then((r) => setDevLoginEnabled(!!r.data?.dev_login_enabled)).catch(() => {});
  }, []);

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) { setToken(token); navigate('/admin/dashboard'); }
  }, [searchParams]);

  if (isAuthenticated) { navigate('/admin/dashboard'); return null; }

  const handleVkLogin = async () => {
    setError(''); setLoading(true);
    try {
      const r = await client.get('/auth/vk-login');
      window.location.href = r.data.url;
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); setLoading(false); }
  };

  const handleDevLogin = async () => {
    setError(''); setDevLoading(true);
    try {
      const r = await client.post('/auth/dev-login');
      setToken(r.data.access_token);
      navigate('/admin/dashboard');
    } catch (e: any) { setError(e.response?.data?.detail || 'Ошибка'); setDevLoading(false); }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', padding: 20 }}>
      <div className="lair-card lair-rise" style={{ width: '100%', maxWidth: 420, padding: '40px 32px', textAlign: 'center' }}>
        <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'center' }}>
          <DragonLogo width={120} height={120} />
        </div>
        <h1 style={{ margin: '0 0 4px', fontSize: 22 }}>Гнездо Дракона</h1>
        <p style={{ margin: '0 0 28px', color: 'var(--parchment-dim)', fontSize: 15, fontFamily: 'var(--font-body)' }}>
          Административная панель
        </p>

        {error && (
          <div style={{ padding: '10px 16px', marginBottom: 16, borderRadius: 8, background: 'rgba(255,70,0,0.1)', color: '#d47474', fontSize: 14 }}>{error}</div>
        )}

        <button className="lair-btn" style={{ width: '100%', justifyContent: 'center', padding: '14px 0' }}
                disabled={loading} onClick={handleVkLogin}>
          {loading ? 'Перенаправление...' : 'Войти через VK ID'}
        </button>

        {devLoginEnabled && (
          <>
            <div style={{ margin: '22px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ flex: 1, height: 1, background: 'var(--bronze)' }} />
              <span style={{ color: 'var(--parchment-faded)', fontSize: 12, fontFamily: 'var(--font-title)', letterSpacing: 2 }}>разработка</span>
              <div style={{ flex: 1, height: 1, background: 'var(--bronze)' }} />
            </div>
            <button className="lair-btn lair-btn-outline" style={{ width: '100%', justifyContent: 'center', padding: '14px 0' }}
                    disabled={devLoading} onClick={handleDevLogin}>
              {devLoading ? 'Вход...' : 'Войти локально (тест)'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default Login;
