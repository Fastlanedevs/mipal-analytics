import { ScrollArea } from "@/components/ui/scroll-area";
import { MetadataContent } from "../../../types/chat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface AnalyticsMetadataArtifactProps {
  content: MetadataContent;
}

export const AnalyticsMetadataArtifact = ({
  content,
}: AnalyticsMetadataArtifactProps) => {
  const getColumnIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "varchar":
        return "📝";
      case "text":
        return "📄";
      case "integer":
      case "int":
      case "float":
      case "decimal":
      case "numeric":
        return "🔢";
      case "date":
      case "timestamp":
        return "📅";
      case "boolean":
        return "✅";
      case "json":
      case "jsonb":
        return "{ }";
      default:
        return "📊";
    }
  };

  return (
    <ScrollArea className="max-h-[600px] overflow-auto">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold mb-4">Schema Information</h3>
        <div className="grid gap-4">
          {content.columns.map((column, index) => (
            <Card key={index} className="p-4 space-y-2">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">
                  {column.icon || getColumnIcon(column.type)}
                </span>
                <div>
                  <h4 className="font-medium">{column.display_name}</h4>
                  <code className="text-sm text-muted-foreground">
                    {column.name}
                  </code>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 mt-3">
                <div className="space-y-1">
                  <div className="flex gap-2">
                    <Badge variant="outline">{column.type}</Badge>
                    {column.sortable && (
                      <Badge variant="secondary">Sortable</Badge>
                    )}
                    {column.filterable && (
                      <Badge variant="secondary">Filterable</Badge>
                    )}
                  </div>

                  {column.format && (
                    <div className="text-sm text-muted-foreground">
                      Format: {column.format}
                    </div>
                  )}

                  {column.constraints && (
                    <div className="text-sm text-muted-foreground">
                      Range:{" "}
                      {column.constraints.min
                        ? column.constraints.min.toLocaleString()
                        : "N/A"}{" "}
                      -{" "}
                      {column.constraints.max
                        ? column.constraints.max.toLocaleString()
                        : "N/A"}
                    </div>
                  )}
                </div>
              </div>

              {column.sample_values && (
                <div>
                  <div className="text-sm font-medium mb-1">Sample Values:</div>
                  <div className="flex flex-wrap gap-1">
                    {column.sample_values.map((value, i) => (
                      <Badge key={i} variant="outline" className="text-xs">
                        {value}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </ScrollArea>
  );
};
