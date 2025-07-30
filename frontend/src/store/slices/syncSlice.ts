import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface SyncState {
  isSyncing: boolean;
  syncInProgress: Record<string, boolean>;
  lastSyncTime: Record<string, string>;
}

const initialState: SyncState = {
  isSyncing: false,
  syncInProgress: {},
  lastSyncTime: {},
};

const syncSlice = createSlice({
  name: "sync",
  initialState,
  reducers: {
    setSyncStatus(
      state,
      action: PayloadAction<{ integrationType: string; isSyncing: boolean }>
    ) {
      const { integrationType, isSyncing } = action.payload;
      state.syncInProgress[integrationType] = isSyncing;
    },
    setLastSyncTime(
      state,
      action: PayloadAction<{ integrationType: string; time: string }>
    ) {
      const { integrationType, time } = action.payload;
      state.lastSyncTime[integrationType] = time;
    },
  },
});

export const { setSyncStatus, setLastSyncTime } = syncSlice.actions;
export default syncSlice.reducer;
