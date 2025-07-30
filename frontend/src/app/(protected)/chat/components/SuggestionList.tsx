import React, { useEffect } from "react";
import {
  Suggestion,
  DocumentContent,
  PersonContent,
  PALContent,
  TextContent,
  IntentContent,
} from "../types/chat";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useTranslations } from "next-intl";
interface SuggestionListProps {
  suggestions: Suggestion[];
  selectedSuggestions: Suggestion[];
  onSuggestionSelect: (suggestion: Suggestion) => void;
  isUserMessage?: boolean;
  isCurrentLeafMessage?: boolean;
  isLastMessage?: boolean;
}

export const SuggestionList: React.FC<SuggestionListProps> = ({
  suggestions,
  selectedSuggestions,
  onSuggestionSelect,
  isUserMessage = false,
  isCurrentLeafMessage = false,
  isLastMessage = false,
}) => {
  const t = useTranslations("chatPage.suggestionList");

  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  const isSuggestionSelected = (suggestion: Suggestion) => {
    return selectedSuggestions.some(
      (selected) =>
        JSON.stringify(selected.suggestion_content) ===
        JSON.stringify(suggestion.suggestion_content)
    );
  };

  const renderSuggestionContent = (suggestion: Suggestion) => {
    const isDocumentContent = (content: any): content is DocumentContent => {
      return content && "title" in content && "type" in content;
    };

    const isPersonContent = (content: any): content is PersonContent => {
      return content && "Name" in content;
    };

    const isPALContent = (content: any): content is PALContent => {
      return (
        content &&
        "title" in content &&
        ("model" in content || "type" in content || "description" in content)
      );
    };

    const isTextContent = (content: any): content is TextContent => {
      return content && "text" in content;
    };

    const isQueryContent = (content: any): content is IntentContent => {
      return (
        content &&
        "title" in content &&
        "type" in content &&
        "source_url" in content
      );
    };

    if (
      suggestion.type === "Document" &&
      isDocumentContent(suggestion.suggestion_content)
    ) {
      const doc = suggestion.suggestion_content;
      return (
        <div className="flex flex-col text-left">
          <span className="font-medium">{doc.title}</span>
          <span className="text-sm text-gray-500">{doc.description}</span>
          <span className="text-xs text-gray-400">
            {doc.type} • {doc.uploaded_by}
          </span>
        </div>
      );
    }

    if (
      suggestion.type === "Person" &&
      isPersonContent(suggestion.suggestion_content)
    ) {
      const person = suggestion.suggestion_content;
      return (
        <div className="flex items-center space-x-3">
          {person.image && (
            <img
              src={person.image}
              alt={person.Name}
              className="w-8 h-8 rounded-full"
            />
          )}
          <div>
            <span className="font-medium">{person.Name}</span>
            <span className="block text-sm text-gray-500">
              {person.Position}
            </span>
          </div>
        </div>
      );
    }

    if (
      suggestion.type === "PAL" &&
      isPALContent(suggestion.suggestion_content)
    ) {
      const pal = suggestion.suggestion_content;
      return (
        <div className="flex flex-col">
          <span className="font-medium">{pal.title}</span>
          {pal.description && (
            <span className="text-sm text-gray-500">{pal.description}</span>
          )}
          {pal.type && (
            <span className="text-xs text-gray-400">{pal.type}</span>
          )}
        </div>
      );
    }

    if (
      suggestion.type === "Text" &&
      isTextContent(suggestion.suggestion_content)
    ) {
      const text = suggestion.suggestion_content;
      return (
        <div className="flex flex-col">
          <span className="text-sm text-left">{text.text}</span>
        </div>
      );
    }

    if (
      suggestion.type === "QUERY" &&
      isQueryContent(suggestion.suggestion_content)
    ) {
      const query = suggestion.suggestion_content;
      return (
        <div className="flex flex-col">
          <span className="text-sm text-gray-500">{query.text}</span>
        </div>
      );
    }

    if (!suggestion.suggestion_content) {
      return (
        <div className="flex flex-col">
          <span className="text-sm text-left">{t("unknownContent")}</span>
        </div>
      );
    }

    console.warn("Unsupported suggestion type or content:", suggestion);
    return null;
  };

  // Get the suggestion types for dynamic labeling
  const getSuggestionTypeLabel = (
    suggestions: Suggestion[],
    isUserMessage: boolean
  ) => {
    // Ensure suggestions is an array and has items
    if (!Array.isArray(suggestions) || suggestions.length === 0) {
      return isUserMessage ? "Selected References" : "Suggested References";
    }

    // Filter out suggestions without valid types
    const validSuggestions = suggestions.filter((s) => s && s.type);
    if (validSuggestions.length === 0) {
      return isUserMessage ? "Selected References" : "Suggested References";
    }

    const types = new Set(validSuggestions.map((s) => s.type));
    const prefix = isUserMessage ? "Selected" : "Suggested";

    if (types.size === 1) {
      const type = types.values().next().value;
      switch (type) {
        case "PAL":
          return `${prefix} ${t("PAL")}`;
        case "Document":
          return `${prefix} ${t("Document")}`;
        case "Person":
          return `${prefix} ${t("Person")}`;
        case "Text":
          return `${prefix} ${t("Text")}`;
        case "QUERY":
          return `${prefix} ${t("Query")}`;
        default:
          return `${prefix} ${t("References")}`;
      }
    }

    // Handle multiple types
    if (types.size > 1) {
      const typeLabels = Array.from(types).map((type) => {
        switch (type) {
          case "PAL":
            return t("PAL");
          case "Document":
            return t("Document");
          case "Person":
            return t("Person");
          case "Text":
            return t("Text");
          case "QUERY":
            return t("Query");
          default:
            return t("References");
        }
      });
      return `${prefix} ${typeLabels.join(" & ")}`;
    }

    return isUserMessage ? t("selectedReferences") : t("suggestedReferences");
  };

  // if QUERY suggestions, return null
  if (isUserMessage && suggestions.some((s) => s.type === "QUERY")) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {getSuggestionTypeLabel(suggestions, isUserMessage)}
      </h3>
      <div className="space-y-2">
        {suggestions.map((suggestion, index) => {
          const content = renderSuggestionContent(suggestion);
          if (!content) return null;

          // Show checkbox for non-PAL suggestions when it's the current leaf message
          const showCheckbox =
            !isUserMessage &&
            isCurrentLeafMessage &&
            suggestion.type !== "PAL" &&
            suggestion.type !== "QUERY";

          if (suggestion.type === "PAL") {
            return (
              <div
                key={index}
                onClick={() => {
                  if (isLastMessage) {
                    onSuggestionSelect(suggestion);
                  }
                }}
                className="flex items-start gap-2 p-3 border rounded-xl cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 bg-background"
              >
                <Badge variant="secondary" className="mt-1">
                  {t("usePAL")}
                </Badge>
                {content}
              </div>
            );
          }

          return (
            <div
              key={index}
              className={`flex items-start gap-2 p-3 border rounded-xl bg-background ${
                isLastMessage &&
                (suggestion.type === "Text" || suggestion.type === "QUERY")
                  ? "cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-800"
                  : ""
              } ${
                isSuggestionSelected(suggestion)
                  ? "bg-gray-200 dark:bg-gray-900"
                  : ""
              } active:bg-gray-300 dark:active:bg-gray-900
              md:flex-row flex-col
              `}
              onClick={() => {
                if (isLastMessage) {
                  onSuggestionSelect(suggestion);
                }
              }}
            >
              {showCheckbox ? (
                <Checkbox
                  checked={isSuggestionSelected(suggestion)}
                  onCheckedChange={() => {
                    if (isLastMessage) {
                      onSuggestionSelect(suggestion);
                    }
                  }}
                  className="mt-1"
                />
              ) : (
                <Badge
                  variant={isUserMessage ? "default" : "secondary"}
                  className="mt-1"
                >
                  {suggestion.type === "QUERY"
                    ? t("Query")
                    : isUserMessage
                      ? t("Selected")
                      : t("Suggested")}
                </Badge>
              )}
              <div className="pt-1">{content}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
