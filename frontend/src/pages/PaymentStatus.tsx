import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import DragonLogo from '../components/DragonLogo';

const PAY_BASE = import.meta.env.VITE_PAY_BASE || (window.location.origin + '/pay');
const COMMUNITY_URL = 'https://vk.ru/bestiaryofdragonlegends';
const POLL_MS = 3000;

type PageState = 'loading' | 'pending' | 'success' | 'cancelled' | 'failed' | 'not_found';

function PaymentStatus() {
  const [searchParams] = useSearchParams();
  const txn = searchParams.get('txn') || '';
  const [state, setState] = useState<PageState>('loading');

  useEffect(() => {
    if (!txn) { setState('not_found'); return; }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const r = await fetch(`${PAY_BASE}/status/${txn}`);
        if (r.status === 404) { if (!cancelled) setState('not_found'); return; }
        if (r.ok) {
          const data = await r.json();
          if (data.status && data.status !== 'pending') {
            if (!cancelled) setState(data.status as PageState);
            return;
          }
          if (!cancelled) setState('pending');
        }
      } catch {}
      if (!cancelled) timer = setTimeout(poll, POLL_MS);
    };
    poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [txn]);

  const view = (() => {
    switch (state) {
      case 'loading':
        return { icon: '🔎', title: 'Проверяем оплату…', text: '', color: 'var(--parchment-dim)' };
      case 'pending':
        return {
          icon: '⏳', title: 'Ждём подтверждения оплаты', color: 'var(--ember)',
          text: 'Если ты уже оплатил — страница обновится сама, обычно в течение пары минут. Не закрывай её.',
        };
      case 'success':
        return {
          icon: '✅', title: 'Оплата прошла!', color: 'var(--success)',
          text: 'PIN-коды драконов отправлены тебе в личные сообщения сообщества. Если сообщение не пришло — напиши нам.',
        };
      case 'cancelled':
        return {
          icon: '⏰', title: 'Заказ отменён', color: 'var(--parchment-faded)',
          text: 'Срок оплаты истёк или заказ был отменён. Если деньги списались — напиши нам, разберёмся.',
        };
      case 'failed':
        return {
          icon: '❌', title: 'Оплата не прошла', color: 'var(--fire)',
          text: 'Платёж не был завершён. Средства не списаны или вернутся автоматически. Попробуй оформить заказ заново.',
        };
      default:
        return {
          icon: '🐉', title: 'Заказ не найден', color: 'var(--parchment-faded)',
          text: 'Проверь ссылку, по которой ты перешёл, или оформи заказ заново в боте сообщества.',
        };
    }
  })();

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', padding: 20 }}>
      <div className="lair-card lair-rise" style={{ width: '100%', maxWidth: 440, padding: '40px 32px', textAlign: 'center' }}>
        <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'center' }}>
          <DragonLogo width={110} height={110} />
        </div>
        <div style={{ fontSize: 44, lineHeight: 1, marginBottom: 12 }}>{view.icon}</div>
        <h1 style={{ margin: '0 0 10px', fontSize: 22, color: view.color }}>{view.title}</h1>
        {view.text && (
          <p style={{ margin: '0 0 26px', color: 'var(--parchment-dim)', fontSize: 15, fontFamily: 'var(--font-body)' }}>
            {view.text}
          </p>
        )}
        {state === 'pending' || state === 'loading' ? (
          <div style={{ fontSize: 13, color: 'var(--parchment-faded)', fontFamily: 'var(--font-mono)' }}>
            {txn}
          </div>
        ) : (
          <a
            className="lair-btn"
            href={COMMUNITY_URL}
            target="_blank"
            rel="noreferrer"
            style={{ display: 'inline-flex', textDecoration: 'none', justifyContent: 'center', padding: '14px 28px' }}
          >
            Вернуться в сообщество
          </a>
        )}
      </div>
    </div>
  );
}

export default PaymentStatus;
