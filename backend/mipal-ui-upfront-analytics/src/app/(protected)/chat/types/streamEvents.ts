export interface MessageMetadata {
  id: string;
  type: "message";
  role: "assistant";
  model: string;
  parent_uuid: string;
  uuid: string;
  content: any[];
  stop_reason?: string;
  stop_sequence?: string;
}

export interface MessageStartEvent {
  type: "message_start";
  message: MessageMetadata;
}

export interface ContentBlock {
  type: "text";
  text: string;
}

export interface ContentBlockStartEvent {
  type: "content_block_start";
  index: number;
  content_block: ContentBlock;
}

export interface TextDelta {
  type: "text_delta";
  text: string;
}

export interface ContentBlockDeltaEvent {
  type: "content_block_delta";
  index: number;
  delta: TextDelta;
}

export interface ContentBlockStopEvent {
  type: "content_block_stop";
  index: number;
}

export interface MessageDeltaData {
  stop_reason: string;
  stop_sequence?: string;
}

export interface MessageDeltaEvent {
  type: "message_delta";
  delta: MessageDeltaData;
}

export interface MessageStopEvent {
  type: "message_stop";
}

export interface ErrorData {
  message: string;
  type: string;
}

export interface ErrorEvent {
  type: "error";
  error: ErrorData;
}

export interface ChatCompletionRequest {
  prompt: string;
  parent_message_id: string;
  attachments: any[];
  files: string[];
  rendering_mode: "messages";
  sync_sources: any[];
  timezone: string;
  web_search: boolean;
}
