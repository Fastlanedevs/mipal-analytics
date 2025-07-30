"use client";

import { useEffect, useState } from "react";
import LoadingScreen from "@/components/common/LoadingScreen";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Set loading to false after component mounts
    setIsLoading(false);
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return <div className="no-flash">{children}</div>;
}
