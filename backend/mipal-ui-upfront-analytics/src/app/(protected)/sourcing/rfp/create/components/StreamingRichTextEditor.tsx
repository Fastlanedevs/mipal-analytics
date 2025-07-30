import React, { useState, useEffect, useRef, useMemo } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import BulletList from "@tiptap/extension-bullet-list";
import OrderedList from "@tiptap/extension-ordered-list";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import { Loader2, FileText, Table as TableIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface StreamingRichTextEditorProps {
  content?: string;
  onChange?: (content: string) => void;
  height?: string;
  maxWords?: number;
  streaming?: boolean;
  readOnly?: boolean;
  a4View?: boolean;
  streamRef?: React.MutableRefObject<AbortController | null>;
  onAbort?: () => void;
}

const StreamingRichTextEditor: React.FC<StreamingRichTextEditorProps> = ({
  content = "",
  onChange = () => {},
  height = "100%",
  maxWords = 5000,
  streaming = false,
  readOnly = false,
  a4View = false,
  streamRef,
  onAbort,
}) => {
  const [wordCount, setWordCount] = useState(0);
  const [isA4View, setIsA4View] = useState(a4View);

  // Helper function to count words in a string
  const countWords = (text: string): number => {
    // Strip HTML tags for word counting
    const strippedText = text.replace(/<[^>]*>/g, ' ');
    return strippedText.trim().split(/\s+/).filter((word) => word.length > 0).length;
  };

  useEffect(() => {
    console.log("Current content (first 200 chars):", content?.substring(0, 200));
  }, [content]);

  useEffect(() => {
    console.log("A4 View mode:", isA4View);
  }, [isA4View]);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bulletList: false,
        orderedList: false,
      }),
      BulletList.configure({
        keepMarks: true,
        keepAttributes: true,
      }),
      OrderedList.configure({
        keepMarks: true,
        keepAttributes: true,
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content,
    editable: !readOnly && !isA4View,
    enablePasteRules: true,
    enableInputRules: true,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      const words = countWords(html);

      if (words <= maxWords || readOnly) {
        onChange(html);
        setWordCount(words);
      } else {
        setWordCount(words);
        onChange(html);
      }
    },
  });

  // Update editor's editable state when readOnly or isA4View changes
  useEffect(() => {
    if (editor) {
      editor.setEditable(!readOnly && !isA4View);
      // If no longer read-only and not in A4 view, focus the editor
      if (!readOnly && !isA4View) {
        editor.chain().focus().run();
      }
      console.log("Editor editable state updated:", !readOnly && !isA4View);
    }
  }, [readOnly, isA4View, editor]);

  // Update editor content when content changes
  useEffect(() => {
    if (editor && content !== undefined) {
      if (streaming || !editor.getText().trim()) {
        editor.commands.setContent(content);
        setWordCount(countWords(content));
      } else {
        const currentContent = editor.getHTML();
        if (currentContent !== content) {
          editor.commands.setContent(content);
          setWordCount(countWords(content));
        }
      }
    }
  }, [content, editor, streaming]);

  // Initialize word count on load
  useEffect(() => {
    if (editor) {
      const initialHtml = editor.getHTML();
      setWordCount(countWords(initialHtml));
    }
  }, [editor]);

  const handleCancelStreaming = () => {
    if (streamRef?.current) {
      streamRef.current.abort();
      if (onAbort) onAbort();
    }
  };

  // Toggle A4 view
  const toggleA4View = () => {
    console.log("Toggling A4 view from", isA4View, "to", !isA4View);
    setIsA4View(!isA4View);
    
    // When entering normal edit mode, focus the main editor
    if (isA4View && editor) {
      console.log("Returning to edit mode, updating editor...");
      setTimeout(() => {
        if (editor) {
          editor.commands.focus();
        }
      }, 100);
    }
  };

  return (
    <div className="relative border rounded-md">
      {/* Global styles for all editor components */}
      <style jsx global>{`
        /* Regular ProseMirror editor styling */
        .ProseMirror {
          outline: none;
          min-height: 100%;
        }
        .ProseMirror table {
          border-collapse: collapse;
          table-layout: fixed;
          width: 100%;
          margin: 0;
          overflow: hidden;
        }
        .ProseMirror td,
        .ProseMirror th {
          min-width: 1em;
          border: 1px solid #ced4da;
          padding: 3px 5px;
          vertical-align: top;
          box-sizing: border-box;
          position: relative;
        }
        .ProseMirror th {
          font-weight: bold;
          background-color: #f8f9fa;
          text-align: left;
        }
        .ProseMirror .selectedCell:after {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          top: 0;
          bottom: 0;
          background: rgba(200, 200, 255, 0.4);
          pointer-events: none;
        }
        .ProseMirror table p {
          margin: 0;
        }
        
        /* A4 content styling */
        .a4-content {
          font-family: inherit;
          line-height: 1.5;
        }
        .a4-content * {
          max-width: 100%;
        }
        .a4-content div[style] {
          display: block !important;
        }
      `}</style>

      <div className="border-b bg-muted/30 p-2 flex flex-wrap gap-2">
        {!readOnly && !isA4View && (
          <>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleBold().run()}
              className={editor?.isActive("bold") ? "bg-muted" : ""}
              disabled={readOnly}
            >
              <strong>B</strong>
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              className={editor?.isActive("italic") ? "bg-muted" : ""}
              disabled={readOnly}
            >
              <em>I</em>
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
              className={editor?.isActive("heading", { level: 1 }) ? "bg-muted" : ""}
              disabled={readOnly}
            >
              H1
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
              className={editor?.isActive("heading", { level: 2 }) ? "bg-muted" : ""}
              disabled={readOnly}
            >
              H2
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
              className={editor?.isActive("heading", { level: 3 }) ? "bg-muted" : ""}
              disabled={readOnly}
            >
              H3
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              className={editor?.isActive("bulletList") ? "bg-muted" : ""}
              disabled={readOnly}
            >
              • Bullet List
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              className={editor?.isActive("orderedList") ? "bg-muted" : ""}
              disabled={readOnly}
            >
              1. Ordered List
            </Button>
            <div className="flex items-center gap-1 border-l pl-1 ml-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  editor
                    ?.chain()
                    .focus()
                    .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                    .run()
                }
                className={editor?.isActive("table") ? "bg-muted" : ""}
                disabled={readOnly || editor?.isActive("table")}
                title="Insert table"
              >
                <TableIcon className="h-4 w-4" />
              </Button>
              {editor?.isActive("table") && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => editor?.chain().focus().addColumnBefore().run()}
                    disabled={readOnly}
                    title="Add column before"
                  >
                    +◀
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => editor?.chain().focus().addColumnAfter().run()}
                    disabled={readOnly}
                    title="Add column after"
                  >
                    ▶+
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => editor?.chain().focus().addRowBefore().run()}
                    disabled={readOnly}
                    title="Add row before"
                  >
                    +▲
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => editor?.chain().focus().addRowAfter().run()}
                    disabled={readOnly}
                    title="Add row after"
                  >
                    ▼+
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => editor?.chain().focus().deleteTable().run()}
                    disabled={readOnly}
                    title="Delete table"
                  >
                    ❌
                  </Button>
                </>
              )}
            </div>
          </>
        )}
        <div className={cn("ml-auto flex items-center gap-2")}>
          <Button
            size="sm"
            variant="outline"
            onClick={toggleA4View}
            className="gap-1"
          >
            <FileText className="h-4 w-4" />
            {isA4View ? "Normal View" : "Preview"}
          </Button>
        </div>
      </div>

      <div
        className={cn(
          "overflow-auto",
          isA4View ? "p-8 bg-gray-200 dark:bg-gray-900" : ""
        )}
        style={{ height: isA4View ? "auto" : height }}
      >
        {isA4View ? (
          // A4 Preview mode - ALWAYS use the raw HTML content directly
          <div 
            className="shadow-2xl bg-white dark:bg-gray-800 mx-auto relative prose prose-sm dark:prose-invert max-w-none"
            style={{
              width: "210mm",
              minHeight: "297mm",
              padding: "2.5cm 2cm",
              marginBottom: "2rem",
              boxShadow: "0 0 20px rgba(0,0,0,0.15)",
              position: "relative",
              backgroundImage:
                "linear-gradient(to right, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0) 10%, rgba(0,0,0,0) 90%, rgba(0,0,0,0.02) 100%)",
            }}
          >
            {/* PDF content - view-only */}
            <div 
              dangerouslySetInnerHTML={{ __html: content }} 
              className="a4-content"
            />
            
            {/* A4 decorative elements */}
          
            
           
          </div>
        ) : (
          // Edit mode or streaming mode
          <div className="prose prose-sm dark:prose-invert max-w-none h-full">
            {streaming ? (
              // During streaming, show raw HTML
              <div dangerouslySetInnerHTML={{ __html: content }} />
            ) : (
              // Normal edit mode with editor
              <EditorContent editor={editor} className="h-full" />
            )}
          </div>
        )}
        
        {streaming && (
          <div className="absolute top-2 right-2 flex items-center gap-2 text-sm bg-background px-2 py-1 rounded shadow z-10">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Generating...</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 ml-2 text-xs"
              onClick={handleCancelStreaming}
            >
              Cancel
            </Button>
          </div>
        )}
      </div>

      {!readOnly && !isA4View && (
        <div className="px-3 py-2 border-t bg-muted/10 flex justify-end">
          <span
            className={cn(
              "text-xs",
              wordCount > maxWords ? "text-destructive" : "text-muted-foreground"
            )}
          >
            {wordCount}/{maxWords} words
          </span>
        </div>
      )}
    </div>
  );
};

export default StreamingRichTextEditor; 