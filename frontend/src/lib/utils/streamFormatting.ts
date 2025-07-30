export const formatStreamContent = (content: string): string => {
  let formattedContent = content;

  formattedContent = formattedContent.replace(
    /```(\w+)?\n([\s\S]*?)```/g,
    (match, lang, code) => {
      return `\`\`\`${lang || ""}\n${code.trim()}\`\`\``;
    }
  );

  formattedContent = formattedContent.replace(
    /`([^`]+)`/g,
    (match, code) => `\`${code}\``
  );

  formattedContent = formattedContent.replace(
    /^(#{1,6})\s(.+)$/gm,
    (match, hashes, text) => `${hashes} ${text}`
  );

  formattedContent = formattedContent.replace(
    /^(\s*[-*+]|\d+\.)\s(.+)$/gm,
    (match, bullet, text) => `${bullet} ${text}`
  );

  formattedContent = formattedContent.replace(
    /\*\*(.+?)\*\*/g,
    (match, text) => `**${text}**`
  );

  formattedContent = formattedContent.replace(
    /\*(.+?)\*/g,
    (match, text) => `*${text}*`
  );

  return formattedContent;
};

export const isMarkdownBlockStart = (content: string): boolean => {
  return /^(```|#{1,6}\s|[*-+]\s|\d+\.\s)/.test(content);
};

export const isMarkdownBlockEnd = (content: string): boolean => {
  return content.includes("```") || content.endsWith("\n");
};
