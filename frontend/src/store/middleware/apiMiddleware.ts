import { createListenerMiddleware } from "@reduxjs/toolkit";
import { userApi } from "../services/userApi";
import { organizationApi } from "../services/organizationApi";

export const listenerMiddleware = createListenerMiddleware();

listenerMiddleware.startListening({
  matcher: userApi.endpoints.getUserProfile.matchFulfilled,
  effect: async (action, listenerApi) => {
    const userProfile = action.payload;
    if (userProfile?.organisation?.id) {
      // Trigger organization fetch when user profile is loaded
      listenerApi.dispatch(
        organizationApi.endpoints.getOrganization.initiate(
          userProfile.organisation.id
        )
      );
    }
  },
});
