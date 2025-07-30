import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface SelectedFile {
  id: string;
  title: string;
  content: string;
  address: string;
}

interface FileSearchState {
  selectedFiles: SelectedFile[];
}

const initialState: FileSearchState = {
  selectedFiles: [],
};

export const fileSearchSlice = createSlice({
  name: "fileSearch",
  initialState,
  reducers: {
    addSelectedFile: (state, action: PayloadAction<SelectedFile>) => {
      const exists = state.selectedFiles.some(
        (file) => file.id === action.payload.id
      );
      if (!exists) {
        state.selectedFiles.push(action.payload);
      }
    },
    removeSelectedFile: (state, action: PayloadAction<string>) => {
      state.selectedFiles = state.selectedFiles.filter(
        (file) => file.id !== action.payload
      );
    },
    clearSelectedFiles: (state) => {
      state.selectedFiles = [];
    },
    resetSelectedFiles: () => initialState,
  },
});

export const {
  addSelectedFile,
  removeSelectedFile,
  clearSelectedFiles,
  resetSelectedFiles,
} = fileSearchSlice.actions;
export default fileSearchSlice.reducer;
