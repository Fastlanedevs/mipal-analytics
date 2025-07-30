import { AppDispatch } from "@/store/store";
import {
  updateMessage,
  updateMetaContent,
  updateArtifactsContent,
} from "@/store/slices/chatSlice";
import { ThinkingDescription, ThinkingStep } from "../types/chat";

export class MessageStreamHandler {
  private dispatch: AppDispatch;
  private conversationId: string;
  private messageId: string;
  private setIsInCodeBlock: (value: boolean) => void;
  private setCodeBlockLanguage: (value: string) => void;
  private currentContent: string = "";
  private isInCodeBlock: boolean = false;
  private codeBlockLanguage: string = "";
  private metaContent: ThinkingStep[] = []; // Track meta content for thinking steps
  private artifacts: any[] = []; // Track artifacts
  private suggestions: any[] = []; // Track suggestions
  private dataSummaryDelta: string = ""; // Track data summary delta content

  constructor(
    dispatch: AppDispatch,
    conversationId: string,
    messageId: string,
    setIsInCodeBlock: (value: boolean) => void,
    setCodeBlockLanguage: (value: string) => void
  ) {
    this.dispatch = dispatch;
    this.conversationId = conversationId;
    this.messageId = messageId;
    this.setIsInCodeBlock = setIsInCodeBlock;
    this.setCodeBlockLanguage = setCodeBlockLanguage;
  }

  onStreamStart?: () => void;

  processSSELine(line: string) {
    if (!line.startsWith("data: ")) return;

    const data = line.slice(6);
    if (data === "[DONE]") return;

    try {
      const event = JSON.parse(data);

      switch (event.type) {
        case "message_start":
          // Initialize message if needed
          if (this.onStreamStart) {
            this.onStreamStart();
          }
          break;

        case "content_block_start":
          // Initialize content block
          break;

        case "content_block_delta":
          this.handleContentDelta(event.delta.text);
          break;

        // case "data_summary_delta":
        //   this.handleDataSummaryDelta(event.delta);
        //   break;

        case "meta_content":
          if (event?.meta_content) {
            this.handleMetaContent(event.meta_content);
          }
          break;

        case "meta_content_block_stop":
          // Meta content block completed, update the UI with current meta content
          this.updateMetaContentInUI();
          break;

        case "artifact_block_start":
          if (event.artifact_block?.artifacts) {
            this.handleArtifacts(event.artifact_block.artifacts);
          }
          break;

        case "artifact_block_stop":
          // Artifact block completed, ensure artifacts are in UI
          this.updateArtifactsInUI();
          break;

        case "suggestion_block_start":
          if (event.suggestion_block?.suggestions) {
            this.handleSuggestions(event.suggestion_block.suggestions);
          }
          break;

        case "suggestion_block_stop":
          // Suggestions block completed, ensure suggestions are in UI
          this.updateSuggestionsInUI();
          break;

        case "content_block_stop":
          // Handle block completion
          this.dispatch(
            updateMessage({
              conversationId: this.conversationId,
              messageId: this.messageId,
              updates: {
                isStreaming: false,
                content: this.currentContent,
                isThinking: this.hasInProgressMetaContent(),
              },
            })
          );
          break;

        case "message_delta":
          if (event.delta.stop_reason) {
            this.dispatch(
              updateMessage({
                conversationId: this.conversationId,
                messageId: this.messageId,
                updates: {
                  isStreaming: false,
                  isThinking: false,
                  ...(event.delta.stop_reason && {
                    stop_reason: event.delta.stop_reason,
                  }),
                },
              })
            );
          }
          break;

        case "message_limit":
          // Handle message limit
          break;

        case "message_stop":
          this.dispatch(
            updateMessage({
              conversationId: this.conversationId,
              messageId: this.messageId,
              updates: {
                isStreaming: false,
                isThinking: false,
                metaContent: this.updateAllMetaContentStatus("completed"),
              },
            })
          );
          break;
      }
    } catch (error) {
      console.error("Error processing SSE line:", error, "Raw line:", line);
    }
  }

  private handleMetaContent(metaContent: any) {
    // Process and store meta content for thinking steps
    const { id, title, status, type = "text", description = [] } = metaContent;

    // Update previous steps to completed if a new step is "inprogress"
    if (status === "inprogress") {
      this.updatePreviousStepsStatus(id);
    }

    // Find if we already have this step by title or id
    const existingStepIndex = this.metaContent.findIndex(
      (step) => step.title === title || step.id === id
    );

    // Process descriptions recursively to handle nested descriptions and error states
    const processDescriptions = (descriptions: any[] = []): any[] => {
      return descriptions.map((desc: any) => {
        // If description has nested descriptions, process them
        if (desc.description && Array.isArray(desc.description)) {
          const nestedDesc = processDescriptions(desc.description);
          // Check if any nested description has error
          const hasNestedError = nestedDesc.some(
            (d: any) => d.status === "error"
          );
          return {
            title: desc.title || "",
            execution: desc.text || desc.execution || "",
            status: hasNestedError ? "error" : desc.status || "pending",
            type: desc.type || "text",
            description:
              typeof desc.description === "string"
                ? desc.description
                : undefined,
            nestedDescriptions: nestedDesc,
          };
        }
        return {
          title: desc.title || "",
          execution: desc.text || desc.execution || "",
          status: desc.status || "pending",
          type: desc.type || "text",
          description:
            typeof desc.description === "string" ? desc.description : undefined,
        };
      });
    };

    // Check if any description has error status recursively
    const hasErrorInDescriptions = (descriptions: any[] = []): boolean => {
      return descriptions.some((desc) => {
        // Check current description
        if (desc.status === "error") return true;

        // Check nested descriptions
        if (desc.description && Array.isArray(desc.description)) {
          return hasErrorInDescriptions(desc.description);
        }

        // Check nestedDescriptions if they exist
        if (desc.nestedDescriptions && Array.isArray(desc.nestedDescriptions)) {
          return hasErrorInDescriptions(desc.nestedDescriptions);
        }

        return false;
      });
    };

    const processedDescriptions = processDescriptions(description);
    const hasError = hasErrorInDescriptions(processedDescriptions);

    // Create the new step object with the determined status
    const newStep = {
      id,
      title,
      status: hasError ? "error" : status,
      type,
      description: processedDescriptions,
    };

    if (existingStepIndex >= 0) {
      // Replace the existing step with the new one
      this.metaContent[existingStepIndex] = newStep;
    } else {
      // Add new step
      this.metaContent.push(newStep);

      // Sort meta content by ID (assuming numeric IDs)
      this.metaContent.sort((a, b) => {
        const aId = Number(a.id);
        const bId = Number(b.id);
        return aId - bId;
      });
    }

    // Filter out any duplicate steps based on title or id
    this.metaContent = this.metaContent.reduce((acc: any[], current) => {
      const existingIndex = acc.findIndex(
        (item) => item.title === current.title || item.id === current.id
      );

      if (existingIndex === -1) {
        acc.push(current);
      } else {
        // If duplicate found, keep the one with the most recent status
        const existing = acc[existingIndex];
        if (current.status === "error" || existing.status !== "error") {
          acc[existingIndex] = current;
        }
      }
      return acc;
    }, []);

    // Update UI immediately
    this.updateMetaContentInUI();
  }

  private updatePreviousStepsStatus(currentId: string) {
    // Convert to number for proper comparison
    const currentIdNum = Number(currentId);

    // Update all previous steps (with smaller IDs) to completed if they're not already
    this.metaContent = this.metaContent.map((step) => {
      const stepIdNum = Number(step.id);
      if (stepIdNum < currentIdNum && step.status === "inprogress") {
        // Preserve error status in descriptions
        const updatedDescriptions = step.description.map(
          (desc: ThinkingDescription) => ({
            ...desc,
            status: desc.status === "error" ? "error" : ("completed" as const),
          })
        );

        // Only update to completed if there are no errors in descriptions
        const hasErrors = updatedDescriptions.some(
          (desc) => desc.status === "error"
        );

        return {
          ...step,
          status: hasErrors ? "error" : ("completed" as const),
          description: updatedDescriptions,
        } as ThinkingStep;
      }
      return step;
    });
  }

  private updateAllMetaContentStatus(
    status: "completed" | "inprogress" | "pending"
  ) {
    // Create a new array with all items updated to the specified status
    const updatedMetaContent = this.metaContent.map((step) => ({
      ...step,
      status,
    }));

    // Return the updated array (useful for final updates)
    return updatedMetaContent;
  }

  private hasInProgressMetaContent(): boolean {
    return this.metaContent.some((step) => step.status === "inprogress");
  }

  private updateMetaContentInUI() {
    // First update the meta content specifically
    this.dispatch(
      updateMetaContent({
        messageId: this.messageId,
        metaContent: this.metaContent.map((step) => ({
          ...step,
          status: step.status || "pending",
        })),
      })
    );

    // Then update the message streaming/thinking state
    this.dispatch(
      updateMessage({
        conversationId: this.conversationId,
        messageId: this.messageId,
        updates: {
          isStreaming: true,
          isThinking: this.hasInProgressMetaContent(),
        },
      })
    );
  }

  private handleArtifacts(artifacts: any[]) {
    // Store new artifacts
    this.artifacts = artifacts;
    this.updateArtifactsInUI();
  }

  private updateArtifactsInUI() {
    if (!this.artifacts || this.artifacts.length === 0) return;

    // Update artifacts content specifically
    this.dispatch(
      updateArtifactsContent({
        messageId: this.messageId,
        artifacts: this.artifacts,
      })
    );

    // Keep the existing message update
    this.dispatch(
      updateMessage({
        conversationId: this.conversationId,
        messageId: this.messageId,
        updates: {
          artifacts: this.artifacts,
          isStreaming: true,
          isThinking: this.hasInProgressMetaContent(),
          metaContent: this.metaContent,
        },
      })
    );
  }

  private handleSuggestions(suggestions: any[]) {
    // Store new suggestions
    this.suggestions = suggestions;
    this.updateSuggestionsInUI();
  }

  private updateSuggestionsInUI() {
    if (!this.suggestions || this.suggestions.length === 0) return;

    this.dispatch(
      updateMessage({
        conversationId: this.conversationId,
        messageId: this.messageId,
        updates: {
          suggestions: this.suggestions,
        },
      })
    );
  }

  private handleContentDelta(content: string) {
    this.currentContent += content;

    // Check for code block markers
    if (content.includes("```")) {
      const matches = content.match(/```(\w+)?/g);
      if (matches) {
        matches.forEach((match: string) => {
          this.isInCodeBlock = !this.isInCodeBlock;
          if (this.isInCodeBlock) {
            this.codeBlockLanguage = match.slice(3).trim();
            this.setCodeBlockLanguage(this.codeBlockLanguage);
          }
        });
      }
      this.setIsInCodeBlock(this.isInCodeBlock);
    }

    // Update message in Redux store
    this.dispatch(
      updateMessage({
        conversationId: this.conversationId,
        messageId: this.messageId,
        updates: {
          content: this.currentContent,
          isStreaming: true,
          isThinking: this.hasInProgressMetaContent(),
        },
      })
    );
  }

  /* Alert: handleDataSummaryDelta is not removed, instead commented out because to take reference of the functionality of streaming text.

  The JSON text is in the following format
  {
    "summary": "This is the summary",
    "key_points": ["Point 1", "Point 2", "Point 3"]
  }

  private handleDataSummaryDelta(delta: any) {
    // Accumulate the delta
    this.dataSummaryDelta += delta.text || delta;

    // Find or create a rich data summary artifact
    const richDataSummaryIndex = this.artifacts.findIndex(
      (a) => a.artifact_type === "rich_data_summary"
    );

    // Create a new artifact object instead of modifying the existing one
    const newArtifact = {
      artifact_type: "rich_data_summary" as const,
      content: this.dataSummaryDelta,
    };

    // Update or add the artifact with current content
    if (richDataSummaryIndex >= 0) {
      // Create a new array with the updated artifact
      this.artifacts = [
        ...this.artifacts.slice(0, richDataSummaryIndex),
        newArtifact,
        ...this.artifacts.slice(richDataSummaryIndex + 1),
      ];
    } else {
      // Add new artifact to the array
      this.artifacts = [...this.artifacts, newArtifact];
    }

    // Update the UI without trying to parse the JSON
    // Let the renderer handle the parsing and fixing
    this.updateArtifactsInUI();
  }

  */
}
