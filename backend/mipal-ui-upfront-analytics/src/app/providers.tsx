"use client";

import { Provider } from "react-redux";
import { SessionProvider } from "next-auth/react";
import { store } from "@/store/store";
import { InitializeAppProvider } from "@/components/providers/InitializeAppProvider";
import { NavigationProvider } from "@/components/providers/NavigationProvider";
import { TourProvider } from "@/contexts/TourContext";
import { PostHogProvider } from "@/components/providers/PostHogProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <SessionProvider>
        <InitializeAppProvider>
          <NavigationProvider>
            <TourProvider>
              <PostHogProvider>{children}</PostHogProvider>
            </TourProvider>
          </NavigationProvider>
        </InitializeAppProvider>
      </SessionProvider>
    </Provider>
  );
}
