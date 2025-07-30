"use client";

import { useEffect, useState, useCallback } from "react";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import LoadingScreen from "@/components/common/LoadingScreen";
import { NavigationEvents } from "./NavigationEvents";
import { setNavigationCallback } from "@/components/common/NavLink";
import { usePageTitle } from "@/hooks/usePageTitle";

export function NavigationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isPageChanging, setIsPageChanging] = useState(false);

  // Use the page title hook
  usePageTitle();

  // Function to handle navigation events
  const handleNavigation = useCallback(() => {
    setIsPageChanging(true);
  }, []);

  // Register the navigation callback for NavLink components
  useEffect(() => {
    setNavigationCallback(handleNavigation);
  }, [handleNavigation]);

  // Add global click event listener for <a> tags and buttons that might trigger navigation
  useEffect(() => {
    const handleDocumentClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const linkElement = target.closest("a");
      const buttonElement = target.closest("button");

      // Check if it's a link with href or a button that might trigger navigation
      if (
        linkElement &&
        linkElement.href &&
        linkElement.href.startsWith(window.location.origin) &&
        linkElement.href !== window.location.href
      ) {
        handleNavigation();
      } else if (
        buttonElement &&
        buttonElement.getAttribute("data-navigation")
      ) {
        handleNavigation();
      }
    };

    document.addEventListener("click", handleDocumentClick);
    return () => document.removeEventListener("click", handleDocumentClick);
  }, [handleNavigation]);

  // Track page changes through pathname and searchParams
  useEffect(() => {
    // When pathname or searchParams change, the navigation has completed
    const timer = setTimeout(() => {
      setIsPageChanging(false);
    }, 100); // Short delay to ensure the page has rendered

    return () => clearTimeout(timer);
  }, [pathname, searchParams]);

  // Add safeguard to hide loader after a maximum timeout
  useEffect(() => {
    if (isPageChanging) {
      const maxLoadingTimer = setTimeout(() => {
        setIsPageChanging(false);
      }, 3000); // Set a reasonable maximum loading time

      return () => clearTimeout(maxLoadingTimer);
    }
  }, [isPageChanging]);

  return (
    <>
      {isPageChanging && <LoadingScreen />}
      <NavigationEvents setIsNavigating={setIsPageChanging} />
      {children}
    </>
  );
}
