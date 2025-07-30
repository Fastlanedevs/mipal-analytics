"use client";

import { useSession } from "next-auth/react";
import { useGetUserProfileQuery } from "@/store/services/userApi";
import LoadingScreen from "../common/LoadingScreen";

export function InitializeAppProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { status } = useSession();
  const { isLoading: isUserLoading } = useGetUserProfileQuery(
    {},
    {
      // Only fetch when authenticated
      skip: status !== "authenticated",
    }
  );

  if (status === "loading" || isUserLoading) {
    return <LoadingScreen />;
  }

  return <>{children}</>;
}
