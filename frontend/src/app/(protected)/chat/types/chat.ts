import { SelectedFile } from "@/store/slices/fileSearchSlice";

export interface ChatConversation {
  id: string;
  name: string | null;
  summary: string | null;
  model: string | null;
  created_at: string;
  updated_at: string;
  settings: {
    preview_feature_uses_artifacts: boolean;
    preview_feature_uses_latex: boolean | null;
    preview_feature_uses_citations: boolean | null;
    enabled_artifacts_attachments: boolean | null;
    enabled_turmeric: boolean | null;
  };
  is_starred: boolean;
  project_id: string | null;
  current_leaf_message_id: string | null;
  messages?: Message[];
}

export interface RecentConversation {
  conversations: ChatConversation[];
}

export interface Reference {
  type: string;
  title: string;
  content?: string;
  address?: string;
  description?: string;
}

export interface Message {
  id: string;
  content: string;
  metadata?: any;
  role: "user" | "assistant" | "system";
  parent_message_id: string;
  conversation_id: string;
  created_at: string;
  suggestions: Suggestion[];
  selected_suggestions?: Suggestion[];
  attachments?: Attachment[];
  artifacts?: Artifact[];
  references?: Reference[];
  isStreaming?: boolean;
  isThinking?: boolean;
  files?: SelectedFile[];
  tiptap_content?: string;
  isSetup?: boolean;
  metaContent?: ThinkingStep[];

  // New fields added
  model?: string;
  database_uid?: string;
  table_uid?: string;
  people?: any[]; // Define a more specific type if possible
  documents?: any[]; // Define a more specific type if possible
  follow_up_questions?: any[]; // Define a more specific type if possible
  skip_option?: boolean;
  codes?: any[]; // Define a more specific type if possible
  edited_at?: string;
  edited_by?: string;
  regenerating?: boolean;
  original_content?: any[]; // Define a more specific type if possible
  stop_reason?: string | null;
  stop_sequence?: string | null;
  index?: number;
  truncated?: boolean;
  sender?: string;
}

export interface ContentBlock {
  type: string;
  text?: string;
  suggestions?: Suggestion[];
  suggestion_block?: {
    suggestions: Suggestion[];
  };
}

export interface SuggestionBlock {
  type: "suggestions" | "suggestion_block";
  suggestions: Suggestion[];
}

export interface IntentContent {
  title: string;
  type: string;
  source_url: string;
  uploaded_by: string;
  description: string;
  text: string;
}

export interface Suggestion {
  type: "Document" | "Person" | "Text" | "PAL" | "QUERY";
  suggestion_content:
    | DocumentContent
    | PersonContent
    | TextContent
    | PALContent
    | IntentContent;
}

export interface PersonContent {
  Name: string;
  image: string;
  Position: string;
}

export interface TextContent {
  text: string;
}

export interface PALContent {
  title: string;
  description?: string;
  model?: string;
  type?: string;
  source_url?: string;
  uploaded_by?: string;
}

export interface DocumentContent {
  title: string;
  type: string;
  source_url?: string;
  date?: string;
  uploaded_by?: string;
  description?: string;
}

export interface Person {
  Name: string;
  image: string;
  Position: string;
  Role: string;
}

export interface PAL {
  model: string;
  title: string;
  description: string;
  image_url: string;
}

export interface CodeSnippet {
  type: string;
  title: string;
  content: string;
  language?: string;
}

// Base interfaces for different content types
export interface CodeContent {
  code: string;
  code_type?: string;
  explanation?: string;
}

export interface DataContent {
  payment_method?: string;
  city?: string;
  volume?: number;
  year?: number;
}

export interface MetadataContent {
  columns: Array<{
    name: string;
    display_name: string;
    type: string;
    icon: string;
    sortable: boolean;
    filterable: boolean;
    sample_values?: string[];
    format?: string;
    constraints?: {
      min?: number;
      max?: number;
    };
  }>;
}

// Update ArtifactType to include new types
export type ArtifactType =
  | "code"
  | "code_type"
  | "explanation"
  | "data"
  | "data_summary"
  | "rich_data_summary"
  | "metadata"
  | "columns"
  | "image"
  | "text"
  | "document"
  | "tsx"
  | "jsx"
  | "presentation"
  | "tiptap"
  | "chart"
  | string;

// Update DataContent to match the actual data structure
export interface DataContent {
  payment_method?: string;
  city?: string;
  volume?: number;
  year?: number;
}

// Add new interfaces for the new content types
export interface RichDataSummaryContent {
  summary: string;
  key_points: string[];
  data_shape: {
    error?: string;
    // Add other potential data shape properties here
  };
}

export interface ColumnsContent {
  name: string;
  display_name: string;
  type: string;
  icon: string;
  sortable: boolean;
  filterable: boolean;
  sample_values: string[];
}

// Update the Artifact interface to handle string or object content
export interface Artifact {
  artifact_type: ArtifactType;
  content:
    | CodeContent
    | DataContent
    | MetadataContent
    | RichDataSummaryContent
    | ColumnsContent
    | string;
  language?: string | null;
  title?: string | null;
  file_type?: string | null;
}

// Type guard functions for different artifact types
export const isCodeArtifact = (
  artifact: Artifact
): artifact is Artifact & { artifact_type: "code"; content: CodeContent } => {
  return artifact.artifact_type === "code";
};

export const isDataArtifact = (
  artifact: Artifact
): artifact is Artifact & { artifact_type: "data"; content: DataContent } => {
  return artifact.artifact_type === "data";
};

export const isMetadataArtifact = (
  artifact: Artifact
): artifact is Artifact & {
  artifact_type: "metadata";
  content: MetadataContent;
} => {
  return artifact.artifact_type === "metadata";
};

export interface Attachment {
  id?: string;
  file_name: string;
  file_size: number;
  file_type: string;
  extracted_content: string;
}

export interface ChatState {
  conversations: ChatConversation[];
  activeConversation: string | null;
  messages: Record<string, Message[]>;
  isLoading: boolean;
  error: string | null;
}

export interface Warning {
  id: string;
  type: "rate_limit" | "content_policy" | "usage" | "system";
  message: string;
  level: "info" | "warning" | "error";
  action?: {
    type: "acknowledge" | "upgrade" | "retry";
    label: string;
  };
}

export interface ConversationStatus {
  is_archived: boolean;
  last_activity: string;
  participant_count: number;
  rate_limit_remaining: number;
}

export interface ConversationUpdate {
  conversation: ChatConversation;
  messages: Message[];
  warnings: Warning[];
  status: ConversationStatus;
}

export interface ChatAttachment {
  id: string;
  type: string;
  // Add other relevant fields
}

export interface ChatFile {
  id: string;
  name: string;
  size: number;
  // Add other relevant fields
}

interface ChatMessage {
  content?: Array<{
    type: string;
    suggestions?: Suggestion[];
    // ... other content block properties
  }>;
  suggestions?: Suggestion[];
  // ... other message properties
}

export interface FileUploadState {
  id: string;
  file: File;
  status: "pending" | "uploading" | "processing" | "complete" | "error";
  progress: number;
  preview?: string;
  error?: string;
}

export interface EnhancedSuggestion extends Suggestion {
  category: "command" | "context" | "pal" | "general";
  priority: number;
  previewContent?: string;
  metadata?: Record<string, any>;
}

export interface SuggestionGroup {
  category: string;
  suggestions: EnhancedSuggestion[];
  isExpanded: boolean;
}

export interface SearchResponse {
  id: string;
  title: string;
  content: string;
  address: string;
}

export interface SelectedDataSource {
  type: "csv" | "database";
  name: string;
}

export interface ThinkingStep {
  id: string;
  title: string;
  status?: "completed" | "inprogress" | "pending" | "error";
  type?: string;
  description: ThinkingDescription[];
}

export interface ThinkingDescription {
  title: string;
  execution?: string;
  status: "completed" | "inprogress" | "pending" | "error";
  type?: string;
}
