import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import bridge from '@vkontakte/vk-bridge';
import { setVkLaunchParams } from '../api/client';
import { parseVkLaunchParams } from '../api/vkLaunchParams';

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
      let id: number | null = null;
      let params: Record<string, string> = {};

      const parsed = parseVkLaunchParams(window.location.search, window.location.hash);
      if (parsed.vkUserId) {
        id = parsed.vkUserId;
        params = parsed.params;
      }

      // Обязательный запуск приложения в VK (fire-and-forget, не блокируем
      // рендер). Без VKWebAppInit VK считает приложение «не инициализированным».
      bridge.send('VKWebAppInit').catch(() => {});

      // Дополнительный запрос launch params через VK Bridge — не блокирующий,
      // используется только если URL-разбор ничего не дал.
      if (!id) {
        try {
          const lp = await withTimeout(bridge.send('VKWebAppGetLaunchParams'), 3000);
          if (lp && lp.vk_user_id) {
            id = Number(lp.vk_user_id);
            params = Object.fromEntries(
              Object.entries(lp).map(([k, v]) => [k, String(v)])
            );
          }
        } catch {
          // вне VK — метод недоступен
        }
      }

      if (id) {
        setIsVkWebView(true);
        setVkUserId(id);
        setLaunchParams(params);
        setVkLaunchParams(params);
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
