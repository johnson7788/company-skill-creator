import React, { useEffect, useRef, useCallback } from 'react';
import ChatArea from './components/ChatArea';
import ChatInput from './components/ChatInput';
import AttachmentBar from './components/AttachmentBar';
import useChat from './hooks/useChat';
import useAttachments from './hooks/useAttachments';

export default function App() {
  const {
    sessionId,
    messages,
    isStreaming,
    backendOk,
    checkHealth,
    newSession,
    sendMessage,
    abortStream,
  } = useChat();

  const {
    attachments,
    isUploading,
    addFiles,
    removeAttachment,
    clearAttachments,
    popAttachments,
    formatFileSize,
  } = useAttachments(sessionId);

  const chatAreaRef = useRef(null);
  const toastTimer = useRef(null);

  // Check health on mount
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Auto-scroll when messages change
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [messages]);

  // Drag & drop on chat area
  useEffect(() => {
    const el = chatAreaRef.current;
    if (!el) return;

    const onDragOver = (e) => { e.preventDefault(); e.stopPropagation(); };
    const onDrop = (e) => {
      e.preventDefault(); e.stopPropagation();
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    };
    el.addEventListener('dragover', onDragOver);
    el.addEventListener('drop', onDrop);
    return () => {
      el.removeEventListener('dragover', onDragOver);
      el.removeEventListener('drop', onDrop);
    };
  }, [addFiles]);

  // Toast
  const showToast = useCallback((message) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    const toast = document.createElement('div');
    toast.className = 'toast error';
    toast.textContent = message;
    document.body.appendChild(toast);
    toastTimer.current = setTimeout(() => toast.remove(), 3000);
  }, []);

  // Show backend unreachable warning
  useEffect(() => {
    if (backendOk === false) {
      showToast('后端服务不可达，请确认服务已启动');
    }
  }, [backendOk, showToast]);

  const handleSend = useCallback((text) => {
    const files = popAttachments();
    sendMessage(text, files);
  }, [sendMessage, popAttachments]);

  const handleStop = useCallback(() => {
    abortStream();
  }, [abortStream]);

  const handleNewSession = useCallback(() => {
    clearAttachments();
    newSession();
  }, [clearAttachments, newSession]);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">Company Skill Creator</h1>
        <div className="header-actions">
          <button className="btn btn-sm btn-outline" onClick={handleNewSession} disabled={isStreaming}>
            + 新会话
          </button>
          <span className="session-badge">{sessionId}</span>
        </div>
      </header>

      <div className="chat-area-wrapper" ref={chatAreaRef}>
        <ChatArea messages={messages} isStreaming={isStreaming} />
      </div>

      <AttachmentBar
        attachments={attachments}
        onRemove={removeAttachment}
        onClear={clearAttachments}
        formatSize={formatFileSize}
      />

      <ChatInput
        onSend={handleSend}
        onStop={handleStop}
        isStreaming={isStreaming}
        onFilesAdded={addFiles}
      />
    </div>
  );
}
