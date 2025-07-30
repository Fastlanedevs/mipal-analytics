import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { updateSessionTokens } from "@/lib/auth-helpers";
import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import type { SerializedError } from "@reduxjs/toolkit";

export interface Organization {
  id: string;
  name: string;
  address?: string;
  phone?: string;
  website?: string;
  industry?: string;
  size?: string;
  logo?: string;
  position?: string;
}

interface CreateOrganizationRequest {
  name: string;
  address?: string;
  phone?: string;
  website?: string;
  position?: string;
  logo?: string;
}

interface CreateOrganizationResponse {
  organisation: Organization;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface JoinOrganizationResponse {
  organisation: Organization;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const organizationApi = createApi({
  reducerPath: "organizationApi",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api/proxy",
    credentials: "same-origin",
  }),
  tagTypes: ["Organization", "Members", "Requests"],
  endpoints: (builder) => ({
    getOrganization: builder.query<Organization, string>({
      query: () => `user/organization`,
      providesTags: ["Organization"],
    }),
    createOrganization: builder.mutation<
      CreateOrganizationResponse,
      CreateOrganizationRequest
    >({
      query: (data) => ({
        url: "user/organizations",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Organization"],
      async onQueryStarted(_, { queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          // Update session with new tokens after organization creation
          if (data.access_token && data.refresh_token) {
            await updateSessionTokens(data.access_token, data.refresh_token);
          }
        } catch (err) {
          console.error("Failed to update session tokens:", err);
        }
      },
    }),
    inviteMember: builder.mutation<void, { orgId: string; email: string }>({
      query: ({ orgId, email }) => ({
        url: `user/organizations/${orgId}/invite`,
        method: "POST",
        body: { email },
      }),
    }),
    acceptInvitation: builder.mutation<void, { orgId: string; token: string }>({
      query: ({ orgId, token }) => ({
        url: `user/organizations/${orgId}/accept-invitation`,
        method: "POST",
        body: { token },
      }),
      invalidatesTags: ["Organization"],
    }),
    getJoinRequests: builder.query<any[], string>({
      query: (orgId) => `user/organizations/${orgId}/requests`,
      providesTags: ["Requests"],
    }),
    approveRequest: builder.mutation<void, { orgId: string; userId: string }>({
      query: ({ orgId, userId }) => ({
        url: `user/organizations/${orgId}/requests/${userId}/approve`,
        method: "POST",
      }),
      invalidatesTags: ["Requests", "Members"],
    }),
    rejectRequest: builder.mutation<void, { orgId: string; userId: string }>({
      query: ({ orgId, userId }) => ({
        url: `user/organizations/${orgId}/requests/${userId}/reject`,
        method: "POST",
      }),
      invalidatesTags: ["Requests"],
    }),
    getMembers: builder.query<any[], string>({
      query: (orgId) => `user/organizations/${orgId}/members`,
      providesTags: ["Members"],
    }),
    updateMember: builder.mutation<void, { orgId: string; data: any }>({
      query: ({ orgId, data }) => ({
        url: `user/organizations/${orgId}/members`,
        method: "PUT",
        body: data,
      }),
      invalidatesTags: ["Members"],
    }),
    deleteMember: builder.mutation<void, { orgId: string; userId: string }>({
      query: ({ orgId, userId }) => ({
        url: `user/organizations/${orgId}/members/${userId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Members"],
    }),
    searchOrganizations: builder.query<Organization[], string>({
      query: (query) => `user/organizations/search?query=${query}`,
      providesTags: ["Organization"],
    }),
    joinOrganizationRequest: builder.mutation<
      JoinOrganizationResponse,
      { orgId: string }
    >({
      query: ({ orgId }) => {
        return {
          url: `user/organizations/${orgId}`,
          method: "POST",
          body: {},
        };
      },
      transformResponse: (response: JoinOrganizationResponse) => {
        return response;
      },
      transformErrorResponse: (
        response: FetchBaseQueryError | SerializedError
      ) => {
        console.error("Join request error response:", response);
        return response;
      },
      invalidatesTags: ["Organization"],
    }),
    updateOrganization: builder.mutation<
      Organization,
      { orgId: string; data: Partial<Organization> }
    >({
      query: ({ orgId, data }) => ({
        url: `user/organization`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["Organization"],
    }),
    uploadOrganizationLogo: builder.mutation<
      { image_url: string },
      { file: File; file_type: string }
    >({
      query: ({ file, file_type }) => {
        const formData = new FormData();
        formData.append("file", file);

        return {
          url: "upload",
          method: "POST",
          body: formData,
          formData: true,
        };
      },

      invalidatesTags: ["Organization"],
    }),
    inviteUser: builder.mutation<
      void,
      { organizationId: string; email: string; role: string }
    >({
      query: ({ organizationId, email, role }) => ({
        url: `/organizations/${organizationId}/invite`,
        method: "POST",
        body: { email, role },
      }),
    }),
    respondToJoinRequest: builder.mutation<
      void,
      { organizationId: string; requestId: string; status: "ACCEPT" | "REJECT" }
    >({
      query: ({ organizationId, requestId, status }) => ({
        url: `/organizations/${organizationId}/join-requests/${requestId}`,
        method: "PUT",
        body: { status },
      }),
      invalidatesTags: ["Requests"],
    }),
    getDomainOrganization: builder.query<Organization, void>({
      query: () => "user/domain-organization",
      transformErrorResponse: (
        response: FetchBaseQueryError | SerializedError
      ) => {
        if ("status" in response && response.status === 404) {
          return { notFound: true };
        }
        return response;
      },
    }),
  }),
});

export const {
  useGetOrganizationQuery,
  useCreateOrganizationMutation,
  useUpdateOrganizationMutation,
  useInviteMemberMutation,
  useAcceptInvitationMutation,
  useGetJoinRequestsQuery,
  useApproveRequestMutation,
  useRejectRequestMutation,
  useGetMembersQuery,
  useUpdateMemberMutation,
  useDeleteMemberMutation,
  useSearchOrganizationsQuery,
  useJoinOrganizationRequestMutation,
  useUploadOrganizationLogoMutation,
  useInviteUserMutation,
  useRespondToJoinRequestMutation,
  useGetDomainOrganizationQuery,
} = organizationApi;
