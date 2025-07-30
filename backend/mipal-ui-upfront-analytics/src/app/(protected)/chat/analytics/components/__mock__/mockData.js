export const mockChartArtifacts = {
  barChart: {
    artifact_type: "chart",
    content: {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      data: {
        values: [
          { month: "Jan", sales: 2420, profit: 530, category: "Electronics" },
          { month: "Feb", sales: 3580, profit: 810, category: "Electronics" },
          { month: "Mar", sales: 4150, profit: 920, category: "Electronics" },
          { month: "Apr", sales: 4890, profit: 1100, category: "Apparel" },
          { month: "May", sales: 5520, profit: 1250, category: "Apparel" },
          { month: "Jun", sales: 6180, profit: 1480, category: "Apparel" },
          { month: "Jul", sales: 6850, profit: 1620, category: "Home Goods" },
          { month: "Aug", sales: 7240, profit: 1780, category: "Home Goods" },
          { month: "Sep", sales: 6920, profit: 1590, category: "Home Goods" },
          { month: "Oct", sales: 5850, profit: 1320, category: "Food" },
          { month: "Nov", sales: 4980, profit: 1150, category: "Food" },
          { month: "Dec", sales: 5640, profit: 1280, category: "Food" },
        ],
      },
      mark: "bar",
      encoding: {
        x: { field: "month", type: "nominal" },
        y: { field: "sales", type: "quantitative" },
        color: { field: "category", type: "nominal" },
      },
      description: "A bar chart showing the sales by month and category",
    },
  },

  timeSeriesChart: {
    artifact_type: "chart",
    content: {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      data: {
        values: [
          {
            date: "2023-01-01",
            value: 1250,
            type: "Revenue",
            confidence: 0.95,
          },
          {
            date: "2023-02-01",
            value: 1580,
            type: "Revenue",
            confidence: 0.92,
          },
          {
            date: "2023-03-01",
            value: 2150,
            type: "Revenue",
            confidence: 0.94,
          },
          {
            date: "2023-04-01",
            value: 2480,
            type: "Revenue",
            confidence: 0.93,
          },
          { date: "2023-01-01", value: 850, type: "Costs", confidence: 0.96 },
          { date: "2023-02-01", value: 920, type: "Costs", confidence: 0.95 },
          { date: "2023-03-01", value: 1150, type: "Costs", confidence: 0.93 },
          { date: "2023-04-01", value: 1280, type: "Costs", confidence: 0.94 },
        ],
      },
      mark: "line",
      encoding: {
        x: { field: "date", type: "temporal" },
        y: { field: "value", type: "quantitative" },
        color: { field: "type", type: "nominal" },
      },
    },
  },

  scatterChart: {
    artifact_type: "chart",
    content: {
      $schema: "https://vega.github.io/schema/vega-lite/v5.json",
      data: {
        values: [
          { x: 45, y: 85, size: 120, category: "Region A", density: 0.75 },
          { x: 52, y: 92, size: 150, category: "Region A", density: 0.82 },
          { x: 65, y: 78, size: 180, category: "Region A", density: 0.68 },
          { x: 72, y: 91, size: 140, category: "Region B", density: 0.91 },
          { x: 58, y: 88, size: 160, category: "Region B", density: 0.85 },
          { x: 81, y: 95, size: 200, category: "Region B", density: 0.88 },
        ],
      },
      mark: "point",
      encoding: {
        x: { field: "x", type: "quantitative" },
        y: { field: "y", type: "quantitative" },
        size: { field: "size", type: "quantitative" },
        color: { field: "category", type: "nominal" },
      },
    },
  },
};

export const mockSuggestions = {
  query: "What is the trend of order values over the past year?",
  recommendations: [
    {
      suggestion: "What is the trend of total order values over the past year?",
      code: {
        type: "sql",
        text: "SELECT DATE_TRUNC('month', to_timestamp(order_purchase_timestamp, 'YYYY-MM-DD HH24:MI:SS')) AS month,\nSUM(p.payment_value) AS total_order_value\nFROM orders o\nJOIN order_payments p ON o.order_id = p.order_id\nWHERE o.order_purchase_timestamp >= NOW() - INTERVAL '1 year'\nGROUP BY month\nORDER BY month;",
        description:
          "This query provides the total order values aggregated by month over the past year. It helps to visualize the trend in order values, indicating growth or decline in sales performance.",
        category: "time_series",
        visualization: "line_chart",
      },
      recommendation_type: "query_based",
    },
    {
      suggestion: "Can you show me the monthly growth rate in order values?",
      code: {
        type: "sql",
        text: "WITH monthly_totals AS (\n  SELECT DATE_TRUNC('month', to_timestamp(order_purchase_timestamp, 'YYYY-MM-DD HH24:MI:SS')) AS month,\n  SUM(p.payment_value) AS total_order_value\n  FROM orders o\n  JOIN order_payments p ON o.order_id = p.order_id\n  GROUP BY month\n  ORDER BY month\n)\nSELECT month,\n  total_order_value,\n  ((total_order_value - LAG(total_order_value) OVER (ORDER BY month)) / LAG(total_order_value) OVER (ORDER BY month) * 100) AS growth_rate\nFROM monthly_totals;",
        description:
          "This query calculates the month-over-month growth rate in order values, helping identify periods of significant growth or decline.",
        category: "time_series",
        visualization: "combo_chart",
      },
      recommendation_type: "insight_based",
    },
    {
      suggestion: "What's the seasonal pattern in our order values?",
      code: {
        type: "sql",
        text: "SELECT EXTRACT(MONTH FROM to_timestamp(order_purchase_timestamp, 'YYYY-MM-DD HH24:MI:SS')) AS month,\nAVG(p.payment_value) AS avg_order_value\nFROM orders o\nJOIN order_payments p ON o.order_id = p.order_id\nGROUP BY month\nORDER BY month;",
        description:
          "This query analyzes the average order values by month to identify seasonal patterns in purchasing behavior.",
        category: "time_series",
        visualization: "bar_chart",
      },
      recommendation_type: "pattern_based",
    },
  ],
};

export const mockArtifacts = [
  {
    artifact_type: "code",
    content:
      "-- First CTE to get top 5 payment methods\\nWITH TopPaymentMethods AS (\\n    SELECT\\n        ",
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "code_type",
    content: "sql" /*sql or python*/,
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "explanation", //"overview"
    content:
      "Code extracted from text output: AgentRunResult(data=CodeGenerationResult(code='-- ...",
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "data",
    content:
      '[{"payment_method": "credit_card", "city": "New York", "volume": 1250000, "year": 2023}, {"payment_method": "credit_card", "city": "Los Angeles", "volume": 980000, "year": 2023}, {"payment_method": "paypal", "city": "New York", "volume": 850000, "year": 2023}, {"payment_method": "paypal", "city": "Chicago", "volume": 720000, "year": 2023}, {"payment_method": "debit_card", "city": "Houston", "volume": 650000, "year": 2023}, {"payment_method": "credit_card", "city": "New York", "volume": 1150000, "year": 2022}, {"payment_method": "credit_card", "city": "Los Angeles", "volume": 920000, "year": 2022}, {"payment_method": "paypal", "city": "New York", "volume": 750000, "year": 2022}, {"payment_method": "paypal", "city": "Chicago", "volume": 680000, "year": 2022}, {"payment_method": "debit_card", "city": "Houston", "volume": 590000, "year": 2022}]',
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "data_summary",
    content:
      "Unable to generate a comprehensive summary of the data: 'str' object has no attribute 'key_points'. The data was generated in response to the query: 'TOP 5 most prefferred payment method and how much volume was done yearly by top 5 cities'.",
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "rich_data_summary", // "overview"
    content:
      '{"summary": "Unable to generate a comprehensive summary of the data: \'str\' object has no attribute \'key_points\'. The data was generated in response to the query: \'TOP 5 most prefferred payment method and how much volume was done yearly by top 5 cities\'.", "key_points": ["The data structure could not be fully analyzed.", "Please review the raw data to understand its contents.", "Consider refining your query for more specific results."], "data_shape": {"error": "Data shape could not be determined"}}',
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "metadata", // just for me to understand the data
    content:
      '{"total_rows": 10, "returned_rows": 10, "data_source": {"type": "postgres", "id": "6a04d422c6f44465a6bce5b6f79547d7"}}',
    language: null,
    title: null,
    file_type: null,
  },
  {
    artifact_type: "columns", // 'headers in table'
    content:
      '[{"name": "payment_method", "display_name": "Payment Method", "type": "OBJECT", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["credit_card", "paypal", "debit_card"]}, {"name": "city", "display_name": "City", "type": "OBJECT", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["Chicago", "Los Angeles", "Houston", "New York"]}, {"name": "volume", "display_name": "Volume", "type": "INT64", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["720000", "1250000", "850000", "980000", "650000"]}, {"name": "year", "display_name": "Year", "type": "INT64", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["2023"]}]',
    language: null,
    title: null,
    file_type: null,
  },
];

export const postgresDatasource = {
  database_name: "my_postgre_db",
  id: "12DZEAZEDF",
  type: "postgre",
  tables: [],
};

export const csvDatasource = {
  database_name: "my_csv_db",
  id: "12DZEAZEDF",
  type: "csv",
  tables: [
    {
      name: "Canadasalesdata",
      id: "12DZEAZEDF",
      columns: [
        "Model",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Sumofsales",
        "Category",
        "Year",
      ],
      row_count: 0,
      storage_url: "",
      description: "",
      column_stats: null,
    },
    {
      name: "Canadasalesdata2",
      id: "133243a",
      columns: [
        "Model",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Sumofsales",
        "Category",
        "Year",
      ],
      row_count: 0,
      storage_url: "",
      description: "",
      column_stats: null,
    },
  ],
};

export const messagesMock = {
  id: "6d4a611c2efd7448b0df6026f39ea121",
  name: "New Conversation",
  model: "ANALYST_PAL",
  created_at: "2025-03-03T00:05:47.480014Z",
  updated_at: "2025-03-03T00:06:56.689890Z",
  is_starred: false,
  current_leaf_message_id: "a534e906-4803-4e71-8527-34951dbd5efa",
  chat_messages: [
    {
      id: "246d9d9244b74cc38959c87abb7f3bbc",
      role: "user",
      content:
        "TOP 5 most prefferred payment method and how much volume was done yearly by top 5 cities",
      conversation_id: "",
      parent_message_id: "",
      model: "ANALYST_PAL",
      suggestions: [],
      people: [],
      documents: [],
      follow_up_questions: [],
      skip_option: false,
      codes: [],
      artifacts: [],
      attachments: [
        {
          file_name: "",
          file_size: 1234,
          file_type: "",
          extracted_content: " ",
        },
      ],
      files: [],
      edited_at: "",
      edited_by: "",
      regenerating: false,
      original_content: [],
      stop_reason: null,
      stop_sequence: null,
      created_at: "2025-03-03T00:05:57.027625Z",
      index: 0,
      truncated: false,
      sender: "user",
    },
    {
      id: "a534e906-4803-4e71-8527-34951dbd5efa",
      role: "assistant",
      content:
        "# Analysis Results\n\nThe analysis highlights that the 'credit card' is the most preferred payment method, with 'New York' and 'Los Angeles' leading in transaction volumes in both 2022 and 2023. It also shows consistent growth in transaction volume across top cities, demonstrating a solid trend in payment preferences and city contribution to overall volume.\n\n## Key Insights\n\n- Credit cards are the most preferred payment method with consistently high volumes across both 2022 and 2023. New York leads in total volume with 1.25 million in 2023 and 1.15 million in 2022, followed by Los Angeles with 980,000 in 2023 and 920,000 in 2022.\n- Paypal is the second most used payment method, particularly notable in New York and Chicago. There's an increase in volume from 750,000 in 2022 to 850,000 in 2023 in New York. Chicago maintains a strong usage at 680,000 despite a slight increase to 720,000 in 2023.\n- Transaction volumes have shown steady growth across major cities from 2022 to 2023, indicating an overall increase in transaction activities, potentially linked to economic growth or increased adoption of digital payments.\n",
      conversation_id: "",
      parent_message_id: "",
      model: "ANALYST_PAL",
      suggestions: [],
      people: [],
      documents: [],
      follow_up_questions: [],
      skip_option: false,
      codes: [],
      artifacts: [
        {
          artifact_type: "code",
          content:
            "-- First CTE to get top 5 payment methods\\nWITH TopPaymentMethods AS (\\n    SELECT\\n        ",
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "code_type",
          content: "sql" /*sql or python*/,
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "explanation", //"overview"
          content:
            "Code extracted from text output: AgentRunResult(data=CodeGenerationResult(code='-- ...",
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "data",
          content:
            '[{"payment_method": "credit_card", "city": "New York", "volume": 1250000, "year": 2023}, {"payment_method": "credit_card", "city": "Los Angeles", "volume": 980000, "year": 2023}, {"payment_method": "paypal", "city": "New York", "volume": 850000, "year": 2023}, {"payment_method": "paypal", "city": "Chicago", "volume": 720000, "year": 2023}, {"payment_method": "debit_card", "city": "Houston", "volume": 650000, "year": 2023}, {"payment_method": "credit_card", "city": "New York", "volume": 1150000, "year": 2022}, {"payment_method": "credit_card", "city": "Los Angeles", "volume": 920000, "year": 2022}, {"payment_method": "paypal", "city": "New York", "volume": 750000, "year": 2022}, {"payment_method": "paypal", "city": "Chicago", "volume": 680000, "year": 2022}, {"payment_method": "debit_card", "city": "Houston", "volume": 590000, "year": 2022}]',
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "data_summary",
          content:
            "Unable to generate a comprehensive summary of the data: 'str' object has no attribute 'key_points'. The data was generated in response to the query: 'TOP 5 most prefferred payment method and how much volume was done yearly by top 5 cities'.",
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "rich_data_summary", // "overview"
          content:
            '{"summary": "Unable to generate a comprehensive summary of the data: \'str\' object has no attribute \'key_points\'. The data was generated in response to the query: \'TOP 5 most prefferred payment method and how much volume was done yearly by top 5 cities\'.", "key_points": ["The data structure could not be fully analyzed.", "Please review the raw data to understand its contents.", "Consider refining your query for more specific results."], "data_shape": {"error": "Data shape could not be determined"}}',
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "metadata", // just for me to understand the data
          content:
            '{"total_rows": 10, "returned_rows": 10, "data_source": {"type": "postgres", "id": "6a04d422c6f44465a6bce5b6f79547d7"}}',
          language: null,
          title: null,
          file_type: null,
        },
        {
          artifact_type: "columns", // 'headers in table'
          content:
            '[{"name": "payment_method", "display_name": "Payment Method", "type": "OBJECT", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["credit_card", "paypal", "debit_card"]}, {"name": "city", "display_name": "City", "type": "OBJECT", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["Chicago", "Los Angeles", "Houston", "New York"]}, {"name": "volume", "display_name": "Volume", "type": "INT64", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["720000", "1250000", "850000", "980000", "650000"]}, {"name": "year", "display_name": "Year", "type": "INT64", "icon": "\\ud83d\\udd20", "sortable": true, "filterable": true, "sample_values": ["2023"]}]',
          language: null,
          title: null,
          file_type: null,
        },
      ],
      attachments: [],
      files: [],
      edited_at: "",
      edited_by: "",
      regenerating: false,
      original_content: [],
      stop_reason: "end_turn",
      stop_sequence: null,
      created_at: "2025-03-03T00:06:56.054150Z",
      index: 0,
      truncated: false,
      sender: "assistant",
    },
  ],
};

export const datasourcesMock = [postgresDatasource, csvDatasource];

/*

Sample meta_content for streaming intermediate yeild results
{
                "type": "meta_content",
                'meta_content': {
                    "id": "1",
                    "title": "Starting analysis...",
                    "description": [{"title":"description of whats happening"
"execution": "pythoncode or sqlcode", "status":"inprogress"}]
                }
            }

*/

export const metaContentMock = {
  type: "meta_content",
  meta_content: [
    {
      id: "1",
      title: "Starting analysis...",
      description: [
        {
          title: "description of whats happening",
          execution: "pythoncode or sqlcode",
          status: "inprogress",
        },
      ],
    },
    {
      id: "2",
      title: "Starting analysis...",
      description: [
        {
          title: "description of whats happening",
          execution: "pythoncode or sqlcode",
          status: "inprogress",
        },
      ],
    },
    {
      id: "3",
      title: "Starting analysis...",
      description: [
        {
          title: "description of whats happening",
          execution: "pythoncode or sqlcode",
          status: "inprogress",
        },
      ],
    },
  ],
};
