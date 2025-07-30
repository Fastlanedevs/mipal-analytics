import { combineReducers } from "@reduxjs/toolkit";

import { organizationApi } from "./services/organizationApi";

const rootReducer = combineReducers({
  [organizationApi.reducerPath]: organizationApi.reducer,
});

export type RootState = ReturnType<typeof rootReducer>;
export default rootReducer;
