import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { SuggestionContent } from "../services/intentApi";

interface IntentsState {
  suggestions: SuggestionContent[];
  selectedSuggestion: SuggestionContent | null;
  loading: boolean;
  error: string | null;
}

const initialState: IntentsState = {
  suggestions: [],
  selectedSuggestion: null,
  loading: false,
  error: null,
};

const intentsSlice = createSlice({
  name: "intents",
  initialState,
  reducers: {
    setSuggestions: (state, action: PayloadAction<SuggestionContent[]>) => {
      state.suggestions = action.payload;
    },
    setSelectedSuggestion: (
      state,
      action: PayloadAction<SuggestionContent | null>
    ) => {
      state.selectedSuggestion = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    clearSuggestions: (state) => {
      state.suggestions = [];
      state.selectedSuggestion = null;
    },
  },
});

export const {
  setSuggestions,
  setSelectedSuggestion,
  setLoading,
  setError,
  clearSuggestions,
} = intentsSlice.actions;

export default intentsSlice.reducer;
