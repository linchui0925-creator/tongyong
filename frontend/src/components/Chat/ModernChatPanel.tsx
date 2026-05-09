import { useState, useEffect, useRef, useCallback } from 'react';
import { streamChat, generateMessageId } from '../../api/stream';
import { getSessionMessages } from '../../api/memory';
import { Message } from '../../types';
import './ModernChatPanel.css';

interface ModernChatPanelProps {
  initialSessionId?: string;
}

function ModernChatPanel({ initialSessionId }: ModernChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [currentSessionId, setCurrentSessionId] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showHelp, setShowHelp] = useState(false);
  const [progressText, setProgressText] = useState<string>('');
  const [elapsed, setElapsed] = useState<number>(0);
  const [currentTool, setCurrentTool] = useState<{name: string; emoji: string; startTime: number} | null>(null);
  const [toolElapsed, setToolElapsed] = useState<number>(0);
  const [expandedThinkingMsgId, setExpandedThinkingMsgId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Sync session
  useEffect(() => {
    if (initialSessionId) setCurrentSessionId(initialSessionId);
  }, [initialSessionId]);

  // Load history
  const loadMessages = useCallback(async (sid: string) => {
    if (!sid) return;
    try {
      const data = await getSessionMessages(sid);
      const msgs: Message[] = (data.messages || []).map((m: any, i: number) => ({
        id: m.id || `msg-${i}`,
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at || Date.now()).getTime(),
        status: 'completed' as const,
      }));
      setMessages(msgs);
    } catch {
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    if (currentSessionId) loadMessages(currentSessionId);
  }, [currentSessionId, loadMessages]);

  // Auto-scroll — only when user is near the bottom
  const handleScroll = useCallback(() => {
    const el = messagesRef.current;
    if (el) {
      const threshold = 120;
      isNearBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    }
  }, []);

  useEffect(() => {
    if (isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const handleSend = useCallback(async () => {
    const text = inputValue.trim();
    if (!text || isLoading || isStreaming) return;

    abortRef.current?.abort();
    abortRef.current = null;

    const uid = generateMessageId();
    const aid = generateMessageId();

    setMessages(prev => [...prev,
      { id: uid, role: 'user', content: text, timestamp: Date.now(), status: 'completed' },
      { id: aid, role: 'assistant', content: '', timestamp: Date.now(), status: 'streaming' },
    ]);
    setInputValue('');
    setIsLoading(true);
    setErrorMessage(null);
    setElapsed(0);
    setToolElapsed(0);
    setCurrentTool(null);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsed(prev => prev + 100);
      setToolElapsed(prev => prev + 100);
    }, 100);
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    abortRef.current = streamChat(text, currentSessionId || undefined, true, {
      onStart: () => {
        setIsStreaming(true);
        setProgressText('连接中...');
        setExpandedThinkingMsgId(null);
      },
      onProgress: (content) => {
        setProgressText(content);
      },
      onToolStart: (toolName, _args, emoji) => {
        setToolElapsed(0);
        setCurrentTool({ name: toolName, emoji, startTime: Date.now() });
      },
      onToolComplete: (_toolName, _preview, _duration, _emoji) => {
        setCurrentTool(null);
      },
      onToolError: (_toolName, _error, _emoji) => {
        setCurrentTool(null);
      },
      onToolFeedback: (_content) => {
        // 忽略工具反馈，不显示在回复内容中
      },
      onThinkingDelta: (content) => {
        setMessages(prev => prev.map(m =>
          m.id === aid ? { ...m, thinking: (m.thinking || '') + content } : m
        ));
      },
      onThinkingDone: () => {
        // thinking done
      },
      onContent: (_chunk, full) => {
        setProgressText('');
        // 提取 thinking 内容并过滤
        const thinkMatch = full.match(/<think>([\s\S]*?)晖/);
        const thinking = thinkMatch ? thinkMatch[1] : '';
        const displayContent = full.replace(/<think>[\s\S]*?晖/g, '').trim();
        setMessages(prev => prev.map(m =>
          m.id === aid ? { ...m, content: displayContent, thinking: thinking || m.thinking, status: 'streaming' as const } : m
        ));
      },
      onDone: () => {
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        setProgressText('');
        setMessages(prev => prev.map(m =>
          m.id === aid ? { ...m, status: 'completed' as const } : m
        ));
        setIsStreaming(false);
        setIsLoading(false);
        abortRef.current = null;
      },
      onError: (err) => {
        if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
        setProgressText('');
        setErrorMessage(err);
        setMessages(prev => prev.map(m =>
          m.id === aid ? { ...m, status: 'error' as const, error: err } : m
        ));
        setIsStreaming(false);
        setIsLoading(false);
        abortRef.current = null;
      },
    });
  }, [inputValue, isLoading, isStreaming, currentSessionId]);

  const handleStop = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    abortRef.current?.abort();
    setIsStreaming(false);
    setIsLoading(false);
    setProgressText('');
    setMessages(prev => prev.map(m =>
      m.status === 'streaming' ? { ...m, status: 'completed' as const } : m
    ));
  }, []);

  const handleDelete = useCallback((id: string) => {
    setMessages(prev => prev.filter(m => m.id !== id));
  }, []);

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, []);

  const handleKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);

  return (
    <div className="chat-panel">
      {errorMessage && (
        <div className="chat-error">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)}>×</button>
        </div>
      )}

      <div className="chat-toolbar">
        <button className="btn btn-ghost" onClick={() => setShowHelp(!showHelp)}>
          {showHelp ? '收起帮助' : '帮助'}
        </button>
      </div>

      {showHelp && (
        <div className="chat-help">
          <div className="chat-help-section">
            <strong>📋 什么是对话？</strong>
            <p>在这里与 AI Agent 进行交流。Agent 会结合上下文、记忆和技能来回应你的问题。</p>
          </div>
          <div className="chat-help-section">
            <strong>📖 使用说明</strong>
            <ul>
              <li><strong>发送消息</strong> — 在输入框中输入内容，按 <kbd>Enter</kbd> 发送</li>
              <li><strong>换行</strong> — 按 <kbd>Shift</kbd>+<kbd>Enter</kbd> 换行</li>
              <li><strong>停止生成</strong> — Agent 回复时点击输入框旁的停止按钮可中断</li>
              <li><strong>删除消息</strong> — 鼠标悬停消息可删除单条记录</li>
              <li>Agent 会自动利用记忆、人格设定和技能来提供更精准的回答</li>
            </ul>
          </div>
        </div>
      )}

      <div className="chat-messages" ref={messagesRef} onScroll={handleScroll}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-marker">✦</div>
            <p>开始新对话</p>
            <span className="chat-empty-hint">Enter 发送 · Shift+Enter 换行</span>
          </div>
        ) : (
          <>
            {messages.map((msg) => {
              const isUser = msg.role === 'user';
              return (
                <div key={msg.id}>
                  {isUser ? (
                    <div className="chat-msg chat-msg--user">{msg.content}</div>
                  ) : (
                    <div className={`chat-msg chat-msg--assistant chat-msg--${msg.status}`}>
                      {msg.status === 'streaming' && !msg.content ? (
                        <div className="chat-thinking">
                          {progressText || '思考'}
                          <span className="chat-elapsed">{(elapsed / 1000).toFixed(1)}s</span>
                          <span className="chat-thinking-dots">
                            <span /><span /><span />
                          </span>
                        </div>
                      ) : (
                        <>
                          {msg.content}
                          {msg.status === 'streaming' && <span className="chat-cursor" />}
                          {msg.status === 'streaming' && <span className="chat-elapsed">{(elapsed / 1000).toFixed(1)}s</span>}
                        </>
                      )}
                      {/* 思考过程展开按钮 */}
                      {msg.thinking && (
                        <div className="chat-thinking-toggle">
                          <button
                            className="chat-thinking-btn"
                            onClick={() => setExpandedThinkingMsgId(
                              expandedThinkingMsgId === msg.id ? null : msg.id
                            )}
                          >
                            💭 {expandedThinkingMsgId === msg.id ? '收起' : '查看'}思考过程
                          </button>
                          {expandedThinkingMsgId === msg.id && (
                            <div className="chat-thinking-content">
                              {msg.thinking}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  {/* Meta row (time + delete on hover) */}
                  <div className="chat-meta" style={{ justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
                    <span className="chat-time">
                      {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {msg.status === 'error' && <span style={{ color: 'var(--danger)', fontSize: 12 }}>!</span>}
                    <button className="chat-delete" onClick={() => handleDelete(msg.id)} title="删除">×</button>
                  </div>
                </div>
              );
            })}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 工具执行仪表板 — 仅显示当前正在运行的工具 */}
      {currentTool && (
        <div className="chat-tools-dashboard">
          <div className="tool-item tool-item--running">
            <span className="tool-emoji">{currentTool.emoji}</span>
            <span className="tool-name">{currentTool.name}</span>
            <span className="tool-spinner"><span /><span /><span /></span>
            <span className="tool-duration tool-duration--live">{(toolElapsed / 1000).toFixed(1)}s</span>
          </div>
        </div>
      )}
      {/* 进度提示（无工具调用时） */}
      {isStreaming && !currentTool && (
        <div className="chat-statusbar">
          <span className="chat-statusbar-dot" />
          <span className="chat-statusbar-text">{progressText || '思考中...'}</span>
          <span className="chat-statusbar-elapsed">{(elapsed / 1000).toFixed(1)}s</span>
        </div>
      )}

      <div className="chat-input">
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleInput}
            onKeyDown={handleKey}
            placeholder="输入消息..."
            disabled={isLoading && !isStreaming}
            rows={1}
          />
          <div>
            {isStreaming ? (
              <button className="chat-stop-btn" onClick={handleStop} title="停止">■</button>
            ) : (
              <button className="chat-send-btn" onClick={handleSend} disabled={!inputValue.trim() || isLoading} title="发送">→</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ModernChatPanel;
