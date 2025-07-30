import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery, formDataBaseQuery } from "./baseQuery";

export type DatabaseType = "postgres" | "csv";

// Column interface
export interface Column {
  uid: string;
  name: string;
  data_type: string;
  description: string;
  is_primary_key: boolean;
  is_nullable: boolean;
  default: string;
  stats: Record<string, any>;
}

// Table interface
export interface TableStats {
  uid: string;
  name: string;
  schema_name: string;
  description: string;
  columns: Column[];
  row_count: number;
  last_updated: string;
}

// Database interface
export interface Database {
  uid: string;
  name: string;
  type: string;
  description: string;
  tables: TableStats[];
  user_id: string;
  integration_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Add new interface for the upload response
export interface CSVUploadResponse {
  database_name: string;
  files: string[];
  description?: string;
  settings?: string;
  tables?: TableStats[];
}

// API 1
export const analyticsApi = createApi({
  reducerPath: "analyticsApi",
  baseQuery: baseQuery,
  tagTypes: ["Databases"],
  endpoints: (builder) => ({
    getDatabases: builder.query<Database[], void>({
      query: () => "/analytics/databases",
      providesTags: ["Databases"],
    }),
  }),
});

export const analyticsApiFormData = createApi({
  reducerPath: "analyticsApiFormData",
  baseQuery: formDataBaseQuery,
  tagTypes: ["CSVDatabase", "Analytics"],
  endpoints: (builder) => ({
    uploadCSV: builder.mutation<any, FormData>({
      query: (formData) => ({
        url: "/analytics/csv/databases",
        method: "POST",
        body: formData,
        formData: true,
      }),
      invalidatesTags: ["CSVDatabase"],
    }),
    uploadFilesToDatabase: builder.mutation<
      CSVUploadResponse,
      { databaseUid: string; formData: FormData }
    >({
      query: ({ databaseUid, formData }) => ({
        url: `/analytics/csv/databases/${databaseUid}/files`,
        method: "PUT",
        body: formData,
        formData: true,
      }),
      invalidatesTags: ["CSVDatabase"],
    }),
    uploadExcel: builder.mutation<any, FormData>({
      query: (formData) => ({
        url: "/analytics/excel/database",
        method: "POST",
        body: formData,
        formData: true,
      }),
      invalidatesTags: ["CSVDatabase"],
    }),
  }),
});

export const { useGetDatabasesQuery } = analyticsApi;

export const {
  useUploadCSVMutation,
  useUploadFilesToDatabaseMutation,
  useUploadExcelMutation,
} = analyticsApiFormData;
