import { configureStore, combineReducers } from "@reduxjs/toolkit";
import { persistStore, persistReducer, PURGE } from "redux-persist";
import storage from "redux-persist/lib/storage";
import { organizationApi } from "./services/organizationApi";
import { userApi } from "./services/userApi";
import { chatApi } from "./services/chatApi";
import { integrationApi } from "./services/integrationApi";
import { syncApi } from "./services/syncApi";
import { listenerMiddleware } from "./middleware/apiMiddleware";
import { palApi } from "./services/palApi";
import { dashboardApi } from "./services/dashboardApi";
import { stripeApi } from "./services/stripeApi";
import { analyticsApi } from "./services/analyticsApi";
import { chartsApi } from "./services/chartsApi";
import { analyticsApiFormData } from "./services/analyticsApi";
import { formDataApi, sourcingApi } from "./services/sourcingApi";

import appReducer from "./slices/appSlice";
import chatReducer from "./slices/chatSlice";
import chatCreationReducer from "./slices/chatCreationSlice";
import syncReducers from "./slices/syncSlice";
import { filesApi } from "./services/filesApi";
import fileSearchReducer from "./slices/fileSearchSlice";
import artifactsReducer from "./slices/artifactsSlice";
// import dashboardChartsReducer from "./slices/dashboardChartsSlice";
import intentsReducer from "./slices/intentsSlice";
// import datasourceReducer from "./slices/datasourceSlice";
import analyticsReducer from "./slices/analyticsSlice";
import dashboardReducer from "./slices/dashboardSlice";
import chartDataReducer from "./slices/chartDataSlice";
import { intentApi } from "./services/intentApi";
import referencesReducer from "./slices/referencesSlice";

const persistConfig = {
  key: "root",
  storage,
  whitelist: ["app"],
};

const rootReducer = combineReducers({
  [organizationApi.reducerPath]: organizationApi.reducer,
  [userApi.reducerPath]: userApi.reducer,
  [chatApi.reducerPath]: chatApi.reducer,
  [integrationApi.reducerPath]: integrationApi.reducer,
  [syncApi.reducerPath]: syncApi.reducer,
  [filesApi.reducerPath]: filesApi.reducer,
  [palApi.reducerPath]: palApi.reducer,
  [dashboardApi.reducerPath]: dashboardApi.reducer,
  [stripeApi.reducerPath]: stripeApi.reducer,
  [analyticsApi.reducerPath]: analyticsApi.reducer,
  [intentApi.reducerPath]: intentApi.reducer,
  [chartsApi.reducerPath]: chartsApi.reducer,
  [sourcingApi.reducerPath]: sourcingApi.reducer,
  [formDataApi.reducerPath]: formDataApi.reducer,
  app: appReducer,
  chat: chatReducer,
  chatCreation: chatCreationReducer,
  sync: syncReducers,
  fileSearch: fileSearchReducer,
  artifacts: artifactsReducer,
  // dashboardCharts: dashboardChartsReducer,
  intents: intentsReducer,
  // datasource: datasourceReducer,
  analytics: analyticsReducer,
  dashboard: dashboardReducer,
  chartData: chartDataReducer,
  references: referencesReducer,
});

export const store = configureStore({
  reducer: persistReducer(persistConfig, rootReducer),
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }).concat(
      organizationApi.middleware,
      userApi.middleware,
      chatApi.middleware,
      integrationApi.middleware,
      syncApi.middleware,
      filesApi.middleware,
      palApi.middleware,
      dashboardApi.middleware,
      stripeApi.middleware,
      listenerMiddleware.middleware,
      analyticsApi.middleware,
      analyticsApiFormData.middleware,
      intentApi.middleware,
      chartsApi.middleware,
      sourcingApi.middleware,
      formDataApi.middleware
    ),
});

export const purgeStore = () => {
  store.dispatch({ type: PURGE });
};

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
