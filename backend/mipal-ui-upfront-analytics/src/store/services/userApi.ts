//userApi.ts
import { Theme } from "@/contexts/ThemeContext";
import { baseApi } from "./baseApi";

// Define tag types
export type TagTypes = "UserProfile";
export type UserSettingsTagTypes = "UserSettings";

// Add interface for user profile
export interface UserProfile {
  id: string;
  name: string;
  email: string;
  image_url: string;
  joined_org: boolean;
  organisation?: {
    id: string;
    name: string;
  };
  phone?: string;
  job_role?: string;
  user_id: string;
  stripe_customer_id?: string;
}
export interface UserSettings {
  user_id: string;
  theme: Theme;
  language: string;
  timezone: string;
  date_format: string;
  subscription_plan: string;
  pinned_sidebar: boolean;
}

interface UserCredits {
  user_id: string;
  current_credits: number;
  total_credits: number;
  subscription_plan: string;
}

export interface TourGuideState {
  analytics_tour: boolean;
  knowledge_pal_tour: boolean;
  integrations_tour: boolean;
  home: boolean;
  dashboard: boolean;
  search: boolean;
}

interface UserOrganizationsMembers {
  user_id: string;
  email: string;
  role: string;
}

interface Subscription {
  id: string;
  user_id: string;
  subscription_plan: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  start_date: string;
  end_date: string | null;
}

export const userApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getUserProfile: builder.query<UserProfile, object>({
      query: () => ({
        url: "user/profile",
        method: "GET",
      }),
      keepUnusedDataFor: 30,
      providesTags: [{ type: "UserProfile", id: "LIST" }],
    }),
    requestPasswordReset: builder.mutation<void, { email: string }>({
      query: (data) => ({
        url: "auth/password-reset-request",
        method: "POST",
        body: data,
      }),
      transformErrorResponse: (response: { status: number; data: any }) => {
        if (
          typeof response.data === "string" &&
          response.data.includes("<!DOCTYPE html>")
        ) {
          return {
            data: {
              detail:
                "There is an issue with the server. Please try again later.",
            },
          };
        }
        return response;
      },
    }),
    resetPassword: builder.mutation<
      void,
      { email: string; otp: string; new_password: string }
    >({
      query: (data) => ({
        url: "auth/password-reset",
        method: "POST",
        body: data,
      }),
      transformErrorResponse: (response: { status: number; data: any }) => {
        if (
          typeof response.data === "string" &&
          response.data.includes("<!DOCTYPE html>")
        ) {
          return {
            data: {
              detail:
                "There is an issue with the server. Please try again later.",
            },
          };
        }
        return response;
      },
    }),
    getUserSettings: builder.query<UserSettings, object>({
      query: () => ({
        url: "user/settings",
        method: "GET",
      }),
      providesTags: [{ type: "UserSettings", id: "LIST" }],
    }),
    updateUserSettings: builder.mutation({
      query: (data) => ({
        url: "user/settings",
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: [{ type: "UserSettings", id: "LIST" }],
    }),
    updateUserProfile: builder.mutation({
      query: (data) => ({
        url: "user/profile",
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: [{ type: "UserProfile", id: "LIST" }],
    }),
    getUserCredits: builder.query<UserCredits, object>({
      query: () => ({
        url: "credits",
        method: "GET",
      }),
      providesTags: [{ type: "UserCredits", id: "LIST" }],
    }),
    getTourGuide: builder.query<TourGuideState, void>({
      query: () => ({
        url: "user/guide-tour",
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      }),
    }),
    updateTourGuide: builder.mutation<TourGuideState, Partial<TourGuideState>>({
      query: (tourGuideState) => ({
        url: "user/guide-tour",
        method: "PATCH",
        headers: {
          Accept: "application/json",
        },
        body: tourGuideState,
      }),
    }),
    getUserOrganizationsMembers: builder.query<
      UserOrganizationsMembers[],
      { org_id: string }
    >({
      query: ({ org_id }) => ({
        url: `user/organizations/members`,
        method: "GET",
        params: { org_id },
      }),
      providesTags: [{ type: "UserOrganizationsMembers", id: "LIST" }],
    }),
    getSubscription: builder.query<Subscription, void>({
      query: () => ({
        url: "tokens/subscription",
        method: "GET",
      }),
      providesTags: [{ type: "UserCredits", id: "LIST" }],
    }),
  }),
  overrideExisting: false,
});

// Add these selectors
export const selectCurrentUser = userApi.endpoints.getUserProfile.select({});

// Export existing hooks
export const {
  useGetUserProfileQuery,
  useGetUserSettingsQuery,
  useUpdateUserSettingsMutation,
  useUpdateUserProfileMutation,
  useGetUserCreditsQuery,
  useGetTourGuideQuery,
  useUpdateTourGuideMutation,
  useGetUserOrganizationsMembersQuery,
  useGetSubscriptionQuery,
  useRequestPasswordResetMutation,
  useResetPasswordMutation,
} = userApi;
