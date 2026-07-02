import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import bridge from '@vkontakte/vk-bridge';

interface VkContextType {
  vkUserId: number | null;
  isVkWebView: boolean;
  launchParams: Record<string, string>;
  loading: boolean;
}

const VkBridgeContext = createContext<VkContextType>({
  vkUserId: null,
  isVkWebView: false,
  launchParams: {},
  loading: true,
});

export function VkBridgeProvider({ children }: { children: ReactNode }) {
  const [vkUserId, setVkUserId] = useState<number | null>(null);
  const [isVkWebView, setIsVkWebView] = useState(false);
  const [launchParams, setLaunchParams] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await bridge.send('VKWebAppGetLaunchParams');
        if (data && data.vk_user_id) {
          setIsVkWebView(true);
          setVkUserId(Number(data.vk_user_id));
          setLaunchParams(data as unknown as Record<string, string>);
        }
      } catch {
        // Not in VK Mini App environment — user is in regular browser
        setIsVkWebView(false);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <VkBridgeContext.Provider value={{ vkUserId, isVkWebView, launchParams, loading }}>
      {children}
    </VkBridgeContext.Provider>
  );
}

export function useVkBridge() {
  return useContext(VkBridgeContext);
}
