import React from 'react';

export default function AttachmentBar({ attachments, onRemove, onClear, formatSize }) {
  if (attachments.length === 0) return null;

  return (
    <div className="attachment-bar">
      <div className="attachment-bar-header">
        <span className="attachment-bar-title">
          已选择 <span className="attachment-count">{attachments.length}</span> 个文件
        </span>
        <button className="btn btn-sm btn-text" onClick={onClear}>清空</button>
      </div>
      <div className="attachment-list">
        {attachments.map((file, i) => (
          <div className="attachment-item" key={`${file.name}-${i}`}>
            <span className="attachment-item-name" title={file.name}>{file.name}</span>
            <span className="attachment-item-size">{formatSize(file.size)}</span>
            <button className="attachment-item-remove" onClick={() => onRemove(i)} title="移除">
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
