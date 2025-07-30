import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";

interface CheckoutSession {
  lookup_key: string;
  success_url: string;
  cancel_url: string;
  client_reference_id?: string;
  email?: string;
}

interface PortalSession {
  customer_id: string;
  return_url: string;
}

export const stripeApi = createApi({
  reducerPath: "stripeApi",
  baseQuery,
  endpoints: (builder) => ({
    createCheckoutSession: builder.mutation<{ url: string }, CheckoutSession>({
      query: (data) => ({
        url: "/stripe/create-checkout-session",
        method: "POST",
        body: data,
      }),
    }),
    retrieveSession: builder.query<any, string>({
      query: (sessionId) => ({
        url: `/stripe/session/${sessionId}`,
        method: "GET",
      }),
    }),
    createPortalSession: builder.mutation<{ url: string }, PortalSession>({
      query: (data) => ({
        url: "/stripe/create-portal-session",
        method: "POST",
        body: data,
      }),
    }),
  }),
});

export const {
  useCreateCheckoutSessionMutation,
  useRetrieveSessionQuery,
  useCreatePortalSessionMutation,
} = stripeApi;
