import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";
import {
  ChatConversation,
  Message,
  Warning,
  ConversationUpdate,
  Attachment,
  RecentConversation,
} from "@/app/(protected)/chat/types/chat";
import { toast } from "@/hooks/use-toast";
import * as Sentry from "@sentry/nextjs";
import { handleWarnings } from "@/lib/utils/warningUtils";
import { PalType, Pal } from "@/store/types";

export const chatApi = createApi({
  reducerPath: "chatApi",
  baseQuery,
  tagTypes: ["Chat"],
  endpoints: (builder) => ({
    createConversation: builder.mutation<
      ChatConversation,
      { id: string; model: string | null }
    >({
      query: ({ id, model }) => ({
        url: `/chat/conversations`,
        method: "POST",
        body: { id, model },
      }),
      invalidatesTags: ["Chat"],
      async onQueryStarted(_, { queryFulfilled }) {
        try {
          await queryFulfilled;
        } catch (error: any) {
          const isDuplicateError =
            error?.error?.data?.detail?.includes("already exists");

          if (!isDuplicateError) {
            Sentry.captureException(error, {
              tags: {
                operation: "createConversation",
                errorType: "unknown",
              },
            });
          }

          toast({
            variant: "destructive",
            title: "Error",
            description: isDuplicateError
              ? "This conversation ID already exists. Please try again."
              : "Failed to create conversation",
          });
        }
      },
    }),

    getRecentConversations: builder.query<RecentConversation, string | void>({
      query: (pal) => ({
        url: "/chat/conversations",
        method: "GET",
        params: pal ? { pal } : undefined,
      }),
      providesTags: ["Chat"],
    }),

    getConversationWithMessages: builder.query<ConversationUpdate, string>({
      query: (id) => `/chat/conversations/${id}`,
      providesTags: ["Chat"],
      async onQueryStarted(_, { queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          handleWarnings(data.warnings);
        } catch (error) {
          Sentry.captureException(error, {
            tags: { operation: "getConversation" },
          });
        }
      },
    }),

    streamCompletion: builder.mutation<
      void,
      {
        conversation_uuid: string;
        parent_message_uuid: string;
        message: string;
        attachments?: Attachment[];
        model?: string;
      }
    >({
      queryFn: async (arg) => {
        try {
          const response = await fetch("/api/proxy/chat/completion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(arg),
          });

          if (!response.ok) {
            throw new Error("Completion failed");
          }

          return { data: undefined };
        } catch (error) {
          Sentry.captureException(error, {
            tags: {
              operation: "streamCompletion",
            },
          });
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to get response",
          });
          return { error: error as any };
        }
      },
    }),

    pollConversation: builder.query<ConversationUpdate, string>({
      query: (id) => `/chat/conversations/${id}/poll`,
      async onQueryStarted(_, { queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          // Handle new warnings from polling
          data.warnings?.forEach((warning: Warning) => {
            toast({
              variant: warning.level === "error" ? "destructive" : "default",
              title:
                warning.type.charAt(0).toUpperCase() + warning.type.slice(1),
              description: warning.message,
              duration: warning.type === "rate_limit" ? 10000 : 5000,
            });
          });
        } catch (error) {
          Sentry.captureException(error, {
            tags: {
              operation: "pollConversation",
            },
          });
        }
      },
    }),

    updateMessage: builder.mutation<
      {
        message: Message;
        affected_messages: Message[];
      },
      {
        conversationId: string;
        messageId: string;
        content: string;
      }
    >({
      query: ({ conversationId, messageId, content }) => ({
        url: `/chat/conversations/${conversationId}/messages/${messageId}`,
        method: "PATCH",
        body: { content },
      }),
      // Update cache with both edited message and affected messages
      async onQueryStarted({ conversationId }, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;

          // Update edited message and all affected messages
          dispatch(
            chatApi.util.updateQueryData(
              "getConversationWithMessages",
              conversationId,
              (draft) => {
                // Find and update the edited message
                const messageIndex = draft.messages.findIndex(
                  (m) => m.id === data.message.id
                );
                if (messageIndex !== -1) {
                  draft.messages[messageIndex] = data.message;
                }

                // Update all affected messages (usually responses that need regeneration)
                data.affected_messages.forEach((affectedMessage) => {
                  const affectedIndex = draft.messages.findIndex(
                    (m) => m.id === affectedMessage.id
                  );
                  if (affectedIndex !== -1) {
                    draft.messages[affectedIndex] = affectedMessage;
                  }
                });
              }
            )
          );

          // Show toast for affected messages
          if (data.affected_messages.length > 0) {
            toast({
              title: "Message Updated",
              description:
                "Some responses have been regenerated based on your edit.",
              duration: 5000,
            });
          }
        } catch (error) {
          // Handle error
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to update message",
          });
        }
      },
    }),

    getConversation: builder.query<ChatConversation, string>({
      query: (conversationId) => ({
        url: `/chat/conversations/${conversationId}`,
        method: "GET",
      }),
      transformResponse: (response: any) => ({
        id: response.id,
        name: response.name,
        summary: response.summary,
        model: response.model,
        created_at: response.created_at,
        updated_at: response.updated_at,
        messages: response.chat_messages || [],
        settings: {
          preview_feature_uses_artifacts:
            response.settings?.preview_feature_uses_artifacts || false,
          preview_feature_uses_latex:
            response.settings?.preview_feature_uses_latex || null,
          preview_feature_uses_citations:
            response.settings?.preview_feature_uses_citations || null,
          enabled_artifacts_attachments:
            response.settings?.enabled_artifacts_attachments || null,
          enabled_turmeric: response.settings?.enabled_turmeric || null,
        },
        is_starred: response.is_starred,
        project_id: response.project_id,
        current_leaf_message_id: response.current_leaf_message_id,
      }),
    }),
  }),
});

export const {
  useCreateConversationMutation,
  useGetRecentConversationsQuery,
  useGetConversationWithMessagesQuery,
  useStreamCompletionMutation,
  usePollConversationQuery,
  useUpdateMessageMutation,
  useGetConversationQuery,
} = chatApi;
