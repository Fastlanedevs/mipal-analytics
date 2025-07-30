"use client";

import { useAppSelector } from "@/store/hooks";
import { useGetOrganizationQuery } from "@/store/services/organizationApi";
import { useSession } from "next-auth/react";

export default function OrganizationDashboard() {
  const { status: sessionStatus } = useSession();
  const { currentOrganization } = useAppSelector((state) => state.organization);
  const { profile } = useAppSelector((state) => state.user);
  const {
    data: org,
    isLoading,
    isSuccess,
  } = useGetOrganizationQuery("", {
    skip: sessionStatus !== "authenticated" || !profile?.user_id,
  });

  if (sessionStatus === "loading" || !profile) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading user profile...</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <p>Loading organization details...</p>
      </div>
    );
  }

  if (!currentOrganization && org) {
    return (
      <div className="container mx-auto p-6">
        <p>Organization data available but not in store...</p>
      </div>
    );
  }

  if (!currentOrganization) {
    return (
      <div className="container mx-auto p-6">
        <p>No organization found.</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">
        Welcome to {currentOrganization.name}
      </h1>
      <div className="grid gap-4">
        <div className="p-4 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-2">Organization Details</h2>
          <p>Name: {currentOrganization.name}</p>
          <p>Address: {currentOrganization.address || "Not specified"}</p>
          <p>Phone: {currentOrganization.phone || "Not specified"}</p>
          <p>Website: {currentOrganization.website || "Not specified"}</p>
          {currentOrganization.position && (
            <p>Position: {currentOrganization.position}</p>
          )}
          {currentOrganization.logo && (
            <div className="mt-2">
              <p>Logo:</p>
              <img
                src={currentOrganization.logo}
                alt="Organization Logo"
                className="w-16 h-16 object-cover rounded mt-1"
              />
            </div>
          )}
        </div>
        <div className="p-4 bg-white rounded-lg shadow">
          <h2 className="text-lg font-semibold mb-2">Your Role</h2>
          <p>Role: {profile.role || "Not specified"}</p>
        </div>
      </div>
    </div>
  );
}
