import React, { useState, useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Markdown } from "tiptap-markdown";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import BulletList from "@tiptap/extension-bullet-list";
import OrderedList from "@tiptap/extension-ordered-list";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import {
  Table as TableIcon,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Bold,
  Italic,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  FileText,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface MarkdownEditorProps {
  content: string;
  onChange: (markdown: string) => void;
  height?: string; // Optional prop to control editor height
  maxWords?: number; // Optional max word limit
}

const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  content,
  onChange,
  height = "300px", // Default height if not specified
  maxWords = 500, // Default word limit
}) => {
  const [wordCount, setWordCount] = useState(0);

  // Helper function to count words in a string
  const countWords = (text: string): number => {
    return text
      .trim()
      .split(/\s+/)
      .filter((word) => word.length > 0).length;
  };

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
      Markdown.configure({
        html: false,
        tightLists: true,
        tightListClass: "tight",
        bulletListMarker: "-",
        linkify: true,
        breaks: true,
        transformPastedText: true,
      }),
    ],
    content,
    onUpdate: ({ editor }) => {
      const markdown = editor.storage.markdown.getMarkdown();
      const words = countWords(markdown);

      if (words <= maxWords) {
        // Within limit, update as normal
        onChange(markdown);
        setWordCount(words);
      } else {
        // Over word limit
        // This is more complex than character limiting, so we'll just update the count
        // and rely on visual feedback to guide the user
        setWordCount(words);
        onChange(markdown);
      }
    },
  });

  // Initialize word count on load
  useEffect(() => {
    if (editor) {
      const initialMarkdown = editor.storage.markdown.getMarkdown();
      setWordCount(countWords(initialMarkdown));
    }
  }, [editor]);

  // Function to insert a table
  const insertTable = (rows: number, cols: number) => {
    editor
      ?.chain()
      .focus()
      .insertTable({ rows, cols, withHeaderRow: true })
      .run();
  };

  // Function to convert selected text to table
  const convertTextToTable = () => {
    if (!editor) return;

    // Get selected text
    const { from, to } = editor.state.selection;
    const text = editor.state.doc.textBetween(from, to, " ");

    if (!text || text.trim() === "") {
      return; // No selection
    }

    // Split into rows
    const rows = text.split("\n").filter((row) => row.trim() !== "");
    if (rows.length === 0) return;

    // Detect delimiter (tab, comma, or space)
    let delimiter = "\t"; // Default to tab
    if (!text.includes("\t") && text.includes(",")) {
      delimiter = ",";
    } else if (!text.includes("\t") && !text.includes(",")) {
      delimiter = " ";
    }

    // Split rows into cells
    const cells = rows.map((row) => row.split(delimiter));
    const columnCount = Math.max(...cells.map((row) => row.length));

    // Delete the selected text first
    editor.chain().focus().deleteSelection().run();

    // Create a table with the content
    const tableHTML = `<table><tbody>${rows
      .map((row, rowIndex) => {
        const rowCells = cells[rowIndex];
        return `<tr>${[...Array(columnCount)]
          .map((_, colIndex) => {
            const cellContent = rowCells[colIndex] || "";
            return rowIndex === 0
              ? `<th>${cellContent.trim()}</th>`
              : `<td>${cellContent.trim()}</td>`;
          })
          .join("")}</tr>`;
      })
      .join("")}</tbody></table>`;

    // Insert the HTML table
    editor.chain().focus().insertContent(tableHTML).run();
  };

  return (
    <div className="border rounded-md">
      <div className="border-b bg-muted/30 p-2 flex flex-wrap gap-2 items-center">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => editor?.chain().focus().toggleBold().run()}
          className={editor?.isActive("bold") ? "bg-muted" : ""}
        >
          <Bold className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => editor?.chain().focus().toggleItalic().run()}
          className={editor?.isActive("italic") ? "bg-muted" : ""}
        >
          <Italic className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            editor?.chain().focus().toggleHeading({ level: 1 }).run()
          }
          className={
            editor?.isActive("heading", { level: 1 }) ? "bg-muted" : ""
          }
        >
          <Heading1 className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            editor?.chain().focus().toggleHeading({ level: 2 }).run()
          }
          className={
            editor?.isActive("heading", { level: 2 }) ? "bg-muted" : ""
          }
        >
          <Heading2 className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            editor?.chain().focus().toggleHeading({ level: 3 }).run()
          }
          className={
            editor?.isActive("heading", { level: 3 }) ? "bg-muted" : ""
          }
        >
          <Heading3 className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => editor?.chain().focus().toggleBulletList().run()}
          className={editor?.isActive("bulletList") ? "bg-muted" : ""}
        >
          <List className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => editor?.chain().focus().toggleOrderedList().run()}
          className={editor?.isActive("orderedList") ? "bg-muted" : ""}
        >
          <ListOrdered className="h-4 w-4" />
        </Button>

        {/* Table Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              variant="ghost"
              className={editor?.isActive("table") ? "bg-muted" : ""}
            >
              <TableIcon className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => insertTable(3, 3)}>
              3×3 Table
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => insertTable(5, 2)}>
              5×2 Table
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => insertTable(3, 5)}>
              3×5 Table
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={convertTextToTable}
              className="border-t mt-1 pt-1"
            >
              <FileText className="h-4 w-4 mr-2" />
              Convert Selected Text to Table
            </DropdownMenuItem>
            {editor?.isActive("table") && (
              <>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().addColumnBefore().run()}
                >
                  Add Column Before
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().addColumnAfter().run()}
                >
                  Add Column After
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().addRowBefore().run()}
                >
                  Add Row Before
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().addRowAfter().run()}
                >
                  Add Row After
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().deleteRow().run()}
                >
                  Delete Row
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().deleteColumn().run()}
                >
                  Delete Column
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => editor.chain().focus().deleteTable().run()}
                >
                  Delete Table
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Table alignment buttons - only show when inside a table */}
        {editor?.isActive("table") && (
          <>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                editor
                  .chain()
                  .focus()
                  .setCellAttribute("textAlign", "left")
                  .run()
              }
              className={
                editor.getAttributes("tableCell").textAlign === "left"
                  ? "bg-muted"
                  : ""
              }
            >
              <AlignLeft className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                editor
                  .chain()
                  .focus()
                  .setCellAttribute("textAlign", "center")
                  .run()
              }
              className={
                editor.getAttributes("tableCell").textAlign === "center"
                  ? "bg-muted"
                  : ""
              }
            >
              <AlignCenter className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                editor
                  .chain()
                  .focus()
                  .setCellAttribute("textAlign", "right")
                  .run()
              }
              className={
                editor.getAttributes("tableCell").textAlign === "right"
                  ? "bg-muted"
                  : ""
              }
            >
              <AlignRight className="h-4 w-4" />
            </Button>
          </>
        )}
      </div>
      <div
        className="p-3 prose prose-sm dark:prose-invert max-w-none overflow-auto"
        style={{ height }}
      >
        <EditorContent editor={editor} className="h-full" />
      </div>
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
    </div>
  );
};

export default MarkdownEditor;
