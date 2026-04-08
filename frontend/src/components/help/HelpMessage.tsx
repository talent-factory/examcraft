import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { SmartToy, Person } from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import HelpFeedback from './HelpFeedback';

interface HelpMessageProps {
  role: 'user' | 'assistant';
  content: string;
  confidence?: number;
  sources?: Array<{ file: string; section: string }>;
  question?: string;
  route: string;
}

const HelpMessage: React.FC<HelpMessageProps> = ({
  role,
  content,
  confidence,
  sources,
  question,
  route,
}) => {
  const isUser = role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
          flexDirection: isUser ? 'row-reverse' : 'row',
          maxWidth: '90%',
        }}
      >
        {isUser ? (
          <Person fontSize="small" color="action" />
        ) : (
          <SmartToy fontSize="small" color="primary" />
        )}
        <Box
          sx={{
            backgroundColor: isUser ? 'primary.light' : 'grey.100',
            borderRadius: 2,
            p: 1.5,
            maxWidth: '100%',
          }}
        >
          {isUser ? (
            <Typography variant="body2">{content}</Typography>
          ) : (
            <Box sx={{ '& p': { m: 0, fontSize: '0.875rem' }, '& ul, & ol': { pl: 2, my: 0.5, fontSize: '0.875rem' }, '& strong': { fontWeight: 600 } }}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </Box>
          )}
          {sources && sources.length > 0 && (
            <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
              {sources.map((s, i) => (
                <Chip key={i} label={s.section} size="small" variant="outlined" />
              ))}
            </Box>
          )}
        </Box>
      </Box>

      {!isUser && question && (
        <HelpFeedback
          question={question}
          answer={content}
          confidence={confidence ?? 0}
          route={route}
        />
      )}
    </Box>
  );
};

export default HelpMessage;
