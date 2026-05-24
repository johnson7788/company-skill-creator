import React from 'react';

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export default function ChatArea({ messages, isStreaming }) {
  if (messages.length === 0) {
    return (
      <main className="chat-area">
        <div className="welcome-message">
          <div className="welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <h2>欢迎使用 Skill Creator</h2>
          <p>上传你的文档、代码或规范文件，我会帮你创建高质量的 Claude Code Skill。</p>
          <p className="welcome-hint">你可以直接输入问题，或先上传附件材料再开始对话。</p>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-area" id="chatArea">
      <div className="message-list">
        {messages.map(msg =>
          msg.role === 'user' ? (
            <UserMessage key={msg.id} msg={msg} />
          ) : (
            <AgentMessage key={msg.id} msg={msg} isStreaming={!!msg.isStreaming} />
          )
        )}
      </div>
    </main>
  );
}

function UserMessage({ msg }) {
  return (
    <div className="message user">
      <div className="message-label">You</div>
      {msg.attachmentNames?.length > 0 && (
        <div className="message-attachments">
          {msg.attachmentNames.map((name, i) => (
            <span className="attachment-tag" key={i}>
              <svg className="attachment-tag-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              {escapeHtml(name)}
            </span>
          ))}
        </div>
      )}
      <div className="message-bubble">{escapeHtml(msg.content)}</div>
    </div>
  );
}

function AgentMessage({ msg, isStreaming }) {
  const [thinkingOpen, setThinkingOpen] = React.useState(false);

  return (
    <div className={`message agent${isStreaming ? ' streaming' : ''}`}>
      <div className="message-label">Agent</div>
      <div className="message-bubble agent-text">
        {msg.content || (isStreaming ? '' : '[空回复]')}
      </div>
      {msg.thinking && (
        <div className={`thinking-block${thinkingOpen ? '' : ' collapsed'}`}>
          <div className="thinking-header" onClick={() => setThinkingOpen(!thinkingOpen)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
            <span>思考过程</span>
          </div>
          <div className="thinking-content">{msg.thinking}</div>
        </div>
      )}
    </div>
  );
}
