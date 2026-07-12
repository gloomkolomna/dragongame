import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import bridge, { parseURLSearchParamsForGetLaunchParams } from '@vkontakte/vk-bridge';

interface VkContextType {
  vkUserId: number | null;
  isVkWebView: boolean;
  isDemo: boolean;
  launchParams: Record<string, string>;
  loading: boolean;
}

const VkBridgeContext = createContext<VkContextType>({
  vkUserId: null,
  isVkWebView: false,
  isDemo: false,
  launchParams: {},
  loading: true,
});

const DEMO_VK_ID = import.meta.env.VITE_DEMO_VK_ID
  ? Number(import.meta.env.VITE_DEMO_VK_ID)
  : null;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error('vk-bridge timeout')), ms),
    ),
  ]);
}

// Разбор launch params из URL — работает и для query (?vk_user_id=...),
// и для hash (#vk_user_id=...). VK на разных платформах передаёт по-разному.
function parseVkParamsFromUrl(): { vkUserId: number | null; params: Record<string, string> } {
  const sources = [window.location.search, window.location.hash];
  const params: Record<string, string> = {};
  let vkUserId: number | null = null;

  for (const src of sources) {
    const qs = src.startsWith('?') || src.startsWith('#') ? src.substring(1) : src;
    qs.split('&').forEach((p) => {
      const [k, v] = p.split('=');
      if (!k) return;
      const val = decodeURIComponent(v || '');
      params[k] = val;
      if (k === 'vk_user_id') vkUserId = Number(val);
    });
  }

  return { vkUserId, params };
}

export function VkBridgeProvider({ children }: { children: ReactNode }) {
  const [vkUserId, setVkUserId] = useState<number | null>(null);
  const [isVkWebView, setIsVkWebView] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const [launchParams, setLaunchParams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const applyInsetTop = (top: unknown) => {
      const px = Math.max(0, Number(top) || 0);
      document.documentElement.style.setProperty('--vk-inset-top', `${px}px`);
    };

    const listener = (e: any) => {
      const type = e?.detail?.type;
      const data = e?.detail?.data;
      if (!type || !data) return;
      if (type === 'VKWebAppUpdateConfig' || type === 'VKWebAppUpdateInsets') {
        const top = data?.insets?.top;
        if (top !== undefined) applyInsetTop(top);
      }
    };

    bridge.subscribe(listener);
    return () => {
      try { bridge.unsubscribe(listener); } catch { /* noop */ }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      // 1. ОБЯЗАТЕЛЬНЫЙ запуск приложения в VK. Без VKWebAppInit VK считает
      //    приложение «не инициализированным». Безопасен вне VK (reject/timeout).
      try {
        await withTimeout(bridge.send('VKWebAppInit'), 3000);
      } catch {
        // вне VK-окружения или бридж не ответил — нормально
      }

      if (cancelled) return;

      let id: number | null = null;
      let params: Record<string, string> = {};
      let inVk = false;

      // 2. Основной способ — запрос launch params через VK Bridge.
      //    Работает везде (мобайл/веб), независимо от того, как VK передал
      //    параметры (query или hash).
      try {
        const lp = await withTimeout(bridge.send('VKWebAppGetLaunchParams'), 3000);
        if (lp && lp.vk_user_id) {
          inVk = true;
          id = Number(lp.vk_user_id);
          params = Object.fromEntries(
            Object.entries(lp).map(([k, v]) => [k, String(v)])
          );
        }
      } catch {
        // вне VK — метод недоступен, переходим к разбору URL
      }

      // 3. Запасной способ — разбор URL (query + hash). Нужен для dev-режима
      //    и прямых переходов, а также если bridge.send почему-то не сработал.
      if (!id) {
        try {
          const lp = parseURLSearchParamsForGetLaunchParams(
            window.location.search + window.location.hash,
          );
          if (lp && (lp as any).vk_user_id) {
            inVk = true;
            id = Number((lp as any).vk_user_id);
          }
        } catch {
          // игнорируем
        }
      }

      if (!id) {
        const fallback = parseVkParamsFromUrl();
        if (fallback.vkUserId) {
          inVk = true;
          id = fallback.vkUserId;
          params = fallback.params;
        }
      }

      if (id) {
        setIsVkWebView(true);
        setVkUserId(id);
        setLaunchParams(params);
        const cur = getComputedStyle(document.documentElement)
          .getPropertyValue('--vk-inset-top').trim();
        if (!cur || cur === '0px') {
          document.documentElement.style.setProperty('--vk-inset-top', '48px');
        }
      } else if (DEMO_VK_ID) {
        setIsDemo(true);
        setVkUserId(DEMO_VK_ID);
      }

      if (!cancelled) setLoading(false);
    }

    init();
    return () => { cancelled = true; };
  }, []);

  return (
    <VkBridgeContext.Provider value={{ vkUserId, isVkWebView, isDemo, launchParams, loading }}>
      {children}
    </VkBridgeContext.Provider>
  );
}

export function useVkBridge() {
  return useContext(VkBridgeContext);
}
