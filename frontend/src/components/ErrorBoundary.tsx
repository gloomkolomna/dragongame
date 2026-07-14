import { Component, type ReactNode } from 'react';

interface State {
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error('[ErrorBoundary]', error, info);
    try {
      const payload = JSON.stringify({
        message: error.message,
        stack: error.stack,
        componentStack: info.componentStack,
        ua: navigator.userAgent,
        href: location.href,
        ts: Date.now(),
      });
      localStorage.setItem('dragons_last_error', payload);
    } catch {
      // noop
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          background: '#1a0010', color: '#ff8080',
          padding: 16, overflow: 'auto',
          fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12, lineHeight: 1.5,
        }}>
          <div style={{ fontSize: 18, marginBottom: 8, color: '#ff4040' }}>
            ❌ React упал
          </div>
          <div style={{ marginBottom: 12, color: '#ffcc66' }}>
            {this.state.error.message}
          </div>
          {this.state.error.stack && (
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#cc9966' }}>
              {this.state.error.stack}
            </pre>
          )}
          <button
            onClick={() => { localStorage.clear(); location.reload(); }}
            style={{
              marginTop: 16, padding: '8px 16px', background: '#cc3030', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 14, cursor: 'pointer',
            }}
          >
            Очистить кеш и перезагрузить
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
