import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Box } from '@mui/material';

interface MarkdownRendererProps {
  content: string;
  variant?: 'default' | 'compact';
}

/**
 * Wiederverwendbare Markdown-Rendering-Komponente mit Syntax-Highlighting
 *
 * Features:
 * - GitHub Flavored Markdown (GFM)
 * - Syntax-Highlighting für Code-Blöcke
 * - Responsive Design
 * - Konsistentes Styling
 */
const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  variant = 'default'
}) => {
  return (
    <Box
      sx={{
        '& p': {
          mt: variant === 'compact' ? 0 : 1,
          mb: variant === 'compact' ? 1 : 2
        },
        '& h1, & h2, & h3, & h4, & h5, & h6': {
          mt: 2,
          mb: 1,
          fontWeight: 600
        },
        '& h1': { fontSize: '2rem' },
        '& h2': { fontSize: '1.5rem' },
        '& h3': { fontSize: '1.25rem' },
        '& ul': {
          pl: 3,
          my: 1,
          listStyleType: 'disc',
          listStylePosition: 'outside'
        },
        '& ol': {
          pl: 3,
          my: 1,
          listStyleType: 'decimal',
          listStylePosition: 'outside'
        },
        '& li': {
          mb: 0.5,
          display: 'list-item'
        },
        '& blockquote': {
          borderLeft: '4px solid',
          borderColor: 'primary.main',
          pl: 2,
          ml: 0,
          my: 2,
          fontStyle: 'italic',
          color: 'text.secondary'
        },
        '& table': {
          width: '100%',
          borderCollapse: 'collapse',
          my: 2
        },
        '& th, & td': {
          border: '1px solid',
          borderColor: 'divider',
          p: 1,
          textAlign: 'left'
        },
        '& th': {
          bgcolor: 'grey.100',
          fontWeight: 600
        },
        '& a': {
          color: 'primary.main',
          textDecoration: 'underline',
          '&:hover': {
            textDecoration: 'none'
          }
        },
        '& img': {
          maxWidth: '100%',
          height: 'auto',
          borderRadius: 1
        },
        '& hr': {
          my: 3,
          border: 'none',
          borderTop: '1px solid',
          borderColor: 'divider'
        },
        // Inline Code
        '& code': {
          bgcolor: 'grey.100',
          color: 'error.dark',
          px: 0.5,
          py: 0.25,
          borderRadius: 0.5,
          fontSize: '0.875rem',
          fontFamily: 'monospace'
        },
        // Code Blocks (werden von SyntaxHighlighter überschrieben)
        '& pre': {
          my: 2,
          borderRadius: 1,
          overflow: 'auto'
        },
        '& pre code': {
          bgcolor: 'transparent',
          color: 'inherit',
          p: 0
        }
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code(props) {
            const { className, children } = props;
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';

            if (match && language) {
              return (
                <SyntaxHighlighter
                  style={vscDarkPlus as any}
                  language={language}
                  PreTag="div"
                  customStyle={{
                    margin: 0,
                    borderRadius: '4px',
                    fontSize: '0.875rem'
                  }}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              );
            }

            return (
              <code className={className}>
                {children}
              </code>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </Box>
  );
};

export default MarkdownRenderer;
