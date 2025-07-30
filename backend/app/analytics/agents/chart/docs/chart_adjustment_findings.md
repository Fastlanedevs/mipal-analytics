# Chart Adjustment API Documentation and Findings

## Overview
The chart adjustment API allows for modification of existing charts by changing the visualization type or adjusting which fields are used for various visualization components. This document outlines the structure of the chart adjustment API, findings from testing, and recommendations for implementation.

## API Endpoint
```
POST /analytics/charts/{chart_id}/adjust
```

## Request Structure
```json
{
  "adjustment_options": {
    "chart_type": "pie",
    "theta": "total_value",
    "color": "payment_type",
    "x_axis": null,
    "y_axis": null,
    "x_offset": null
  }
}
```

### Fields Explanation:
- `chart_type`: The type of chart to convert to (e.g., "bar", "pie", "line")
- `theta`: The field to use for the pie chart slice sizes (required for pie charts)
- `color`: The field to use for coloring elements
- `x_axis`: The field to use for the x-axis
- `y_axis`: The field to use for the y-axis
- `x_offset`: The field to use for grouping or offsetting (used in grouped bar charts)

## Available Chart Adjustments
The `available_adjustments` field in the chart response provides information about what fields can be used for different chart components and which chart types are available:

```json
{
  "chart_types": ["bar", "line", "pie", "grouped_bar", "stacked_bar", "area", "multi_line"],
  "field_mappings": {
    "x_axis": ["payment_type"],
    "y_axis": ["total_value"],
    "color": ["payment_type", "total_value"],
    "theta": ["total_value"],
    "x_offset": ["payment_type"]
  },
  "recommended_combinations": [
    {
      "chart_type": "bar",
      "x_axis": "payment_type",
      "y_axis": "total_value",
      "description": "Bar chart showing total_value by payment_type"
    },
    {
      "chart_type": "pie",
      "theta": "total_value",
      "color": "payment_type",
      "description": "Pie chart showing distribution of total_value across payment_type"
    }
  ],
  "current_settings": {
    "chart_type": "bar",
    "x_axis": "payment_type",
    "y_axis": "total_value",
    "color": "payment_type"
  }
}
```

## Common Chart Type Examples

### Bar Chart
```json
{
  "adjustment_options": {
    "chart_type": "bar",
    "x_axis": "payment_type",
    "y_axis": "total_value",
    "color": "payment_type"
  }
}
```

### Pie Chart
```json
{
  "adjustment_options": {
    "chart_type": "pie",
    "theta": "total_value",
    "color": "payment_type"
  }
}
```

### Line Chart
```json
{
  "adjustment_options": {
    "chart_type": "line",
    "x_axis": "date_field",
    "y_axis": "numeric_value"
  }
}
```

### Grouped Bar Chart
```json
{
  "adjustment_options": {
    "chart_type": "grouped_bar",
    "x_axis": "main_category",
    "y_axis": "numeric_value",
    "x_offset": "sub_category",
    "color": "sub_category"
  }
}
```

## Technical Findings

During testing, we found the following:

1. The API requires a valid authentication token.
2. If the LLM agent fails to generate a valid adjustment, a fallback mechanism preserves the original chart.
3. Validation errors may occur if the requested adjustment is not compatible with the data.
4. The chart adjustment is fully driven by the LLM agent, which may occasionally fail to produce valid results.
5. Recent fixes improved data type recognition, especially for FLOAT64 fields.
6. The API now correctly recognizes theta fields for pie charts.

## Implementation Recommendations

1. **Check Available Adjustments**: Always check the `available_adjustments` field before attempting to adjust a chart to ensure the requested fields are available for the desired chart type.

2. **Use Recommended Combinations**: The `recommended_combinations` field provides tested combinations that are known to work well with the data.

3. **Handle Failures Gracefully**: If the adjustment fails, the API will typically return the original chart. Implement client-side error handling to notify users appropriately.

4. **Field Validation**: Validate that numeric fields are used for y-axis and theta, and categorical fields for color and x-axis components.

5. **Authentication**: Ensure a valid authentication token is included in the request headers.

## Client-side Example

```javascript
async function adjustChart(chartId, adjustmentOptions) {
  try {
    const response = await fetch(`/analytics/charts/${chartId}/adjust`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ adjustment_options: adjustmentOptions })
    });
    
    if (!response.ok) {
      throw new Error('Failed to adjust chart');
    }
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Error adjusting chart:', error);
    return null;
  }
}

// Example usage for pie chart
adjustChart('1c9e2459-124f-4d28-95aa-5aaa1dd1101e', {
  chart_type: 'pie',
  theta: 'total_value',
  color: 'payment_type'
});
``` 