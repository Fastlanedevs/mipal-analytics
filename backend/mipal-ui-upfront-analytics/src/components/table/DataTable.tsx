import {
  DataContent,
  MetadataContent,
  ColumnsContent,
} from "@/app/(protected)/chat/types/chat";

interface DataTableProps {
  content: any;
  columnsContent?: ColumnsContent;
  metadataContent?: MetadataContent;
  showColumnTypes?: boolean;
  showColumnIcons?: boolean;
}

export const DataTable = ({
  content,
  columnsContent,
  metadataContent,
  showColumnTypes = false,
  showColumnIcons = false,
}: DataTableProps) => {
  // Helper function to format numbers with commas
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(num);
  };

  // Helper function to render cell values properly handling booleans
  const renderCellValue = (value: any, column: string) => {
    // Handle null/undefined
    if (value === null || value === undefined) {
      return "";
    }

    // Handle boolean values with tick/cross icons
    if (typeof value === "boolean") {
      return value.toString();
    }

    // Handle specific column formatting
    if (column === "volume" || column === "total_volume") {
      return `${formatNumber(value)}`;
    }

    if (column === "city" || column === "customer_city") {
      return value
        .split(" ")
        .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    }

    if (column === "payment_type" || column === "payment_method") {
      return value
        .split("_")
        .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    }

    return value;
  };

  // Parse content if it's a string
  let parsedContent: any = content;
  if (typeof content === "string") {
    try {
      parsedContent = JSON.parse(content);
    } catch (e) {
      console.error("Error parsing data content:", e);
      return <div>Error parsing data content</div>;
    }
  }

  // Get results from parsed content
  const results = Array.isArray(parsedContent)
    ? parsedContent
    : parsedContent.results || [];

  // Get column headers from the first result object
  const columns = results.length > 0 ? Object.keys(results[0]) : [];

  // Parse columns content if it's a string
  let parsedColumnsContent: any[] = [];
  if (columnsContent) {
    if (typeof columnsContent === "string") {
      try {
        parsedColumnsContent = JSON.parse(columnsContent as string);
      } catch (e) {
        console.error("Error parsing columns content:", e);
      }
    } else {
      parsedColumnsContent = columnsContent as any;
    }
  }

  // Create a map of column names to display names
  const columnDisplayNames: Record<string, string> = {};
  if (parsedColumnsContent && Array.isArray(parsedColumnsContent)) {
    parsedColumnsContent.forEach((column: any) => {
      if (column.name && column.display_name) {
        columnDisplayNames[column.name] = column.display_name;
      }
    });
  } else if (metadataContent?.columns) {
    metadataContent.columns.forEach((column: any) => {
      columnDisplayNames[column.name] = column.display_name;
    });
  }

  return (
    <table className="w-full caption-bottom text-sm">
      <thead className="sticky top-0 bg-background z-10 border-b">
        <tr>
          {columns.map((column) => (
            <th
              key={column}
              className="h-12 px-2 text-left font-medium bg-muted/50 whitespace-nowrap"
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  {showColumnIcons &&
                    parsedColumnsContent &&
                    Array.isArray(parsedColumnsContent) &&
                    parsedColumnsContent.find((col: any) => col.name === column)
                      ?.icon && (
                      <span className="text-primary">
                        {
                          parsedColumnsContent.find(
                            (col: any) => col.name === column
                          )?.icon
                        }
                      </span>
                    )}
                  <span className="font-semibold">
                    {columnDisplayNames[column] || column}
                  </span>
                </div>
                {showColumnTypes &&
                  parsedColumnsContent &&
                  Array.isArray(parsedColumnsContent) &&
                  parsedColumnsContent.find((col: any) => col.name === column)
                    ?.type && (
                    <span className="text-xs text-muted-foreground mt-1">
                      {
                        parsedColumnsContent.find(
                          (col: any) => col.name === column
                        )?.type
                      }
                    </span>
                  )}
              </div>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {results.map((row: any, index: number) => (
          <tr
            key={index}
            className={`transition-colors hover:bg-muted/30 data-[state=selected]:bg-muted ${
              index !== results.length - 1 ? "border-b" : ""
            }`}
          >
            {columns.map((column) => (
              <td key={column} className="p-2 whitespace-nowrap">
                {renderCellValue(row[column], column)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};
