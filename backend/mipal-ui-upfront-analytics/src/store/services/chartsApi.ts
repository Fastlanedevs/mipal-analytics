import { createApi } from "@reduxjs/toolkit/query/react";
import { baseQuery } from "./baseQuery";

// Interface for the request payload
interface ChartRequest {
  message_id: string;
  visibility?: "PRIVATE" | "PUBLIC";
  force_create?: boolean;
  adjustment_query?: string;
}

// Interface for chart data values
interface ChartDataValue {
  territory_id: string;
  territory_description: string;
  employee_count: number;
}

// Interface for field mappings
interface FieldMappings {
  x_axis: string[];
  y_axis: string[];
  color: string[];
  theta: string[];
  x_offset: string[];
}

// Interface for recommended combination
interface RecommendedCombination {
  chart_type: string;
  x_axis?: string;
  y_axis?: string;
  theta?: string;
  color?: string;
  x_offset?: string;
  description: string;
}

// Interface for current settings
interface CurrentSettings {
  chart_type: string;
  x_axis: string;
  y_axis: string;
  color: string;
}

// Interface for available adjustments
interface AvailableAdjustments {
  chart_types: string[];
  field_mappings: FieldMappings;
  recommended_combinations: RecommendedCombination[];
  current_settings: CurrentSettings;
}

// Interface for alternative visualization field mappings
interface AlternativeVisualizationFieldMappings {
  x_axis: string | null;
  y_axis: string | null;
  color: string | null;
  theta: string | null;
  column: string | null;
  tooltip: string[];
}

// Interface for alternative visualization
interface AlternativeVisualization {
  chart_type: string;
  description: string;
  field_mappings: AlternativeVisualizationFieldMappings;
}

// Interface for alternative visualization query
export interface AlternativeVisualizationQuery {
  query: string;
  description: string;
}

// Interface for the response payload
interface ChartResponse {
  id: string;
  title: string;
  description: string;
  chart_type: string;
  chart_schema: {
    $schema: string;
    data: {
      values: ChartDataValue[];
    };
    mark: string;
    encoding: {
      x?: {
        field: string;
        type: string;
        axis?: {
          title: string;
        };
        sort?: null | "ascending" | "descending";
      };
      y?: {
        field: string;
        type: string;
        axis?: {
          title: string;
        };
        scale?: {
          domain?: number[];
        };
        title?: string;
      };
      color?: {
        field: string;
        type: string;
        scale?: {
          domain?: number[];
          range?: string[];
        };
        legend?: {
          title: string;
          orient?: string;
        };
        condition?: {
          test: string;
          value: string;
          value2: string;
        };
      };
      tooltip?: Array<{
        field: string;
        type: string;
        title: string;
      }>;
    };
    title: string;
  };
  chart_data: ChartDataValue[];
  message_id: string;
  visibility: "PRIVATE" | "PUBLIC";
  created_at: string;
  updated_at: string;
  last_refreshed_at: string;
  available_adjustments: AvailableAdjustments;
  alternative_visualizations: AlternativeVisualization[];
  alternative_visualization_queries: AlternativeVisualizationQuery[];
}

// Interface for chart history item
interface ChartHistoryItem {
  id: string;
  chart_id: string;
  chart_type: string;
  chart_schema: Record<string, any>;
  chart_data: Record<string, any>[];
  modified_by: string;
  created_at: string;
}

// Interface for chart history response
interface ChartHistoryResponse {
  items: ChartHistoryItem[];
  total: number;
}

export const chartsApi = createApi({
  reducerPath: "chartsApi",
  baseQuery: baseQuery,
  tagTypes: ["Chart"],
  endpoints: (builder) => ({
    getChartData: builder.mutation<ChartResponse, ChartRequest>({
      query: (data) => {
        // Ensure the input is properly formatted with message_id
        const formattedData = {
          message_id: typeof data === "string" ? data : data.message_id,
          force_create: data.force_create,
          adjustment_query: data.adjustment_query,
        };
        return {
          url: "/analytics/charts",
          method: "POST",
          body: formattedData,
        };
      },
      invalidatesTags: ["Chart"],
    }),
    getChartHistory: builder.query<ChartHistoryResponse, ChartResponse["id"]>({
      query: (chartId) => ({
        url: `/analytics/charts/${chartId}/history`,
        method: "GET",
      }),
    }),
    getChartsByMessage: builder.query<ChartResponse[], string>({
      query: (messageId) => ({
        url: `/analytics/charts/by-message/${messageId}`,
        method: "GET",
      }),
      transformErrorResponse: (response) => {
        if (response.status === 422) {
          return {
            status: response.status,
            data: response.data,
            message: "Validation error occurred",
          };
        }
        return response;
      },
    }),
  }),
});

export const {
  useGetChartDataMutation,
  useGetChartHistoryQuery,
  useGetChartsByMessageQuery,
} = chartsApi;
