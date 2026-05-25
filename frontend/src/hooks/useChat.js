import { useState, useRef, useCallback } from 'react';

const API_BASE = '';
const CHAT_ENDPOINT = `${API_BASE}/api/model/chat`;
const HEALTH_ENDPOINT = `${API_BASE}/health`;

function generateSessionId() {
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function useChat() {
  const [sessionId, setSessionId] = useState(generateSessionId);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [backendOk, setBackendOk] = useState(null); // null = checking, true/false
  const abortRef = useRef(null);

  // Health check
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(HEALTH_ENDPOINT);
      const data = await res.json();
      setBackendOk(data.status === 'ok');
      return data.status === 'ok';
    } catch {
      setBackendOk(false);
      return false;
    }
  }, []);

  // New session
  const newSession = useCallback(() => {
    if (isStreaming) {
      abortRef.current?.abort();
    }
    setSessionId(generateSessionId());
    setMessages([]);
    setIsStreaming(false);
    abortRef.current = null;
  }, [isStreaming]);

  // Send message
  const sendMessage = useCallback(async (text, attachments) => {
    if (isStreaming) return;
    if (!text && attachments.length === 0) return;

    // Build message content — reference file paths instead of inlining content
    let content = '';
    if (attachments.length > 0) {
      content += attachments.map((f, i) =>
        `[附件 ${i + 1}: ${f.name} → ${f.path}]`
      ).join('\n');
      content += '\n\n';
    }
    content += text || '请使用 view_file 工具读取以上附件。';

    const attachmentMeta = {
      files: attachments.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type,
        path: f.path,
      })),
    };

    const attachmentNames = attachments.map(f => f.name);

    // Add user message
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text || '[附件]',
      attachmentNames,
      timestamp: Date.now(),
    };

    // Create placeholder for agent response
    const agentMsg = {
      id: `agent-${Date.now()}`,
      role: 'agent',
      content: '',
      thinking: '',
      isStreaming: true,
      timestamp: Date.now(),
    };

    setMessages(prev => [...prev, userMsg, agentMsg]);
    setIsStreaming(true);

    const abortController = new AbortController();
    abortRef.current = abortController;

    try {
      const response = await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          linkId: `fe-${Date.now()}`,
          sessionId,
          userId: 1,
          functionId: 1,
          messages: [{ role: 'user', content }],
          attachment: attachmentMeta,
          callTools: true,
          XAPIVersion: 1,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${response.status}`);
      }

      // Process SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let agentText = '';
      let thinkingText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let data;
          try { data = JSON.parse(line.slice(6)); }
          catch { continue; }

          if (data.message === '[stop]') {
            setMessages(prev => prev.map(m =>
              m.id === agentMsg.id
                ? { ...m, content: agentText, thinking: thinkingText, isStreaming: false }
                : m
            ));
            setIsStreaming(false);
            abortRef.current = null;
            return;
          }

          if (data.reasoningMessage) {
            thinkingText += data.reasoningMessage;
            setMessages(prev => prev.map(m =>
              m.id === agentMsg.id ? { ...m, thinking: thinkingText } : m
            ));
          }

          if (data.message && data.message !== '[stop]') {
            agentText += data.message;
            setMessages(prev => prev.map(m =>
              m.id === agentMsg.id ? { ...m, content: agentText } : m
            ));
          }
        }
      }

      // Stream ended without [stop]
      setMessages(prev => prev.map(m =>
        m.id === agentMsg.id
          ? { ...m, content: agentText, thinking: thinkingText, isStreaming: false }
          : m
      ));
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages(prev => prev.map(m =>
          m.id === agentMsg.id
            ? { ...m, isStreaming: false, content: m.content || '[已终止]' }
            : m
        ));
      } else {
        setMessages(prev => prev.map(m =>
          m.id === agentMsg.id
            ? { ...m, isStreaming: false, content: `[请求失败: ${err.message}]` }
            : m
        ));
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [isStreaming, sessionId]);

  // Abort stream
  const abortStream = useCallback(async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    // Also signal backend
    try {
      await fetch(CHAT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          linkId: 'fe-abort',
          sessionId,
          userId: 1,
          messages: [{ role: 'user', content: '' }],
          type: -1,
        }),
      });
    } catch { /* best effort */ }
  }, [sessionId]);

  return {
    sessionId,
    messages,
    isStreaming,
    backendOk,
    checkHealth,
    newSession,
    sendMessage,
    abortStream,
  };
}
