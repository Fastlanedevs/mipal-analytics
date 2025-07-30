import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { AddDataframeRequest, Dashboard } from "../services/dashboardApi";

// Types
export interface Chart {
  id: string;
  content: string;
  title: string;
}

interface Layout {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
  isBounded?: boolean;
  isDraggable?: boolean;
  isResizable?: boolean;
  static?: boolean;
  moved?: boolean;
  resizeHandles?: string[];
}

interface DashboardState {
  dashboards: Dashboard[];
  currentDashboard: Dashboard | null;
  isLoading: boolean;
  error: string | null;
}

// Initial state
const initialState: DashboardState = {
  dashboards: [],
  currentDashboard: null,
  isLoading: false,
  error: null,
};

// Create the slice
export const dashboardSlice = createSlice({
  name: "dashboard",
  initialState,
  reducers: {
    // Dashboard actions
    createDashboard: (
      state,
      action: PayloadAction<{
        dashboard_id: string;
        title: string;
        description?: string;
        charts?: Chart[];
        dataframes?: AddDataframeRequest[];
      }>
    ) => {
      const newDashboard: Dashboard = {
        dashboard_id: action.payload.dashboard_id,
        title: action.payload.title,
        description: action.payload.description || "",
        charts: action.payload.charts || [],
        dataframes: action.payload.dataframes || [],
        layout_config: {},
        layouts: {},
        user_id: "",
        org_id: "",
        created_at: "",
        updated_at: "",
      };
      state.dashboards.push(newDashboard);
    },

    setCurrentDashboard: (state, action: PayloadAction<Dashboard | null>) => {
      state.currentDashboard = action.payload;
    },

    updateDashboardName: (
      state,
      action: PayloadAction<{ id: string; title: string; description?: string }>
    ) => {
      const dashboard = state.dashboards.find(
        (d) => d.dashboard_id === action.payload.id
      );
      if (dashboard) {
        dashboard.title = action.payload.title;
        dashboard.description = action.payload.description || "";
      }
    },

    deleteDashboard: (state, action: PayloadAction<string>) => {
      state.dashboards = state.dashboards.filter(
        (d) => d.dashboard_id !== action.payload
      );
      if (state.currentDashboard?.dashboard_id === action.payload) {
        state.currentDashboard = null;
      }
    },

    // Updated Chart actions
    addChart: (
      state,
      action: PayloadAction<{ dashboardId: string; chart: Chart }>
    ) => {
      const dashboard = state.dashboards.find(
        (d) => d.dashboard_id === action.payload.dashboardId
      );
      if (dashboard) {
        if (!dashboard.charts) {
          dashboard.charts = [];
        }
        dashboard.charts.push(action.payload.chart);
      }
    },

    updateChart: (
      state,
      action: PayloadAction<{
        dashboardId: string;
        chartId: string;
        updates: Partial<Chart>;
      }>
    ) => {
      const dashboard = state.dashboards.find(
        (d) => d.dashboard_id === action.payload.dashboardId
      );
      if (dashboard && dashboard.charts) {
        const chartIndex = dashboard.charts.findIndex(
          (c) => c.id === action.payload.chartId
        );
        if (chartIndex !== -1) {
          dashboard.charts[chartIndex] = {
            ...dashboard.charts[chartIndex],
            ...action.payload.updates,
          };
        }
      }
    },

    removeChart: (
      state,
      action: PayloadAction<{ dashboardId: string; chartId: string }>
    ) => {
      const dashboard = state.dashboards.find(
        (d) => d.dashboard_id === action.payload.dashboardId
      );
      if (dashboard && dashboard.charts) {
        dashboard.charts = dashboard.charts.filter(
          (c) => c.id !== action.payload.chartId
        );
      }
    },

    // Layout actions
    updateLayout: (
      state,
      action: PayloadAction<{
        dashboardId: string;
        layouts: { [key: string]: Layout[] };
      }>
    ) => {
      const dashboard = state.dashboards.find(
        (d) => d.dashboard_id === action.payload.dashboardId
      );
      if (dashboard) {
        dashboard.layouts = action.payload.layouts;
      }
    },

    // Loading state actions
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },

    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

// Export actions
export const {
  createDashboard,
  setCurrentDashboard,
  updateDashboardName,
  deleteDashboard,
  addChart,
  updateChart,
  removeChart,
  updateLayout,
  setLoading,
  setError,
} = dashboardSlice.actions;

// Export reducer
export default dashboardSlice.reducer;
