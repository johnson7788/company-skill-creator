import React, { useRef, useEffect } from 'react';

export default function ChatInput({ onSend, onStop, isStreaming, onFilesAdded }) {
  const [text, setText] = React.useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!isStreaming && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isStreaming]);

  const handleSend = () => {
    if (!text.trim() || isStreaming) return;
    onSend(text);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      onFilesAdded(e.target.files);
    }
    e.target.value = '';
  };

  return (
    <footer className="input-area">
      <div className="input-row">
        <label className="btn-upload" title="上传附件">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
          </svg>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".md,.txt,.py,.js,.ts,.yaml,.yml,.json,.xml,.csv,.html,.css,.java,.go,.rs,.sh,.bash,.toml,.ini,.cfg,.env.example"
            onChange={handleFileChange}
            hidden
          />
        </label>
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="输入你的问题，或上传附件后开始对话..."
          rows="1"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          autoFocus
        />
        {isStreaming ? (
          <button className="btn-stop" onClick={onStop} title="停止生成">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1"/>
            </svg>
          </button>
        ) : (
          <button
            className="btn-send"
            onClick={handleSend}
            disabled={!text.trim()}
            title="发送"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        )}
      </div>
    </footer>
  );
}
