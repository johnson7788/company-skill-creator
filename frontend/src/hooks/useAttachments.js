import { useState, useCallback } from 'react';

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function guessMimeType(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const map = { md: 'text/markdown', txt: 'text/plain', py: 'text/x-python',
    js: 'text/javascript', ts: 'text/typescript', yaml: 'text/yaml', yml: 'text/yaml',
    json: 'application/json', xml: 'text/xml', html: 'text/html', css: 'text/css',
    java: 'text/x-java', go: 'text/x-go', rs: 'text/x-rust', sh: 'text/x-shellscript',
    bash: 'text/x-shellscript', toml: 'text/toml', ini: 'text/plain', cfg: 'text/plain' };
  return map[ext] || 'text/plain';
}

export default function useAttachments() {
  const [attachments, setAttachments] = useState([]);

  const addFiles = useCallback(async (files) => {
    const results = [];
    for (const file of files) {
      if (attachments.some(a => a.name === file.name && a.size === file.size)) continue;
      try {
        const content = await file.text();
        results.push({
          name: file.name,
          size: file.size,
          type: file.type || guessMimeType(file.name),
          content,
          encoding: 'utf-8',
        });
      } catch {
        // skip unreadable files
      }
    }
    if (results.length > 0) {
      setAttachments(prev => [...prev, ...results]);
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
    addFiles,
    removeAttachment,
    clearAttachments,
    popAttachments,
    formatFileSize,
  };
}
