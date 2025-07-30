import { fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export const baseQuery = fetchBaseQuery({
  baseUrl: "/api/proxy",
  credentials: "same-origin",
  prepareHeaders: (headers) => {
    headers.set("Content-Type", "application/json");
    return headers;
  },
});

// for form data
// Avoid setting Content-Type to multipart/form-data
// because it sets limits on the size of the payload
export const formDataBaseQuery = fetchBaseQuery({
  baseUrl: "/api/proxy",
  credentials: "same-origin",
  prepareHeaders: (headers) => {
    return headers;
  },
});
