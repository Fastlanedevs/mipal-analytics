import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";
import { Pal } from "@/store/types";

export const palApi = createApi({
  reducerPath: "palApi",
  baseQuery,
  tagTypes: ["Pal"],
  endpoints: (builder) => ({
    getPals: builder.query<Pal[], void>({
      query: () => "/chat/pals",
      providesTags: ["Pal"],
    }),
  }),
});

export const { useGetPalsQuery } = palApi;
