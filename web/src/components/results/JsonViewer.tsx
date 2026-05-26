// ============================================================
// JsonViewer — Custom Monospace JSON Highlight Component
// ============================================================

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Copy, Check } from 'lucide-react';
import './JsonViewer.css';

interface JsonViewerProps {
  data: Record<string, unknown>;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  // Stringify the data
  const jsonString = useMemo(() => {
    return JSON.stringify(data, null, 2);
  }, [data]);

  // Syntax highlight function returning HTML safely
  const highlightedHtml = useMemo(() => {
    // Escaping HTML characters first
    let escaped = jsonString
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Syntax highlight regex
    return escaped.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        let cls = 'json-viewer__number';
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'json-viewer__key';
          } else {
            cls = 'json-viewer__string';
          }
        } else if (/true|false/.test(match)) {
          cls = 'json-viewer__boolean';
        } else if (/null/.test(match)) {
          cls = 'json-viewer__null';
        }

        if (cls === 'json-viewer__key') {
          return `<span class="${cls}">${match.replace(/:$/, '')}</span><span class="json-viewer__punctuation">:</span>`;
        }
        return `<span class="${cls}">${match}</span>`;
      }
    );
  }, [jsonString]);

  // Count lines for line numbering
  const lineNumbers = useMemo(() => {
    const lines = jsonString.split('\n');
    return Array.from({ length: lines.length }, (_, i) => i + 1);
  }, [jsonString]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="json-viewer"
    >
      <div className="json-viewer__header">
        <span className="json-viewer__title">Raw Response</span>
        <button
          type="button"
          onClick={handleCopy}
          className={`json-viewer__copy-btn ${copied ? 'json-viewer__copy-btn--success' : ''}`}
          aria-label={copied ? 'Copied' : 'Copy JSON to clipboard'}
        >
          {copied ? (
            <>
              <Check size={14} />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy size={14} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="json-viewer__content">
        <div className="json-viewer__line-numbers">
          {lineNumbers.map((num) => (
            <span key={num}>{num}</span>
          ))}
        </div>
        <code
          className="json-viewer__code"
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </div>
    </motion.div>
  );
};
