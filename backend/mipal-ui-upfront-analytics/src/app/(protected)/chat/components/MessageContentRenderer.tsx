import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import { Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

// Create a custom theme based on vscDarkPlus with transparent background
const transparentTheme = {
  ...vscDarkPlus,
  'code[class*="language-"]': {
    ...vscDarkPlus['code[class*="language-"]'],
    background: "transparent",
  },
  'pre[class*="language-"]': {
    ...vscDarkPlus['pre[class*="language-"]'],
    background: "transparent",
  },
};

// Define the CodeProps interface
interface CodeProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

interface ContentBlock {
  type: string;
  text?: string;
}

// CopyButton component to handle code copying
const CopyButton = ({ content }: { content: string }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  };

  return (
    <button
      onClick={copyToClipboard}
      className="absolute right-2 top-1 p-1.5 rounded-md bg-background/80 hover:bg-background/90 transition-colors opacity-0 group-hover:opacity-100 mr-2"
      aria-label="Copy code"
    >
      {copied ? (
        <Check className="w-4 h-4 text-green-500" />
      ) : (
        <Copy className="w-4 h-4 text-muted-foreground" />
      )}
    </button>
  );
};

interface MessageContentRendererProps {
  content: string | ContentBlock[];
}

const MessageContentRenderer: React.FC<MessageContentRendererProps> = ({
  content,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [collapsedLists, setCollapsedLists] = useState<{
    [key: string]: boolean;
  }>({});

  // Add useEffect to make pre tags transparent via direct DOM manipulation
  //   useEffect(() => {
  //     // Create a style element
  //     const styleEl = document.createElement("style");
  //     styleEl.innerHTML = `
  //       /* Target the parent pre tags */
  //       pre,
  //       pre[class*="language-"],

  //       /* Target any pre within the syntax highlighter */
  //       .prism-code pre,
  //       div.prism-code,

  //       /* Target actual code elements */
  //       code[class*="language-"],

  //       /* Target any element with a background that might be in the way */
  //       .markdown-content [style*="background"] {
  //         background: transparent !important;
  //       }
  //     `;
  //     document.head.appendChild(styleEl);

  //     // Cleanup on unmount
  //     return () => {
  //       document.head.removeChild(styleEl);
  //     };
  //   }, []);

  // Format the content with markdown
  const processContent = (content: string | ContentBlock[]) => {
    // If content is an array of blocks, join the text blocks
    if (Array.isArray(content)) {
      return content
        .filter((block) => block.type === "text" && block.text)
        .map((block) => block.text)
        .join("\n");
    }

    // Pre-process the content to ensure code blocks are properly terminated
    // and handle newlines correctly
    const processedContent = content
      .replace(/\\n/g, "\n") // Replace literal "\n" with actual newlines
      .replace(/\r\n/g, "\n") // Normalize line endings
      .replace(/\n{3,}/g, "\n\n") // Replace multiple newlines with double newlines
      .split("\n")
      .map((line) => {
        if (line.includes("```") && line.trim().length > 3) {
          const parts = line.split("```");

          if (parts[0].trim()) {
            return parts[0].trim() + "\n```" + (parts[1] || "");
          }

          // If there's text after the code block
          if (parts[parts.length - 1].trim() && parts.length > 2) {
            return "```" + parts[1] + "```\n" + parts[parts.length - 1].trim();
          }
        }
        return line;
      })
      .join("\n");

    return processedContent;
  };

  const processedContent = processContent(content);

  // Special handling for source lists - check if content starts with "Sources" or "References"
  const isSourceList =
    typeof processedContent === "string" &&
    (processedContent.includes("Sources\\n-") ||
      processedContent.includes("References\\n-") ||
      processedContent.includes("## Cited Sources"));

  const sourceRegex = /\[Source:\s*([^\]]+?)\]/g; // Non-greedy match for content within [Source: ...]

  const processTextForSources = (text: string): React.ReactNode[] => {
    const elements: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = sourceRegex.exec(text)) !== null) {
      // Text before the source
      if (match.index > lastIndex) {
        elements.push(text.substring(lastIndex, match.index));
      }

      const sourceContent = match[1]; // e.g., "mipal.ai, medium.com" or "medium.com"
      const domains = sourceContent
        .split(",")
        .map((d) => d.trim().toLowerCase())
        .filter(
          (d) => d && !d.startsWith("http://") && !d.startsWith("https://")
        );

      const sourceKey = `source-${match.index}`;

      if (domains.length > 0) {
        elements.push(
          <span key={sourceKey} className="inline-source">
            {" ("}
            {domains.map((domain, i) => {
              if (!/^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$/.test(domain)) {
                // If not a valid-looking domain, render as plain text
                return (
                  <React.Fragment key={`${sourceKey}-domain-${i}-text`}>
                    {i > 0 && (
                      <span className="mx-1 text-foreground/70">,</span>
                    )}
                    <span className="text-xs text-foreground/70">{domain}</span>
                  </React.Fragment>
                );
              }
              return (
                <React.Fragment key={`${sourceKey}-domain-${i}`}>
                  {i > 0 && <span className="mx-1 text-foreground/70">,</span>}
                  <span className="bg-muted-foreground/20 rounded-full px-2 py-0.5 group inline-flex items-center align-middle text-xs">
                    <a
                      href={`https://${domain}`} // Use https for the link
                      target="_blank"
                      rel="noopener noreferrer"
                      className={cn(
                        "hover:underline text-foreground/70 group-hover:text-foreground inline-flex items-center align-middle"
                      )}
                    >
                      <img
                        src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
                        alt={`${domain} favicon`}
                        className="w-3 h-3 object-contain mr-1 !my-0"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = "none";
                        }}
                      />
                      {domain}
                    </a>
                  </span>
                </React.Fragment>
              );
            })}
            {")"}
          </span>
        );
      }
      lastIndex = sourceRegex.lastIndex;
    }

    // Remaining text after the last source
    if (lastIndex < text.length) {
      elements.push(text.substring(lastIndex));
    }

    return elements.length > 0 ? elements : [text]; // If no sources, return original text node
  };

  const components: Components = {
    code: ({ node, inline, className, children, ...props }: CodeProps) => {
      const match = /language-(\w+)/.exec(className || "");
      const language = match ? match[1] : "";

      // Check if the code content is a single line
      const codeContent = String(children).replace(/\n$/, "");
      const isSingleLine = !codeContent.includes("\n");

      // If it's inline or a single line, render as inline code
      if (inline || isSingleLine) {
        return (
          <code
            className="px-1.5 py-0.5 bg-[hsl(var(--subtle-bg))] dark:bg-[hsl(var(--subtle-bg))] border border-muted-foreground/10 rounded text-sm"
            {...props}
          >
            {codeContent}
          </code>
        );
      }

      // For multi-line code blocks, render as a block
      return (
        <div className="my-2 relative group bg-subtle-bg">
          <CopyButton content={codeContent} />
          <SyntaxHighlighter
            language={language}
            style={transparentTheme}
            PreTag="pre"
            className="rounded-lg !my-0 max-h-[400px] overflow-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar]:h-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/60 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-corner]:bg-transparent"
            customStyle={{
              margin: 0,
              background: "hsl(var(--subtle-bg))",
              border: "1px solid hsl(var(--subtle-border))",
            }}
            {...props}
          >
            {codeContent}
          </SyntaxHighlighter>
        </div>
      );
    },
    // Improve other component styles
    p: ({ node, children: pChildren, ...props }) => {
      const processedChildren = React.Children.toArray(pChildren).flatMap(
        (child) => {
          if (typeof child === "string") {
            return processTextForSources(child);
          }
          // Return non-string children (e.g., <em>, <code>) as is
          return child;
        }
      );

      return (
        <p className="mb-2 whitespace-pre-wrap last:mb-0 first:mt-0" {...props}>
          {processedChildren}
        </p>
      );
    },
    ul: ({ children, className, ...props }) => {
      // Count the number of list items
      const childrenArray = React.Children.toArray(children);
      const sourceCount = childrenArray.length;

      // Generate a unique ID for this list (based on position or content hash)
      const listId = `list-${
        props.node?.position?.start?.line ||
        Math.random().toString(36).substring(2, 9)
      }`;

      // Check if this list is part of a sources section and contains URLs
      const isSourcesListWithUrls =
        isSourceList &&
        childrenArray.every((child) => {
          if (typeof child === "string") {
            return child.startsWith("http");
          } else if (React.isValidElement(child)) {
            const childText = child.props.children;
            return (
              typeof childText === "string" && childText.startsWith("http")
            );
          }
          return false;
        });

      // Check if this is a source list with more than 5 items
      if (isSourcesListWithUrls && sourceCount > 5) {
        // Check if this list is collapsed (default to true)
        const isListCollapsed = collapsedLists[listId] !== false;

        // Show only first 5 items when collapsed
        const visibleItems = childrenArray.slice(0, 5);
        const hiddenItems = childrenArray.slice(5);

        return (
          <div className="mt-2 mb-4">
            <ul className="list-disc [&>li]:my-0 [&>li]:py-0 space-y-0.5">
              {visibleItems}
              {hiddenItems && (
                <Collapsible open={!isListCollapsed}>
                  <CollapsibleContent>{hiddenItems}</CollapsibleContent>
                  <CollapsibleTrigger
                    className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mt-2"
                    onClick={() =>
                      setCollapsedLists((prev) => ({
                        ...prev,
                        [listId]: !isListCollapsed,
                      }))
                    }
                  >
                    {isListCollapsed ? (
                      <>
                        <ChevronDown className="h-4 w-4" />
                        <span>Show more sources</span>
                      </>
                    ) : (
                      <>
                        <ChevronUp className="h-4 w-4" />
                        <span>Show less</span>
                      </>
                    )}
                  </CollapsibleTrigger>
                </Collapsible>
              )}
            </ul>
          </div>
        );
      }

      return (
        <ul
          className={`mb-2 list-disc ${
            isSourceList
              ? "[&>li]:my-0 [&>li]:py-0 space-y-0.5"
              : "[&>li]:mb-0.5"
          }`}
          {...props}
        >
          {children}
        </ul>
      );
    },
    ol: ({ children }) => (
      <ol className="mb-2 list-decimal [&>li]:mb-1">{children}</ol>
    ),
    li: ({ children, node: liNode, ...props }) => {
      // Added node as liNode for clarity
      // Check if the original children consist of a single string that is a URL
      const originalChildrenArray = React.Children.toArray(children);
      let isSimpleUrlItem = false;
      let simpleUrlText = "";

      if (
        originalChildrenArray.length === 1 &&
        typeof originalChildrenArray[0] === "string"
      ) {
        simpleUrlText = (originalChildrenArray[0] as string).trim();
        if (
          simpleUrlText.startsWith("http://") ||
          simpleUrlText.startsWith("https://")
        ) {
          isSimpleUrlItem = true;
        }
      }

      if (isSimpleUrlItem) {
        try {
          const url = new URL(simpleUrlText);
          const domain = url.hostname;
          const displayDomain = domain.startsWith("www.")
            ? domain
            : `www.${domain}`;
          return (
            <li className="pl-1 mb-1" {...props}>
              {" "}
              {/* Original styling for http links in lists */}
              <a
                href={simpleUrlText}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline text-blue-500 inline-flex items-center gap-1.5 py-0.5"
              >
                <img
                  src={`https://www.google.com/s2/favicons?domain=${domain}&sz=32`}
                  alt={domain}
                  className="w-3.5 h-3.5 object-contain flex-shrink-0"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
                <span className="overflow-hidden text-ellipsis">
                  {displayDomain}
                </span>
              </a>
            </li>
          );
        } catch (e) {
          // Fallback to generic processing if URL parsing fails
        }
      }

      // If not a simple URL item, or if URL parsing failed, process children for sources
      const processedLiChildren = React.Children.toArray(children).flatMap(
        (childNode) => {
          if (typeof childNode === "string") {
            return processTextForSources(childNode);
          }
          return childNode;
        }
      );

      return (
        <li
          className={cn(
            "pl-1",
            "mb-1",
            isSourceList ? "py-0 leading-none" : "leading-tight"
          )}
          {...props}
        >
          {processedLiChildren}
        </li>
      );
    },
    a: ({ node, href, children, ...props }) => {
      if (href?.startsWith("http") || href?.startsWith("www.")) {
        try {
          const url = new URL(href);
          const domain = url.hostname;
          // Format domain with www. if not present
          const displayDomain = domain.startsWith("www.")
            ? domain
            : `www.${domain}`;
          return (
            <span className="bg-muted-foreground/20 rounded-full px-2 py-0.5 group inline-flex items-center align-middle">
              {/* Space before first domain or comma before subsequent */}
              <a
                href={`https://${domain}`} // Use https for the link
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline text-xs text-foreground/70 group-hover:text-foreground inline-flex items-center align-middle"
              >
                <img
                  src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
                  alt={`${domain} favicon`}
                  className="w-3 h-3 object-contain mr-1 !my-0"
                  // style={{ verticalAlign: "-2px" }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
                {domain}
              </a>
            </span>
          );
        } catch (e) {
          // If URL parsing fails, render normally
        }
      }
      return (
        <a href={href} {...props} className="text-blue-500 hover:underline">
          {children}
        </a>
      );
    },
    h1: ({ children }) => (
      <h1 className="!mt-4 !mb-2 text-2xl font-bold first:mt-0">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="!mt-0 !mb-2 text-xl font-bold first:mt-0">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="!mt-0 !mb-2 text-lg font-bold first:mt-0">{children}</h3>
    ),
    blockquote: ({ children }) => (
      <blockquote className="pl-4 my-2 italic border-l-4 border-gray-200">
        {children}
      </blockquote>
    ),
    br: () => <br className="mb-2" />,
    // Add custom table components for overflow handling
    table: ({ children }) => (
      <div className="mt-2 mb-4 overflow-auto max-h-[400px] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar]:h-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/60 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-corner]:bg-transparent">
        <table className="min-w-full border-collapse my-0">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-subtle-bg sticky top-0 z-10 bg-background dark:bg-zinc-900">
        {children}
      </thead>
    ),
    tbody: ({ children }) => <tbody>{children}</tbody>,
    tr: ({ children }) => (
      <tr className="border-b border-subtle-border">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-4 py-2 text-left text-sm font-medium border-r last:border-r-0 border-subtle-border">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-2 text-sm border-r last:border-r-0 border-subtle-border">
        {children}
      </td>
    ),
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={components}
      className={cn(`markdown-content`, isSourceList && "sources-list")}
    >
      {processedContent}
    </ReactMarkdown>
  );
};

export default MessageContentRenderer;
