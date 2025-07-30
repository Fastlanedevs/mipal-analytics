"use client";
import { useGetUserProfileQuery } from "@/store/services/userApi";
import { useGetOrganizationQuery } from "@/store/services/organizationApi";

export default function OrgSidebar() {
  const { data: userProfile } = useGetUserProfileQuery({});
  const { data: organization } = useGetOrganizationQuery(
    userProfile?.organisation?.id || "",
    { skip: !userProfile?.organisation?.id }
  );

  // ... rest of the component
}
