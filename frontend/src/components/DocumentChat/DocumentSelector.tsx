import React, { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { 
  Box, 
  Button, 
  Checkbox, 
  FormControlLabel, 
  Typography, 
  Card,
  CardContent,
  TextField
} from '@mui/material';

interface Document {
  id: number;
  title: string;
  filename: string;
  status: string;
}

interface DocumentSelectorProps {
  documents: Document[];
  onStartChat: (documentIds: number[], title: string) => void;
}

export const DocumentSelector: React.FC<DocumentSelectorProps> = ({
  documents,
  onStartChat,
}) => {
  const [selectedDocs, setSelectedDocs] = useState<Set<number>>(new Set());
  const [chatTitle, setChatTitle] = useState('');

  const toggleDocument = (docId: number) => {
    setSelectedDocs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const handleStartChat = () => {
    if (selectedDocs.size > 0) {
      const title = chatTitle.trim() || `Chat mit ${selectedDocs.size} Dokument${selectedDocs.size > 1 ? 'en' : ''}`;
      onStartChat(Array.from(selectedDocs), title);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h6">Dokumente für Chat auswählen</Typography>
      
      <TextField
        fullWidth
        label="Chat-Titel (optional)"
        value={chatTitle}
        onChange={(e) => setChatTitle(e.target.value)}
        placeholder="z.B. Algorithmen Diskussion"
        size="small"
      />

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: '400px', overflowY: 'auto' }}>
        {documents.map(doc => (
          <Card 
            key={doc.id}
            variant="outlined"
            sx={{ 
              cursor: 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              bgcolor: selectedDocs.has(doc.id) ? 'action.selected' : 'background.paper'
            }}
            onClick={() => toggleDocument(doc.id)}
          >
            <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={selectedDocs.has(doc.id)}
                    onChange={() => toggleDocument(doc.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                }
                label={
                  <Box>
                    <Typography variant="body1" fontWeight="medium">
                      {doc.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {doc.filename}
                    </Typography>
                  </Box>
                }
              />
            </CardContent>
          </Card>
        ))}
      </Box>

      <Button
        onClick={handleStartChat}
        disabled={selectedDocs.size === 0}
        variant="contained"
        fullWidth
        startIcon={<MessageSquare size={20} />}
      >
        Chat mit {selectedDocs.size} Dokument{selectedDocs.size !== 1 ? 'en' : ''} starten
      </Button>
    </Box>
  );
};

