/**
 * 前端类型定义模块
 * 统一管理所有TypeScript接口和类型
 */

/** 消息角色枚举 */
export type MessageRole = 'user' | 'assistant' | 'system';

/** 消息状态枚举 */
export type MessageStatus = 'sending' | 'streaming' | 'completed' | 'error';

/** 对话消息接口 */
export interface Message {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: number;
    status: MessageStatus;
    error?: string;
    /** 提取的思考过程内容 */
    thinking?: string;
}

/** 会话信息接口 */
export interface Session {
    id: string;
    name: string;
    created_at: string;
    updated_at: string;
    message_count?: number;
}

/** 聊天请求参数 */
export interface ChatRequest {
    message: string;
    session_id?: string;
    use_memory?: boolean;
}

/** 聊天响应数据 */
export interface ChatResponse {
    reply: string;
    session_id: string;
    memory_added?: any[];
    memory_verification?: any;
    tools_used?: string[];
    processing_time?: number;
}

/** 流式事件类型 */
export type StreamEventType = 'start' | 'content' | 'done' | 'error' | 'progress'
    | 'tool_start' | 'tool_complete' | 'tool_error' | 'tool_feedback';

/** 工具事件数据 */
export interface ToolEvent {
    tool_name: string;
    arguments?: Record<string, any>;
    result_preview?: string;
    duration?: number;
    error?: boolean;
    emoji: string;
    timestamp: number;
}

/** 流式事件数据 */
export interface StreamEvent {
    type: StreamEventType;
    content?: string;
    full_content?: string;
    session_id?: string;
    memory_added?: any[];
    tools_used?: string[];
    commands_executed?: string[];
    processing_time?: number;
    timestamp: number;
    error?: string;
    code?: string;
    emoji?: string;
    tool_name?: string;
    arguments?: Record<string, any>;
    result_preview?: string;
    duration?: number;
}

/** SSE事件源 */
export interface SSECallbacks {
    onStart?: () => void;
    onProgress?: (content: string) => void;
    onContent?: (content: string, fullContent: string) => void;
    onDone?: (data: StreamEvent) => void;
    onError?: (error: string) => void;
    /** 工具开始执行 */
    onToolStart?: (toolName: string, args: Record<string, any>, emoji: string) => void;
    /** 工具执行完成 */
    onToolComplete?: (toolName: string, preview: string, duration: number, emoji: string) => void;
    /** 工具执行出错 */
    onToolError?: (toolName: string, error: string, emoji: string) => void;
    /** 工具执行反馈（如已调用工具列表） */
    onToolFeedback?: (content: string) => void;
    /** 思考过程增量 */
    onThinkingDelta?: (content: string) => void;
    /** 思考过程完成 */
    onThinkingDone?: () => void;
}

/** UI主题配置 */
export interface ThemeConfig {
    primaryColor: string;
    secondaryColor: string;
    backgroundColor: string;
    textColor: string;
    borderRadius: number;
    fontFamily: string;
}

/** 用户偏好设置 */
export interface UserPreferences {
    theme: 'light' | 'dark' | 'auto';
    fontSize: number;
    streamingSpeed: number;
    showTimestamps: boolean;
    enableKeyboardShortcuts: boolean;
    autoScroll: boolean;
}

/** 确认对话框配置 */
export interface ConfirmDialogConfig {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    type?: 'warning' | 'danger' | 'info';
    onConfirm: () => void;
    onCancel?: () => void;
}

/** 快捷键配置 */
export interface KeyboardShortcut {
    key: string;
    ctrl?: boolean;
    shift?: boolean;
    alt?: boolean;
    meta?: boolean;
    action: () => void;
    description: string;
}

/** 头像配置 */
export interface AvatarConfig {
    type: 'image' | 'emoji';
    value: string;
}

/** 打字机效果配置 */
export interface TypewriterConfig {
    enabled: boolean;
    speed: number;
    minDelay: number;
    maxDelay: number;
}
