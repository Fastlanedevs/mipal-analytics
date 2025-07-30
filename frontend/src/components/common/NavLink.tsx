"use client";

import Link from "next/link";
import { ComponentProps, useState } from "react";

type NavLinkProps = ComponentProps<typeof Link> & {
  showLoader?: boolean;
};

// Global callback that can be set by the NavigationProvider
let globalNavigationCallback: (() => void) | null = null;

// Function to set the global navigation callback
export function setNavigationCallback(callback: () => void) {
  globalNavigationCallback = callback;
}

// Enhanced Link component that triggers the loading state
export default function NavLink({
  onClick,
  showLoader = true,
  ...props
}: NavLinkProps) {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // Call the original onClick if provided
    if (onClick) {
      onClick(e);
    }

    // Don't show loader for external links or if disabled
    if (
      !showLoader ||
      (typeof props.href === "string" && props.href.startsWith("http")) ||
      e.defaultPrevented
    ) {
      return;
    }

    // Trigger loading state using the global callback
    if (globalNavigationCallback) {
      globalNavigationCallback();
    }
  };

  return <Link onClick={handleClick} {...props} />;
}
