import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";

export interface ProductionQueueItem {
  order_id: string;
  customer: string;
  wood_type: string;
  rubber_type: string;
  quantity: number;
  priority: string;
  stage: string;
  progress: number;
  status: string;
  start_date: string;
  delivery_date: string;
  issues: string | null;
  delivery_location: string | null;
}

export interface Dashboard {
  dashboard_id: string;
  title: string;
  description: string;
  layout_config: Record<string, any>;
  layouts: Record<string, any>;
  charts: any[];
  dataframes: any[];
  user_id: string;
  org_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDashboardRequest {
  title: string;
  description?: string;
  layout_config?: Record<string, any>;
  layouts?: Record<string, any>;
}

export interface AddChartRequest {
  chart_id: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  config: Record<string, any>;
}

export interface AddDataframeRequest {
  content: string;
  columns: string;
  metadata: string;
}

export interface ShareDashboardUser {
  user_id: string;
  permission: "view" | "edit";
}

export interface ShareDashboardRequest {
  users: ShareDashboardUser[];
}

export interface ShareDashboardResponse {
  dashboard_id: string;
  users: ShareDashboardUser[];
}

export const dashboardApi = createApi({
  reducerPath: "dashboardApi",
  baseQuery,
  tagTypes: ["ProductionQueue", "Dashboards", "Charts"],
  endpoints: (builder) => ({
    getProductionQueue: builder.query<ProductionQueueItem[], void>({
      query: () => ({ url: "/dashboard/production_queue", method: "GET" }),
      providesTags: ["ProductionQueue"],
    }),

    createDashboard: builder.mutation<Dashboard, CreateDashboardRequest>({
      query: (dashboard) => ({
        url: "/analytics/dashboards",
        method: "POST",
        body: dashboard,
      }),
      invalidatesTags: ["Dashboards"],
    }),

    getAllDashboards: builder.query<Dashboard[], void>({
      query: () => ({
        url: "/analytics/dashboards",
        method: "GET",
      }),
      providesTags: ["Dashboards"],
    }),

    getDashboardById: builder.query<Dashboard, string>({
      query: (dashboardId) => ({
        url: `/analytics/dashboards/${dashboardId}`,
        method: "GET",
      }),
      providesTags: (result, error, dashboardId) =>
        result ? [{ type: "Dashboards", id: dashboardId }] : ["Dashboards"],
    }),

    updateDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; data: Dashboard }
    >({
      query: ({ dashboardId, data }) => ({
        url: `/analytics/dashboards/${dashboardId}`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["Dashboards"],
    }),

    addChartToDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; data: AddChartRequest }
    >({
      query: ({ dashboardId, data }) => ({
        url: `/analytics/dashboards/${dashboardId}/charts`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Dashboards", "Charts"],
    }),

    addDataframeToDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; data: AddDataframeRequest }
    >({
      query: ({ dashboardId, data }) => ({
        url: `/analytics/dashboards/${dashboardId}/dataframes`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Dashboards"],
    }),

    deleteDashboard: builder.mutation<void, string>({
      query: (dashboardId) => ({
        url: `/analytics/dashboards/${dashboardId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Dashboards"],
    }),

    shareDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; users: ShareDashboardUser[] }
    >({
      query: ({ dashboardId, users }) => ({
        url: `/analytics/dashboards/${dashboardId}/share`,
        method: "POST",
        body: { users },
      }),
      invalidatesTags: ["Dashboards"],
    }),

    getSharedUsers: builder.query<ShareDashboardResponse, string>({
      query: (dashboardId) => ({
        url: `/analytics/dashboards/${dashboardId}/share`,
        method: "GET",
      }),
    }),

    deleteChartFromDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; chartId: string }
    >({
      query: ({ dashboardId, chartId }) => ({
        url: `/analytics/dashboards/${dashboardId}/charts/${chartId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Dashboards", "Charts"],
    }),

    deleteDataframeFromDashboard: builder.mutation<
      Dashboard,
      { dashboardId: string; dataframeId: string }
    >({
      query: ({ dashboardId, dataframeId }) => ({
        url: `/analytics/dashboards/${dashboardId}/dataframes/${dataframeId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Dashboards"],
    }),
    refreshDashboard: builder.query<Dashboard, string>({
      query: (dashboardId) => ({
        url: `/analytics/dashboards/${dashboardId}?sync=true`,
        method: "GET",
      }),
      providesTags: (result, error, dashboardId) =>
        result ? [{ type: "Dashboards", id: dashboardId }] : ["Dashboards"],
    }),
  }),
});

export const {
  useGetProductionQueueQuery,
  useCreateDashboardMutation,
  useGetAllDashboardsQuery,
  useUpdateDashboardMutation,
  useAddChartToDashboardMutation,
  useAddDataframeToDashboardMutation,
  useDeleteDashboardMutation,
  useGetDashboardByIdQuery,
  useShareDashboardMutation,
  useGetSharedUsersQuery,
  useDeleteChartFromDashboardMutation,
  useDeleteDataframeFromDashboardMutation,
  useLazyRefreshDashboardQuery,
  useRefreshDashboardQuery,
} = dashboardApi;
