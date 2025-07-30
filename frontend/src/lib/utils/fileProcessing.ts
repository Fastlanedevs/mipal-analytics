import { Artifact, Attachment } from "@/app/(protected)/chat/types/chat";

const COMPLEX_FILE_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document", // docx
  "application/msword", // doc
  "application/vnd.openxmlformats-officedocument.presentationml.presentation", // pptx
  "application/vnd.ms-powerpoint", // ppt
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
];

export const isComplexFile = (file: File): boolean => {
  return COMPLEX_FILE_TYPES.includes(file.type);
};

export const isTextFile = (file: File): boolean => {
  const textTypes = [
    // Basic text formats
    "text/plain",
    "text/csv",
    "text/markdown",
    "text/x-markdown",

    // Web development
    "application/json",
    "text/javascript",
    "application/javascript",
    "text/typescript",
    "application/typescript",
    "text/x-typescript",
    "application/x-typescript",
    "text/tsx",
    "application/x-tsx",
    "text/jsx",
    "text/html",
    "text/css",
    "text/x-scss",
    "text/x-sass",
    "text/x-less",
    "text/xml",
    "application/xml",
    "text/yaml",
    "application/x-yaml",

    // Programming languages
    "text/x-python",
    "text/x-java",
    "text/x-c",
    "text/x-cpp",
    "text/x-csharp",
    "text/x-ruby",
    "text/x-php",
    "text/x-go",
    "text/x-rust",
    "text/x-swift",

    // Config files
    "text/x-properties",
    "text/x-toml",
    "text/x-ini",
    "text/x-env",

    // Documentation
    "text/x-rst",
    "text/x-tex",
    "text/x-log",
  ];

  // Check file extension if MIME type is not recognized
  const fileExtension = file.name.split(".").pop()?.toLowerCase() || "";
  const textExtensions = [
    // Basic text formats
    "txt",
    "csv",
    "md",
    "markdown",

    // Web development
    "js",
    "jsx",
    "ts",
    "tsx",
    "html",
    "htm",
    "css",
    "scss",
    "sass",
    "less",
    "json",
    "xml",
    "svg",
    "yaml",
    "yml",

    // Programming languages
    "py",
    "java",
    "c",
    "cpp",
    "h",
    "hpp",
    "cs",
    "rb",
    "php",
    "go",
    "rs",
    "swift",
    "kt",
    "scala",
    "dart",
    "lua",
    "r",

    // Config files
    "env",
    "ini",
    "conf",
    "config",
    "toml",
    "properties",
    "prop",
    "gitignore",
    "dockerignore",
    "lock",
    "editorconfig",

    // Documentation
    "rst",
    "tex",
    "log",

    // Shell scripts
    "sh",
    "bash",
    "zsh",
    "fish",
    "bat",
    "cmd",
    "ps1",

    // Other common text files
    "sql",
    "graphql",
    "prisma",
    "vue",
    "svelte",
    "astro",
  ];

  return (
    textTypes.includes(file.type) || textExtensions.includes(fileExtension)
  );
};

export const readTextFile = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.onerror = reject;
    reader.readAsText(file);
  });
};

export const processFiles = async (
  files: File[]
): Promise<{
  attachments: Attachment[];
  artifacts: Artifact[];
}> => {
  const attachments: Attachment[] = [];
  const artifacts: Artifact[] = [];

  for (const file of files) {
    if (isComplexFile(file)) {
      // For complex files, upload to backend first
      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/proxy/chat/extract", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error("Failed to upload file");
        }

        const data = await response.json();

        // Add to attachments with extracted content from backend
        attachments.push({
          file_name: file.name,
          file_size: file.size,
          file_type: file.type,
          extracted_content: data.extracted_content || "",
        });
      } catch (error) {
        console.error("Failed to upload file:", error);
        // Add to attachments without extracted content
        attachments.push({
          file_name: file.name,
          file_size: file.size,
          file_type: file.type,
          extracted_content: "",
        });
      }
    } else if (isTextFile(file)) {
      // Handle text files locally
      const content = await readTextFile(file);
      attachments.push({
        file_name: file.name,
        file_size: file.size,
        file_type: file.type,
        extracted_content: content,
      });

      artifacts.push({
        artifact_type: "text",
        content,
        title: file.name,
        file_type: file.type,
      });
    }
  }

  return { attachments, artifacts };
};
