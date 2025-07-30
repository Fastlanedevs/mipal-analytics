import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  initialized: boolean;
}

const initialState: AppState = {
  initialized: false,
};

export const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setInitialized: (state, action: PayloadAction<boolean>) => {
      state.initialized = action.payload;
    },
  },
});

export const { setInitialized } = appSlice.actions;
export default appSlice.reducer;
