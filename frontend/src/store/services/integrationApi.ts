import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export interface Integration {
  integration_id: string;
  integration_type: string;
  is_active: boolean;
  last_sync?: string;
  settings?: Record<string, any>;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
  integration_name?: string;
}

interface IntegrationResponse {
  integration_list: Integration[];
}

interface CreateIntegrationRequest {
  integration_type: string;
  credential: Record<string, any>;
  expires_at: string;
  settings: Record<string, any>;
}

interface CreateIntegrationResponse extends Integration {
  user_id: string;
  created_at: string;
  updated_at: string;
}

export const INTEGRATION_TYPES = {
  POSTGRESQL: "POSTGRESQL",
} as const;

export type IntegrationType = keyof typeof INTEGRATION_TYPES;

export const integrationApi = createApi({
  reducerPath: "integrationApi",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api/proxy",
    credentials: "same-origin",
  }),
  tagTypes: ["Integration"],
  endpoints: (builder) => ({
    getIntegration: builder.query<Integration[], void>({
      query: () => "/integrations",
      providesTags: ["Integration"],
      keepUnusedDataFor: 0,
      transformResponse: (response: IntegrationResponse) => {
        return response?.integration_list || [];
      },
    }),
    createIntegration: builder.mutation<
      CreateIntegrationResponse,
      CreateIntegrationRequest
    >({
      query: (data) => ({
        url: "/integrations",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Integration"],
    }),
    getSpecificIntegration: builder.query<Integration, string>({
      query: (integrationType: string) => ({
        url: `/integrations/${integrationType}`,
        method: "GET",
        providesTags: ["Integration"],
      }),
    }),
    deleteIntegration: builder.mutation<void, string>({
      query: (integrationId: string) => ({
        url: `/integrations/${integrationId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Integration"],
    }),
  }),
});

export const {
  useGetIntegrationQuery,
  useCreateIntegrationMutation,
  useGetSpecificIntegrationQuery,
  useDeleteIntegrationMutation,
} = integrationApi;
