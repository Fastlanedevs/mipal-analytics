"use client";

import React, { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import mermaid from "mermaid";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownRendererProps {
  content: string;
}

interface CodeProps {
  node?: any;
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const MermaidDiagram: React.FC<{ content: string; diagramId: string }> = ({
  content,
  diagramId,
}) => {
  useEffect(() => {
    mermaid.render(diagramId, content).then(({ svg }) => {
      const element = document.getElementById(diagramId);
      if (element) {
        element.innerHTML = svg;
      }
    });
  }, [diagramId, content]);

  return (
    <div className="my-4 overflow-x-auto">
      <div id={diagramId} className="mermaid">
        {content}
      </div>
    </div>
  );
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
}) => {
  const mermaidRef = useRef<number>(0);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: document.documentElement.classList.contains("dark")
        ? "dark"
        : "default",
      securityLevel: "loose",
      fontFamily: "inherit",
    });
  }, []);

  const components: Components = {
    code({ node, inline, className, children, ...props }: CodeProps) {
      const match = /language-(\w+)/.exec(className || "");
      const language = match ? match[1] : "";
      const codeContent = String(children).replace(/\n$/, "");

      if (inline) {
        return (
          <code className="px-1 py-0.5 rounded bg-muted text-sm" {...props}>
            {children}
          </code>
        );
      }

      // Handle Mermaid diagrams
      if (language === "mermaid") {
        const diagramId = `mermaid-diagram-${mermaidRef.current++}`;
        return <MermaidDiagram content={codeContent} diagramId={diagramId} />;
      }

      // Regular code blocks
      return (
        <div className="my-4">
          <SyntaxHighlighter
            language={language}
            style={vscDarkPlus}
            PreTag="div"
            className="rounded-md !my-0"
            showLineNumbers
            customStyle={{
              margin: 0,
              background: "#1E1E1E",
            }}
            {...props}
          >
            {codeContent}
          </SyntaxHighlighter>
        </div>
      );
    },
    h1: ({ children }) => (
      <h1 className="mt-6 mb-4 text-2xl font-bold first:mt-0">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="mt-5 mb-3 text-xl font-bold first:mt-0">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="mt-4 mb-2 text-lg font-bold first:mt-0">{children}</h3>
    ),
    p: ({ children }) => <p className="mb-4 leading-7 last:mb-0">{children}</p>,
    ul: ({ children }) => (
      <ul className="mb-4 ml-4 space-y-2 list-disc">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="mb-4 ml-4 space-y-2 list-decimal">{children}</ol>
    ),
    li: ({ children }) => <li className="leading-7">{children}</li>,
    blockquote: ({ children }) => (
      <blockquote className="pl-4 my-4 italic border-l-2 border-muted">
        {children}
      </blockquote>
    ),
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-500 hover:underline"
      >
        {children}
      </a>
    ),
    img: ({ src, alt }) => (
      <img
        src={src}
        alt={alt}
        className="h-auto max-w-full my-4 rounded-lg"
        loading="lazy"
      />
    ),
    table: ({ children }) => (
      <div className="my-4 overflow-x-auto">
        <table className="min-w-full border-collapse border border-border">
          {children}
        </table>
      </div>
    ),
    th: ({ children }) => (
      <th className="px-4 py-2 font-medium text-left bg-muted border border-border">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-2 border border-border">{children}</td>
    ),
  };

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
};
