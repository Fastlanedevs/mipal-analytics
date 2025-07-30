import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery"; // Assuming baseQuery is defined similarly to formDataBaseQuery

// New interface for the suggestion content from backend
export interface SuggestionContent {
  title: string;
  explanation: string;
  question: string;
  category: string;
}

interface Recommendations {
  recommendations: SuggestionContent[];
}

interface RecommendationRequest {
  database_uid: string;
  table_uid: string;
  count: number;
}

interface ErrorDetail {
  loc: [string, number];
  msg: string;
  type: string;
}

export const intentApi = createApi({
  reducerPath: "intentApi",
  baseQuery: baseQuery,
  tagTypes: ["Recommendation"],
  endpoints: (builder) => ({
    getRecommendations: builder.query<Recommendations, RecommendationRequest>({
      query: (request) => ({
        url: "/analytics/recommendation",
        method: "POST",
        body: request,
      }),
      providesTags: ["Recommendation"],
    }),
  }),
});

export const { useGetRecommendationsQuery } = intentApi;
