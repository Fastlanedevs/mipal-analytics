import React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Table, Code, ChartNoAxesColumn } from "lucide-react";
import { Artifact, MetadataContent, ColumnsContent } from "../../../types/chat";
import { AnalyticsDataArtifact } from "./AnalyticsDataArtifact";
import { AnalyticsCodeArtifact } from "./AnalyticsCodeArtifact";
import { ChartsArtifact } from "./ChartsArtifact";
import { motion } from "framer-motion";
import { RootState } from "@/store/store";
import { useSelector } from "react-redux";
import { useAppSelector } from "@/store/hooks";
import { useUser } from "@/store/hooks/useUser";
import { useTranslations } from "next-intl";

export const ArtifactTabs = () => {
  const t = useTranslations("chatPage.analyticsPal.artifactTabs");
  const artifacts = useSelector(
    (state: RootState) => state.artifacts.artifacts
  );
  const selectedArtifactMessageContent = useAppSelector(
    (state) => state.chat.selectedArtifactMessageContent
  );

  // Find explanation artifact to display above tabs
  const explanationArtifact = artifacts.find(
    (a: Artifact) => a.artifact_type === "explanation"
  );

  // Find rich data summary to display before explanation
  const richDataSummaryArtifact = artifacts.find(
    (a: Artifact) => a.artifact_type === "rich_data_summary"
  );

  // Find data summary to display after tabs
  // const dataSummaryArtifact = artifacts.find(
  //   (a: Artifact) => a.artifact_type === "data_summary"
  // );

  // Get code artifacts (both code and code_type)
  const codeArtifacts = artifacts.filter(
    (a: Artifact) =>
      a.artifact_type === "code" || a.artifact_type === "code_type"
  );

  // Get data artifact
  const dataArtifact = artifacts.find(
    (a: Artifact) => a.artifact_type === "data"
  );

  // Get columns artifact for data headers
  const columnsArtifact = artifacts.find(
    (a: Artifact) => a.artifact_type === "columns"
  );

  // Get metadata artifact
  const metadataArtifact = artifacts.find(
    (a: Artifact) => a.artifact_type === "metadata"
  );

  let metadata = null;
  if (metadataArtifact?.content) {
    metadata = JSON.parse(metadataArtifact?.content);
  }

  /* 
  ALert: Do not remove this function, instead commented out because to take reference of the functionality of streaming text. Sometimes the JSON text is not in the correct format.
  The JSON text is in the following format
  {
    "summary": "This is the summary",
    "key_points": ["Point 1", "Point 2", "Point 3"]
  }

  const renderRichDataSummary = (content: string) => {
    if (!content) return null;

    const extractStreamingText = () => {
      try {
        // First try to extract from valid JSON
        if (content.includes('"summary"')) {
          const summaryStart = content.indexOf('"summary"') + 10;
          let summaryText = "";
          let inQuotes = false;
          let i = summaryStart;

          // Skip initial whitespace and opening quote
          while (
            i < content.length &&
            [" ", "\t", "\n", '"'].includes(content[i])
          ) {
            if (content[i] === '"') inQuotes = true;
            i++;
          }

          // Collect text until the closing quote or end
          while (i < content.length) {
            if (content[i] === '"' && inQuotes) break;
            if (content[i] === "," && !inQuotes) break;
            if (content[i] === "}" && !inQuotes) break;
            summaryText += content[i];
            i++;
          }

          // Extract key points if they exist
          let keyPoints: string[] = [];
          if (content.includes('"key_points"')) {
            const keyPointsStart = content.indexOf('"key_points"') + 13;
            const arrayStart = content.indexOf("[", keyPointsStart);

            if (arrayStart !== -1) {
              let arrayContent = "";
              let inArray = true;
              let inPointQuotes = false;
              let currentPoint = "";

              // Start from after the opening bracket
              i = arrayStart + 1;

              while (i < content.length && inArray) {
                if (content[i] === '"') {
                  inPointQuotes = !inPointQuotes;
                  i++;
                  continue;
                }

                if (content[i] === "]" && !inPointQuotes) {
                  inArray = false;
                  break;
                }

                if (content[i] === "," && !inPointQuotes) {
                  if (currentPoint.trim()) {
                    keyPoints.push(currentPoint.trim());
                    currentPoint = "";
                  }
                  i++;
                  continue;
                }

                currentPoint += content[i];
                i++;
              }

              // Add the last point if exists
              if (currentPoint.trim()) {
                keyPoints.push(currentPoint.trim());
              }

              // Clean up the points
              keyPoints = keyPoints
                .map((point) => {
                  let cleaned = point.trim();
                  if (cleaned.startsWith('"')) cleaned = cleaned.substring(1);
                  if (cleaned.endsWith('"'))
                    cleaned = cleaned.substring(0, cleaned.length - 1);
                  return cleaned;
                })
                .filter((point) => point.length > 0);
            }
          }

          return {
            summary: summaryText,
            keyPoints: keyPoints,
          };
        }

        // Fallback to displaying raw text if no JSON structure is found
        return {
          summary:
            content.substring(0, 200) + (content.length > 200 ? "..." : ""),
          keyPoints: [],
        };
      } catch (e) {
        return {
          summary: "Processing data...",
          keyPoints: [],
        };
      }
    };

    try {
      // Try to parse the entire content as JSON first
      try {
        const parsedContent = JSON.parse(content);
        return (
          <div className="rich-data-summary animate-fadeIn">
            <h3 className="font-semibold mb-2">Summary</h3>
            <p className="mb-4 text-[0.95rem]">
              {parsedContent.summary || "Preparing summary..."}
            </p>
            {parsedContent.key_points &&
              parsedContent.key_points.length > 0 && (
                <>
                  <h4 className="font-semibold mb-2">Key Points</h4>
                  <ul className="list-disc pl-4 space-y-1">
                    {parsedContent.key_points.map(
                      (point: string, index: number) => (
                        <li key={index}>{point}</li>
                      )
                    )}
                  </ul>
                </>
              )}
          </div>
        );
      } catch (parseError) {
        // If full JSON parsing fails, try to extract streaming content
        const streamingContent = extractStreamingText();

        return (
          <div className="rich-data-summary">
            <h3 className="font-semibold mb-2">Summary</h3>
            <p className="mb-4 text-[0.95rem]">
              {streamingContent.summary || "Analyzing data..."}
            </p>
            {streamingContent.keyPoints &&
              streamingContent.keyPoints.length > 0 && (
                <>
                  <h4 className="font-semibold mb-2">Key Points</h4>
                  <ul className="list-disc pl-4 space-y-1">
                    {streamingContent.keyPoints.map((point, index) => (
                      <li key={index} className="streaming-item">
                        {point}
                      </li>
                    ))}
                  </ul>
                </>
              )}
          </div>
        );
      }
    } catch (error) {
      console.error("Error in renderRichDataSummary:", error);
      // Ensure we always show something, even if all parsing fails
      return (
        <div className="rich-data-summary">
          <h3 className="font-semibold mb-2">Summary</h3>
          <p className="mb-4 text-[0.95rem]">
            {content.substring(0, 200) + (content.length > 200 ? "..." : "")}
          </p>
        </div>
      );
    }
  };
  */

  const UserAvatar: React.FC = () => {
    const { user, isLoading } = useUser();

    if (isLoading || !user) {
      return null;
    }

    return (
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          {user.image_url ? (
            <img
              src={user.image_url}
              alt={user.name || "User"}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <span className="text-primary font-medium">
              {user.name?.[0]?.toUpperCase() || "U"}
            </span>
          )}
        </div>

        <span className="text-sm font-medium">{user.name || "User"}</span>
      </div>
    );
  };

  const truncateToWords = (text: string, maxWords: number): string => {
    const words = text.split(/\s+/);
    if (words.length > maxWords) {
      return words.slice(0, maxWords).join(" ") + "...";
    }
    return text;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      <div className="flex flex-col gap-2">
        <div className="p-3 bg-muted/30 rounded-xl text-[0.95rem] flex flex-col gap-1">
          <UserAvatar />
          {selectedArtifactMessageContent &&
            truncateToWords(selectedArtifactMessageContent, 100)}
        </div>
        <div className="sticky top-12 bg-background/80 dark:bg-muted/10 backdrop-blur-sm flex items-center justify-between gap-2 py-2 z-[100]">
          <h3 className="text-lg font-semibold">{t("data")}</h3>
          <div className="h-[1px] flex-1 bg-foreground/30 dark:bg-foreground/90"></div>
        </div>

        {!metadata?.is_ambiguous && (
          <Tabs defaultValue="data" className="w-full">
            <TabsList className="mb-2 w-full">
              {dataArtifact && (
                <TabsTrigger
                  value="data"
                  className="flex items-center gap-2 flex-1"
                >
                  <Table className="h-4 w-4" />
                  <span>{t("data")}</span>
                </TabsTrigger>
              )}
              {codeArtifacts.length > 0 && (
                <TabsTrigger
                  value="code"
                  className="flex items-center gap-2 flex-1"
                >
                  <Code className="h-4 w-4" />
                  <span>{t("code")}</span>
                </TabsTrigger>
              )}
              {dataArtifact && (
                <TabsTrigger
                  value="chart"
                  className="flex items-center gap-2 flex-1"
                >
                  <ChartNoAxesColumn className="h-4 w-4" />
                  <span>{t("chart")}</span>
                </TabsTrigger>
              )}
            </TabsList>

            {dataArtifact && (
              <TabsContent value="data">
                <Card className="p-4">
                  <AnalyticsDataArtifact
                    content={dataArtifact.content}
                    columnsContent={columnsArtifact?.content as ColumnsContent}
                    metadataContent={
                      metadataArtifact?.content as MetadataContent
                    }
                  />
                </Card>
              </TabsContent>
            )}

            {codeArtifacts.length > 0 && (
              <TabsContent value="code">
                <Card className="p-4">
                  <AnalyticsCodeArtifact
                    codeArtifact={artifacts.find(
                      (a: Artifact) => a.artifact_type === "code"
                    )}
                    codeTypeArtifact={artifacts.find(
                      (a: Artifact) => a.artifact_type === "code_type"
                    )}
                  />
                </Card>
              </TabsContent>
            )}

            {dataArtifact && (
              <TabsContent value="chart">
                <Card className="p-4">
                  <ChartsArtifact />
                </Card>
              </TabsContent>
            )}
          </Tabs>
        )}

        {/* Display rich data summary and explanation in a card if available */}
        {explanationArtifact && (
          <div className="mb-4 p-3 bg-muted/30 rounded-xl text-[0.95rem]">
            {explanationArtifact && (
              <div className="text-[0.95rem]">
                <h4 className="mb-1 font-semibold">{t("explanation")}</h4>
                {explanationArtifact.content as string}
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
};
