import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface Reference {
  type: string;
  title: string;
  content?: string;
  address?: string;
  description?: string;
}

interface ReferencesState {
  references: Reference[];
  isReferencePanelOpen: boolean;
}

const initialState: ReferencesState = {
  references: [],
  isReferencePanelOpen: false,
};

export const referencesSlice = createSlice({
  name: "references",
  initialState,
  reducers: {
    setReferences: (state, action: PayloadAction<Reference[]>) => {
      state.references = action.payload;
    },
    setIsReferencePanelOpen: (state, action: PayloadAction<boolean>) => {
      state.isReferencePanelOpen = action.payload;
    },
    removeReferences: (state) => {
      state.references = [];
    },
  },
});

export const { setReferences, setIsReferencePanelOpen, removeReferences } =
  referencesSlice.actions;

export default referencesSlice.reducer;
