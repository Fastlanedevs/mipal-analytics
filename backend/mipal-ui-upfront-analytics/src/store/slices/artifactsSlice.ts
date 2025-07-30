import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { Artifact } from "../../app/(protected)/chat/types/chat";
import { mockArtifacts } from "@/app/(protected)/chat/analytics/components/__mock__/mockData";
interface ArtifactsState {
  artifacts: Artifact[];
  isArtifactPanelOpen: boolean;
}

const initialState: ArtifactsState = {
  artifacts: [],
  isArtifactPanelOpen: false,
};

export const artifactsSlice = createSlice({
  name: "artifacts",
  initialState,
  reducers: {
    setArtifacts: (state, action: PayloadAction<Artifact[]>) => {
      state.artifacts = action.payload;
    },
    setIsArtifactPanelOpen: (state, action: PayloadAction<boolean>) => {
      state.isArtifactPanelOpen = action.payload;
    },
    removeArtifacts: (state) => {
      state.artifacts = [];
    },
  },
});

export const { setArtifacts, setIsArtifactPanelOpen, removeArtifacts } =
  artifactsSlice.actions;
export default artifactsSlice.reducer;
