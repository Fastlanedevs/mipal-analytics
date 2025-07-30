import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { CodeContent, Artifact } from "../../../types/chat";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTranslations } from "next-intl";
import { useState } from "react";

interface AnalyticsCodeArtifactProps {
  codeArtifact?: Artifact;
  codeTypeArtifact?: Artifact;
}

export const AnalyticsCodeArtifact: React.FC<AnalyticsCodeArtifactProps> = ({
  codeArtifact,
  codeTypeArtifact,
}) => {
  const t = useTranslations("chatPage.analyticsPal.artifactTabs");
  const [copied, setCopied] = useState(false);

  if (!codeArtifact) {
    return <div>{t("noCodeAvailable")}</div>;
  }

  // Parse content if it's a string
  let codeContent: any = codeArtifact.content;
  if (typeof codeContent === "string") {
    try {
      // Check if it's a JSON string
      if (codeContent.trim().startsWith("{")) {
        codeContent = JSON.parse(codeContent);
      }
    } catch (e) {
      // If it's not valid JSON, use it as is
      console.error("Not a JSON string, using as is");
    }
  }

  // Determine code type (SQL or Python)
  const determineCodeType = (): string => {
    // First check if codeTypeArtifact explicitly specifies the type
    if (codeTypeArtifact?.content) {
      const typeContent =
        typeof codeTypeArtifact.content === "string"
          ? codeTypeArtifact.content.toLowerCase()
          : "";

      if (typeContent.includes("sql")) return "sql";
      if (typeContent.includes("python")) return "python";
    }

    // Otherwise try to infer from the code content
    const code =
      typeof codeContent === "string"
        ? codeContent
        : JSON.stringify(codeContent);

    // Common SQL patterns
    const sqlPatterns = [
      /SELECT\s+.+\s+FROM/i,
      /INSERT\s+INTO/i,
      /UPDATE\s+.+\s+SET/i,
      /DELETE\s+FROM/i,
      /CREATE\s+TABLE/i,
      /ALTER\s+TABLE/i,
      /JOIN\s+.+\s+ON/i,
      /WHERE\s+.+\s*=/i,
    ];

    // Common Python patterns
    const pythonPatterns = [
      /def\s+\w+\s*\(/i,
      /import\s+\w+/i,
      /class\s+\w+/i,
      /if\s+.+:/i,
      /for\s+.+\s+in\s+.+:/i,
      /while\s+.+:/i,
      /print\s*\(/i,
      /return\s+/i,
    ];

    // Check for SQL patterns
    for (const pattern of sqlPatterns) {
      if (pattern.test(code)) return "sql";
    }

    // Check for Python patterns
    for (const pattern of pythonPatterns) {
      if (pattern.test(code)) return "python";
    }

    // Default to Python if we can't determine
    return "python";
  };

  const codeType = determineCodeType();

  // Get explanation from code content if available
  let explanation = "";
  if (typeof codeContent === "object" && codeContent.explanation) {
    explanation = codeContent.explanation;
  }

  // Get the actual code
  const code = typeof codeContent === "object" ? codeContent.code : codeContent;

  // Helper function to extract code starting point (file path, function name, etc.)
  const getCodeStartingPoint = (codeStr: string, type: string): string => {
    if (!codeStr) return type === "sql" ? t("sqlQuery") : t("pythonScript");

    // For SQL queries with CTEs, handle specially
    if (type === "sql" && codeStr.includes("WITH") && codeStr.includes("AS")) {
      const cteMatch = codeStr.match(/--\s*(.*?)\s*\\nWITH\s+(.*?)\s+AS/);
      if (cteMatch) {
        // Return the comment part as the starting point
        return cteMatch[1].trim();
      }
    }

    const lines = codeStr.split("\n");
    if (type === "python") {
      // Python handling remains the same
      const importMatch = lines.find(
        (line: string) =>
          line.trim().startsWith("# File:") || line.trim().startsWith("# Path:")
      );
      if (importMatch) return importMatch.trim().substring(2);

      const defMatch = lines.find(
        (line) =>
          line.trim().startsWith("def ") || line.trim().startsWith("class ")
      );
      if (defMatch) return defMatch.trim();

      return t("pythonScript");
    } else {
      // For SQL, check for comments indicating the source
      const commentMatch = lines.find(
        (line) =>
          line.trim().startsWith("--") &&
          (line.includes("table") || line.includes("query"))
      );
      if (commentMatch) return commentMatch.trim().substring(2).trim();

      return t("sqlQuery");
    }
  };

  // Helper function to extract the main code content
  const getCodeContent = (codeStr: string): string => {
    if (!codeStr) return "";

    // Special handling for SQL with CTEs
    if (
      codeType === "sql" &&
      codeStr.includes("WITH") &&
      codeStr.includes("AS")
    ) {
      const parts = codeStr.split("\\n");

      // Find the index where the actual SELECT statement starts
      const selectIndex = parts.findIndex((part) =>
        part.trim().includes("SELECT")
      );

      if (selectIndex > 0) {
        // Return only the SELECT part and what follows, properly trimmed
        return parts
          .slice(selectIndex)
          .join("\n")
          .replace(/^\s*\(\\n\s*/, "") // Remove leading parenthesis and newline
          .replace(/^\s+/, "") // Remove leading whitespace
          .trim();
      }
    }

    // Check for other SQL query types
    if (codeType === "sql") {
      const sqlKeywords = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "MERGE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
      ];

      // Split by newlines and look for SQL keywords
      const lines = codeStr.split(/\\n|\n/);

      for (const keyword of sqlKeywords) {
        const keywordIndex = lines.findIndex(
          (line) =>
            line.trim().toUpperCase().startsWith(keyword) ||
            line.trim().match(new RegExp(`^\\s*\\(\\s*${keyword}`, "i"))
        );

        if (keywordIndex > 0) {
          // Found a SQL keyword after some comments or other text
          return lines
            .slice(keywordIndex)
            .join("\n")
            .replace(/^\s*\(/, "") // Remove leading parenthesis if present
            .replace(/^\s+/, "") // Remove leading whitespace
            .trim();
        }
      }
    }

    // Check for Python code patterns
    if (codeType === "python") {
      const lines = codeStr.split(/\\n|\n/);

      // Python patterns to identify code start
      const pythonPatterns = [
        /^def\s+\w+\s*\(/i, // Function definition
        /^class\s+\w+/i, // Class definition
        /^if\s+__name__\s*==\s*('|")__main__('|"):/i, // Main block
        /^import\s+\w+/i, // Import statement
        /^from\s+\w+\s+import/i, // From import statement
        /^@\w+/i, // Decorator
        /^for\s+\w+\s+in/i, // For loop
        /^while\s+/i, // While loop
        /^try:/i, // Try block
        /^with\s+/i, // With statement
      ];

      // Find the first line that matches a Python code pattern
      // but skip initial docstring or comment block
      let inDocstring = false;
      let docstringDelimiter = "";
      let codeStartIndex = -1;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Check for docstring delimiters
        if (
          !inDocstring &&
          (line.startsWith('"""') || line.startsWith("'''"))
        ) {
          inDocstring = true;
          docstringDelimiter = line.substring(0, 3);
          continue;
        }

        // Check for end of docstring
        if (inDocstring && line.endsWith(docstringDelimiter)) {
          inDocstring = false;
          continue;
        }

        // Skip if we're in a docstring
        if (inDocstring) continue;

        // Skip single-line comments
        if (line.startsWith("#")) continue;

        // Check if this line matches any Python pattern
        if (pythonPatterns.some((pattern) => pattern.test(line))) {
          codeStartIndex = i;
          break;
        }

        // If we find a non-empty, non-comment line that doesn't match patterns,
        // it's probably code too (like variable assignments)
        if (line && !line.startsWith("#")) {
          codeStartIndex = i;
          break;
        }
      }

      if (codeStartIndex > 0) {
        return lines.slice(codeStartIndex).join("\n").trim();
      }
    }

    // Default handling for other code
    const lines = codeStr.split(/\\n|\n/);
    const contentStartIndex = lines.findIndex(
      (line) =>
        !(line.trim().startsWith("# ") || line.trim().startsWith("-- ")) ||
        line.trim() === ""
    );

    return contentStartIndex > 0
      ? lines.slice(contentStartIndex).join("\n").trim()
      : codeStr.trim();
  };

  // Helper function to extract additional text/notes that should be displayed outside the code box
  const getAdditionalText = (codeStr: string): string | null => {
    if (!codeStr) return null;

    // Special handling for SQL with CTEs
    if (
      codeType === "sql" &&
      codeStr.includes("WITH") &&
      codeStr.includes("AS")
    ) {
      const cteMatch = codeStr.match(/--\s*(.*?)\s*\\nWITH\s+(.*?)\s+AS/);
      if (cteMatch) {
        return `-- ${cteMatch[1]}\\nWITH ${cteMatch[2]} AS`;
      }
    }

    // Check for other SQL query types with comments
    if (codeType === "sql") {
      const sqlKeywords = [
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "CREATE",
        "ALTER",
        "DROP",
        "MERGE",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
      ];

      // Split by newlines
      const lines = codeStr.split(/\\n|\n/);

      for (const keyword of sqlKeywords) {
        const keywordIndex = lines.findIndex(
          (line) =>
            line.trim().toUpperCase().startsWith(keyword) ||
            line.trim().match(new RegExp(`^\\s*\\(\\s*${keyword}`, "i"))
        );

        if (keywordIndex > 0) {
          // Extract all text before the SQL keyword as additional text
          return lines.slice(0, keywordIndex).join("\n").trim();
        }
      }
    }

    // Check for Python docstrings and comments
    if (codeType === "python") {
      const lines = codeStr.split(/\\n|\n/);

      // Python patterns to identify code start
      const pythonPatterns = [
        /^def\s+\w+\s*\(/i,
        /^class\s+\w+/i,
        /^if\s+__name__\s*==\s*('|")__main__('|"):/i,
        /^import\s+\w+/i,
        /^from\s+\w+\s+import/i,
        /^@\w+/i,
        /^for\s+\w+\s+in/i,
        /^while\s+/i,
        /^try:/i,
        /^with\s+/i,
      ];

      // Find docstrings and comment blocks
      let inDocstring = false;
      let docstringDelimiter = "";
      let codeStartIndex = -1;
      let docstringContent = [];
      let commentBlock = [];

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Check for docstring start
        if (
          !inDocstring &&
          (line.startsWith('"""') || line.startsWith("'''"))
        ) {
          inDocstring = true;
          docstringDelimiter = line.substring(0, 3);
          docstringContent.push(line.replace(/^['"]{'3}/, "").trim());
          continue;
        }

        // Check for docstring end
        if (inDocstring && line.endsWith(docstringDelimiter)) {
          inDocstring = false;
          docstringContent.push(line.replace(/['"]{'3}$/, "").trim());
          continue;
        }

        // Collect docstring content
        if (inDocstring) {
          docstringContent.push(line);
          continue;
        }

        // Collect comment lines
        if (line.startsWith("#")) {
          commentBlock.push(line.substring(1).trim());
          continue;
        }

        // Check if this line matches any Python pattern
        if (
          pythonPatterns.some((pattern) => pattern.test(line)) ||
          (line && !line.startsWith("#"))
        ) {
          codeStartIndex = i;
          break;
        }
      }

      if (codeStartIndex > 0) {
        // Combine docstring and comments
        const additionalContent = [];
        if (docstringContent.length > 0) {
          additionalContent.push(...docstringContent);
        }
        if (commentBlock.length > 0) {
          if (additionalContent.length > 0) additionalContent.push("");
          additionalContent.push(...commentBlock);
        }

        return additionalContent.length > 0
          ? additionalContent.join("\n").trim()
          : null;
      }
    }

    // Default handling for other notes
    const lines = codeStr.split(/\\n|\n/);
    const noteLines = [];
    let inNoteBlock = false;

    for (const line of lines) {
      if (
        line.includes("# NOTE:") ||
        line.includes("-- NOTE:") ||
        line.includes("# EXPLANATION:") ||
        line.includes("-- EXPLANATION:")
      ) {
        inNoteBlock = true;
        noteLines.push(
          line.replace(/^(#|--)\s*(NOTE:|EXPLANATION:)/i, "").trim()
        );
      } else if (
        inNoteBlock &&
        (line.trim().startsWith("# ") || line.trim().startsWith("-- "))
      ) {
        noteLines.push(line.replace(/^(#|--)\s*/i, "").trim());
      } else {
        inNoteBlock = false;
      }
    }

    return noteLines.length > 0 ? noteLines.join("\n") : null;
  };

  // Get the code starting point and content
  const codeStartingPoint = getCodeStartingPoint(code, codeType);
  const codeMainContent = getCodeContent(code);
  const additionalText = getAdditionalText(code);

  return (
    <div className="w-full">
      {explanation && <p className="text-sm mb-4">{explanation}</p>}

      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center">
          {codeType && (
            <Badge variant="outline" className="capitalize font-medium">
              {codeType}
            </Badge>
          )}
        </div>
        <div className="flex gap-2">
          <Badge
            variant="outline"
            className="capitalize font-medium"
            onMouseLeave={() => {
              setCopied(false);
            }}
          >
            {copied ? (
              <span className="text-xs text-muted-foreground cursor-default">
                {t("copied")}
              </span>
            ) : (
              <button
                className="text-xs text-muted-foreground hover:text-primary transition-colors"
                onClick={() => {
                  if (code) {
                    navigator.clipboard.writeText(code);
                    setCopied(true);
                  }
                }}
              >
                {t("copyCode")}
              </button>
            )}
          </Badge>
        </div>
      </div>

      {/* Additional text outside the code box */}
      {additionalText && (
        <div className="text-sm text-muted-foreground p-3 mb-2 bg-muted rounded-md">
          {additionalText}
        </div>
      )}

      {/* Code file path or starting point indicator */}
      <div className="text-xs text-muted-foreground px-2 py-1 bg-muted rounded-t-md border border-b-0">
        {codeStartingPoint}
      </div>

      <ScrollArea className="max-h-[300px] overflow-auto border rounded-b-lg">
        <SyntaxHighlighter
          language={codeType}
          style={vscDarkPlus}
          className="rounded-b-lg !bg-[#1E1E1E]"
          showLineNumbers
          customStyle={{
            margin: 0,
            background: "#1E1E1E",
          }}
        >
          {codeMainContent}
        </SyntaxHighlighter>
      </ScrollArea>
    </div>
  );
};
