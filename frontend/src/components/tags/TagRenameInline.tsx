import React, { useState } from 'react';
import { TextField, IconButton, Box } from '@mui/material';
import { Check, Close } from '@mui/icons-material';

interface TagRenameInlineProps {
  currentName: string;
  onSave: (newName: string) => Promise<void>;
  onCancel: () => void;
}

const TagRenameInline: React.FC<TagRenameInlineProps> = ({ currentName, onSave, onCancel }) => {
  const [name, setName] = useState(currentName);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim() || name.trim() === currentName) {
      onCancel();
      return;
    }
    setSaving(true);
    try {
      await onSave(name.trim());
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1 }}>
      <TextField
        size="small"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSave();
          if (e.key === 'Escape') onCancel();
        }}
        autoFocus
        disabled={saving}
        sx={{ flex: 1 }}
      />
      <IconButton size="small" onClick={handleSave} disabled={saving}>
        <Check fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={onCancel} disabled={saving}>
        <Close fontSize="small" />
      </IconButton>
    </Box>
  );
};

export default TagRenameInline;
