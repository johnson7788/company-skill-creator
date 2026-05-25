import { useState, useCallback, useRef } from 'react';

const UPLOAD_ENDPOINT = '/api/upload';

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function useAttachments(sessionId) {
  const [attachments, setAttachments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const sessionRef = useRef(sessionId);
  sessionRef.current = sessionId;

  const addFiles = useCallback(async (files) => {
    const newFiles = Array.from(files).filter(
      f => !attachments.some(a => a.name === f.name && a.size === f.size)
    );
    if (newFiles.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('sessionId', sessionRef.current);
      newFiles.forEach(f => formData.append('files', f));

      const res = await fetch(UPLOAD_ENDPOINT, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `上传失败: HTTP ${res.status}`);
      }

      const data = await res.json();
      // Store metadata from server response (name, path, size, type)
      const uploaded = data.files.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type,
        path: f.path,
      }));

      setAttachments(prev => [...prev, ...uploaded]);
    } catch (err) {
      console.error('文件上传失败:', err);
    } finally {
      setIsUploading(false);
    }
  }, [attachments]);

  const removeAttachment = useCallback((index) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments([]);
  }, []);

  const popAttachments = useCallback(() => {
    const current = [...attachments];
    setAttachments([]);
    return current;
  }, [attachments]);

  return {
    attachments,
    isUploading,
    addFiles,
    removeAttachment,
    clearAttachments,
    popAttachments,
    formatFileSize,
  };
}
