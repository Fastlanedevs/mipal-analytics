import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export const baseApi = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api/proxy",
  }),
  tagTypes: [
    "UserProfile",
    "UserSettings",
    "UserCredits",
    "UserOrganizationsMembers",
  ],
  endpoints: () => ({}),
});
