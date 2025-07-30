import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";
import { SearchResponse } from "@/app/(protected)/chat/types/files";

export const filesApi = createApi({
  reducerPath: "searchApi",
  baseQuery,
  endpoints: (builder) => ({
    getPrefixResults: builder.query<SearchResponse[], string>({
      query: (prefix) => ({
        url: `/knowledge-base/search`,
        method: "GET",
        params: { prefix },
      }),
    }),

    getFullSearchResults: builder.query<SearchResponse[], string>({
      query: (query) => ({
        url: `/knowledge-base/search`,
        method: "POST",
        body: { query },
      }),
    }),

    getFullSearchResultsLazy: builder.query<SearchResponse[], string>({
      query: (query) => ({
        url: `/knowledge-base/search`,
        method: "POST",
        body: { query },
      }),
    }),
  }),
});

export const {
  useGetPrefixResultsQuery,
  useGetFullSearchResultsQuery,
  useLazyGetFullSearchResultsQuery,
} = filesApi;
