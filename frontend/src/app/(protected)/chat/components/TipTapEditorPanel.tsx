import { useEditor, EditorContent, AnyExtension } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Code } from "@tiptap/extension-code";
import CodeBlockComponent from "@tiptap/extension-code-block";
import { Image as TiptapImage } from "@tiptap/extension-image";
import { useEffect, useMemo, useState } from "react";
import { Paragraph } from "@tiptap/extension-paragraph";
import { Heading } from "@tiptap/extension-heading";
import { BulletList } from "@tiptap/extension-bullet-list";
import ListItem from "@tiptap/extension-list-item";
import { Button } from "@/components/ui/button";
import { Document } from "@tiptap/extension-document";
import { Text } from "@tiptap/extension-text";
import { Editor } from "@tiptap/react";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableHeader } from "@tiptap/extension-table-header";
import { TableCell } from "@tiptap/extension-table-cell";
import { Export, ExportContext } from "@tiptap-pro/extension-export";
import { toast } from "react-hot-toast";
import { generateTiptapToken } from "@/app/api/tiptap/actions";
// import { getTiptapToken } from "@/app/api/tiptap/route";

interface TipTapEditorPanelProps {
  content: string;
}

interface ToolbarButtonProps {
  isActive?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({
  isActive,
  onClick,
  children,
}) => (
  <Button
    onClick={onClick}
    variant={isActive ? "default" : "secondary"}
    size="sm"
  >
    {children}
  </Button>
);

interface EditorToolbarProps {
  editor: Editor | null;
}

const EditorToolbar: React.FC<EditorToolbarProps> = ({ editor }) => {
  const handleImageUpload = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const base64 = e.target?.result as string;
          editor?.chain().focus().setImage({ src: base64 }).run();
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  };

  const downloadAsDocx = () => {
    if (!editor) return;

    editor
      .chain()
      .focus()
      .export({
        format: "docx",
        onExport(context: ExportContext) {
          if (context.error) {
            console.error("Export error:", context.error);
            toast.error("Error exporting document");
            return;
          }
          context.download();
        },
      })
      .run();
  };

  const downloadAsMarkdown = () => {
    if (!editor) return;
    editor
      .chain()
      .focus()
      .export({
        format: "md",
        onExport(context: ExportContext) {
          if (context.error) {
            console.error("Export error:", context.error);
            toast.error("Error exporting document");
            return;
          }
          context.download();
        },
      })
      .run();
  };

  if (!editor) return null;

  return (
    <div className="flex flex-col border-b border-border">
      <div className="flex items-center justify-between p-4">
        <h3 className="text-lg font-medium">Document Viewer</h3>
        <Button
          onClick={downloadAsDocx}
          variant="secondary"
          size="sm"
          className="bg-foreground text-background hover:bg-foreground/80"
        >
          Export DOCX
        </Button>
      </div>
      {/*  <div className="flex gap-2 p-2 overflow-x-auto">
         <ToolbarButton
          onClick={() => editor.chain().focus().undo().run()}
          isActive={false}
        >
          Undo
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().redo().run()}
          isActive={false}
        >
          Redo
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("heading", { level: 1 })}
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 1 }).run()
          }
        >
          H1
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("heading", { level: 2 })}
          onClick={() =>
            editor.chain().focus().toggleHeading({ level: 2 }).run()
          }
        >
          H2
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("bold")}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          Bold
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("italic")}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          Italic
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("strike")}
          onClick={() => editor.chain().focus().toggleStrike().run()}
        >
          Strike
        </ToolbarButton>
        <ToolbarButton
          isActive={editor.isActive("bulletList")}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          List
        </ToolbarButton>
        <Button
          className="bg-foreground text-background hover:bg-foreground/80"
          onClick={handleImageUpload}
          variant="secondary"
          size="sm"
        >
          Upload Image
        </Button> 
        <div className="ml-auto flex gap-2">
          <Button
            onClick={downloadAsDocx}
            variant="secondary"
            size="sm"
            className="bg-foreground text-background hover:bg-foreground/80"
          >
            Export DOCX
          </Button>
           <Button
            onClick={downloadAsMarkdown}
            variant="secondary"
            size="sm"
            className="bg-foreground text-background hover:bg-foreground/80"
          >
            Export MD
          </Button> 
        </div> 
      </div> */}
    </div>
  );
};

export const TipTapEditorPanel: React.FC<TipTapEditorPanelProps> = ({
  content,
}) => {
  // Format TipTap JSON content if needed
  const formattedContent = useMemo(() => {
    try {
      // First try to evaluate the string as a JavaScript object
      // This handles cases where the content is a stringified JS object with properties like 'report'
      let parsedContent;
      try {
        // Using Function constructor to safely evaluate the string as JS object
        parsedContent = Function(`'use strict'; return (${content})`)();
      } catch {
        // If JS eval fails, try parsing as JSON
        const cleanContent = content.replace(/\n/g, "").replace(/\s/g, "");
        parsedContent = JSON.parse(cleanContent);
      }

      // If it's already in TipTap format with type: "doc"
      if (parsedContent?.type === "doc") {
        return parsedContent;
      }

      // If it's in our wrapped format with report property
      if (parsedContent?.report?.type === "doc") {
        return parsedContent.report;
      }

      // If it's any other JSON/object, display it as a code block
      return {
        type: "doc",
        content: [
          {
            type: "codeBlock",
            attrs: { language: "json" },
            content: [
              {
                type: "text",
                text: JSON.stringify(parsedContent, null, 2),
              },
            ],
          },
        ],
      };
    } catch (error) {
      console.error("Error parsing content:", error);
      // If parsing fails, display as plain text
      return {
        type: "doc",
        content: [
          {
            type: "paragraph",
            content: [{ type: "text", text: content || "" }],
          },
        ],
      };
    }
  }, [content]);

  const [tiptapToken, setTiptapToken] = useState<string>("");

  useEffect(() => {
    generateTiptapToken().then((response) => {
      setTiptapToken(response.token);
    });
  }, []);

  // Define extensions using useMemo
  const extensions = useMemo(
    () => [
      StarterKit.configure({
        document: false,
        text: false,
        codeBlock: false,
        gapcursor: false, // Explicitly disable gapcursor
      }),
      Document.configure({
        content: "block+",
      }),
      Paragraph,
      Text,
      Heading,
      BulletList,
      ListItem,
      CodeBlockComponent.configure({
        HTMLAttributes: {
          class:
            "bg-foreground/5 p-4 rounded-md font-mono text-foreground dark:bg-zinc-800",
        },
      }),
      TiptapImage.configure({
        allowBase64: true,
        inline: false,
        HTMLAttributes: {
          class: "max-w-full h-auto my-2 shadow-md",
        },
      }),
      Code,
      Table.configure({
        // HTMLAttributes: {
        //   class: "border-collapse table-auto pointer-events-none",
        // },
        resizable: true,
        allowTableNodeSelection: false,
      }),
      TableRow,
      TableHeader.configure({
        // HTMLAttributes: {
        //   class:
        //     "border border-foreground/20 bg-muted p-2 font-bold pointer-events-none",
        // },
      }),
      TableCell.configure({
        // HTMLAttributes: {
        //   class: "border border-foreground/20 p-2 pointer-events-none",
        // },
      }),
      // Gapcursor,
      Export.configure({
        appId: process.env.NEXT_PUBLIC_TIPTAP_CONVERT_APP_ID,
        token: tiptapToken,
      }),
    ],
    [tiptapToken]
  );

  const editor = useEditor(
    {
      extensions: extensions as AnyExtension[],
      content: formattedContent,
      editable: false,
      editorProps: {
        attributes: {
          class: "focus:outline-none",
        },
      },
      parseOptions: {
        preserveWhitespace: "full",
      },
    },
    [extensions, tiptapToken]
  );

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      <EditorToolbar editor={editor} />
      <div className="flex-1 overflow-y-auto bg-foreground/10 p-4 md:p-8">
        <div className="max-w-[21cm] mx-auto space-y-8">
          {editor && (
            <EditorContent
              editor={editor}
              className="prose dark:prose-invert prose-sm sm:prose-base max-w-none
                [&_img]:max-w-[90%] [&_img]:my-2 
                [&_pre]:bg-muted [&_pre]:dark:bg-zinc-800
                text-left prose-p:text-left prose-headings:text-left 
                bg-background p-4 md:p-[2.54cm] border border-border shadow-md
                [caret-color:theme(colors.foreground)] focus:outline-none
                min-h-[29.7cm] w-full md:w-[21cm]"
            />
          )}
        </div>
      </div>
    </div>
  );
};
