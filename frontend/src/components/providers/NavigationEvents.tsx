"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

type NavigationEventsProps = {
  setIsNavigating: (isNavigating: boolean) => void;
};

// This component listens for route change events from Next.js
export function NavigationEvents({ setIsNavigating }: NavigationEventsProps) {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const startNavigation = () => {
      setIsNavigating(true);
    };

    const endNavigation = () => {
      setIsNavigating(false);
    };

    // This approaches patching the router to detect navigation events
    // since Next App Router doesn't expose events directly
    const originalPush = router.push;
    const originalReplace = router.replace;
    const originalRefresh = router.refresh;

    router.push = function () {
      startNavigation();
      return originalPush.apply(router, arguments as any);
    };

    router.replace = function () {
      startNavigation();
      return originalReplace.apply(router, arguments as any);
    };

    router.refresh = function () {
      startNavigation();
      return originalRefresh.apply(router, arguments as any);
    };

    // Cleanup function to restore original methods
    return () => {
      router.push = originalPush;
      router.replace = originalReplace;
      router.refresh = originalRefresh;
    };
  }, [router, setIsNavigating]);

  // This effect runs when pathname changes (navigation completes)
  useEffect(() => {
    setIsNavigating(false);
  }, [pathname, setIsNavigating]);

  return null;
}
