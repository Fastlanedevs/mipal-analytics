import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { FetchBaseQueryError } from "@reduxjs/toolkit/query";

export const SYNC_STATUS = {
  PROCESSING: "PROCESSING",
  STARTED: "STARTED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  NEVER: "NEVER",
} as const;

type SyncStatusType = (typeof SYNC_STATUS)[keyof typeof SYNC_STATUS];

export interface SyncStatus {
  last_sync_process_id: string;
  integration_id: string;
  integration_type: string;
  last_sync_status: SyncStatusType;
  last_sync_start_time: string;
  last_sync_end_time: string | null;
  last_successful_sync: string | null;
}

interface StartSyncResponse {
  sync_process_id: string;
  integration_type: string;
  integration_id: string;
  last_sync_status: SyncStatusType;
  last_sync_start_time: string;
  sync_end_time: string;
}

export const isSyncInProgress = (status?: SyncStatus | null): boolean => {
  if (!status) return false;
  const inProgressStatuses: SyncStatusType[] = [
    SYNC_STATUS.PROCESSING,
    SYNC_STATUS.STARTED,
  ];
  return inProgressStatuses.includes(status.last_sync_status);
};

export const syncApi = createApi({
  reducerPath: "syncApi",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api/proxy",
    prepareHeaders: (headers, { getState }) => {
      return headers;
    },
  }),
  tagTypes: ["Sync"],
  endpoints: (builder) => ({
    startSync: builder.mutation<StartSyncResponse, string>({
      query: (instanceId) => ({
        url: `/integrations/${instanceId}/sync`,
        method: "POST",
        body: {},
      }),
      invalidatesTags: (result, error, instanceId) => [
        { type: "Sync", id: instanceId },
      ],
      async onQueryStarted(instanceId, { dispatch, queryFulfilled }) {
        dispatch(
          syncApi.util.updateQueryData("getSyncStatus", instanceId, (draft) => {
            if (draft) {
              draft.last_sync_status = SYNC_STATUS.STARTED;
              draft.last_sync_start_time = new Date().toISOString();
            }
          })
        );

        try {
          const { data } = await queryFulfilled;
          dispatch(
            syncApi.util.updateQueryData(
              "getSyncStatus",
              instanceId,
              (draft) => {
                if (draft) {
                  draft.last_sync_process_id = data.sync_process_id;
                  draft.last_sync_status = data.last_sync_status;
                  draft.last_sync_start_time = data.last_sync_start_time;
                  draft.last_sync_end_time = data.sync_end_time;
                }
              }
            )
          );
        } catch (error) {
          dispatch(
            syncApi.util.updateQueryData(
              "getSyncStatus",
              instanceId,
              (draft) => {
                if (draft) {
                  draft.last_sync_status = SYNC_STATUS.FAILED;
                  draft.last_sync_end_time = new Date().toISOString();
                }
              }
            )
          );
          console.error("Error in sync mutation:", error);
        }
      },
    }),

    getSyncStatus: builder.query<SyncStatus | null, string>({
      query: (instanceId) => `/integrations/${instanceId}/sync`,
      providesTags: (result, error, instanceId) => [
        { type: "Sync", id: instanceId },
      ],
      transformResponse: (response: unknown) => {
        if (!response) return null;

        const syncResponse = response as SyncStatus;
        return {
          ...syncResponse,
          last_sync_start_time: new Date(
            syncResponse.last_sync_start_time
          ).toISOString(),
          last_sync_end_time: syncResponse.last_sync_end_time
            ? new Date(syncResponse.last_sync_end_time).toISOString()
            : null,
          last_successful_sync: syncResponse.last_successful_sync
            ? new Date(syncResponse.last_successful_sync).toISOString()
            : null,
        };
      },
      transformErrorResponse: (
        response: FetchBaseQueryError | { status: number }
      ) => {
        console.error("Sync status error:", response);
        if ("status" in response && response.status === 404) {
          return null;
        }
        throw response;
      },
    }),
  }),
});

export const { useStartSyncMutation, useGetSyncStatusQuery } = syncApi;
