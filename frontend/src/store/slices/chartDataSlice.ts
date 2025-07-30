import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface ChartData {
  chart_schema: any;
  title: string;
  description?: string;
  available_adjustments: {
    chart_types: string[];
    current_settings: {
      chart_type: string;
    };
  };
}

interface ChartDataState {
  cache: Record<string, ChartData>;
}

const initialState: ChartDataState = {
  cache: {},
};

export const chartDataSlice = createSlice({
  name: "chartData",
  initialState,
  reducers: {
    cacheChartData: (
      state,
      action: PayloadAction<{ messageId: string; data: ChartData }>
    ) => {
      state.cache[action.payload.messageId] = action.payload.data;
    },
    clearChartCache: (state) => {
      state.cache = {};
    },
  },
});

export const { cacheChartData, clearChartCache } = chartDataSlice.actions;

export default chartDataSlice.reducer;
