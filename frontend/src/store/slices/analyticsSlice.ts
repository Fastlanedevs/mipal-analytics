import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { TableStats, Database } from "../services/analyticsApi";

// Updated state interface
interface AnalyticsState {
  databases: Database[];
  selectedDatabase: Database | null;
  selectedTable: TableStats | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: AnalyticsState = {
  databases: [],
  selectedDatabase: null,
  selectedTable: null,
  isLoading: false,
  error: null,
};

export const analyticsSlice = createSlice({
  name: "analytics",
  initialState,
  reducers: {
    setDatabases: (state, action: PayloadAction<Database[]>) => {
      state.databases = action.payload;
    },
    setSelectedDatabase: (state, action: PayloadAction<Database | null>) => {
      state.selectedDatabase = action.payload;
    },
    setSelectedTable: (state, action: PayloadAction<TableStats | null>) => {
      state.selectedTable = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    addDatabase: (state, action: PayloadAction<Database>) => {
      state.databases.push(action.payload);
    },
    addTable: (state, action: PayloadAction<TableStats>) => {
      if (state.selectedDatabase) {
        state.selectedDatabase.tables.push(action.payload);
      }
    },
    setTables: (state, action: PayloadAction<TableStats[]>) => {
      if (state.selectedDatabase) {
        state.selectedDatabase.tables = action.payload;
      }
    },
    resetAnalytics: (state) => {
      state.databases = [];
      state.selectedDatabase = null;
      state.selectedTable = null;
      state.isLoading = false;
      state.error = null;
    },
  },
});

export const {
  setDatabases,
  setSelectedDatabase,
  setSelectedTable,
  setLoading,
  setError,
  addDatabase,
  addTable,
  resetAnalytics,
  setTables,
} = analyticsSlice.actions;

export default analyticsSlice.reducer;
