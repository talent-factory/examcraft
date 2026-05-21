import React, { useRef, useState, useMemo } from 'react';
import { flushSync } from 'react-dom';
import {
  Autocomplete,
  TextField,
  Chip,
  CircularProgress,
  Box,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  createFilterOptions,
} from '@mui/material';
import PublicIcon from '@mui/icons-material/Public';
import CheckIcon from '@mui/icons-material/Check';
import LocalOfferOutlinedIcon from '@mui/icons-material/LocalOfferOutlined';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tagsApi, type Tag, type TagValue, isPendingTag } from '../../api/tagsApi';

interface TagAutocompleteProps {
  value: TagValue[];
  onChange: (tags: TagValue[]) => void;
  disabled?: boolean;
  label?: string;
  deferCreation?: boolean;
}

interface TagCreateOption {
  inputValue: string;
  name: string;
}

type TagOption = Tag | TagCreateOption;

const filter = createFilterOptions<TagOption>();
const isCreateOption = (o: TagOption): o is TagCreateOption => 'inputValue' in o;

const TagAutocomplete: React.FC<TagAutocompleteProps> = ({
  value,
  onChange,
  disabled = false,
  label = 'Tags',
  deferCreation = false,
}) => {
  const queryClient = useQueryClient();
  const [inputValue, setInputValue] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [archivedWarning, setArchivedWarning] = useState<string | null>(null);
  const [createError, setCreateError] = useState(false);

  const valueRef = useRef(value);
  valueRef.current = value;

  const inputElRef = useRef<HTMLInputElement | null>(null);
  const pendingCreateRef = useRef(false);

  const { data: allTagsWithArchived = [], isLoading } = useQuery({
    queryKey: ['tags', 'with-archived'],
    queryFn: () => tagsApi.listTags(true),
    staleTime: 60_000,
  });
  const allTags = useMemo(() =>
    [...allTagsWithArchived.filter((t) => !t.is_archived)].sort((a, b) => {
      if (a.scope === b.scope) return a.name.localeCompare(b.name);
      return a.scope === 'global' ? 1 : -1;
    }),
    [allTagsWithArchived],
  );

  const createMutation = useMutation({
    mutationFn: (name: string) => tagsApi.createTag(name),
    onSuccess: (newTag) => {
      pendingCreateRef.current = false;
      if (newTag.is_archived) {
        setArchivedWarning(newTag.name);
        return;
      }
      queryClient.invalidateQueries({ queryKey: ['tags'] }); // trifft auch ['tags', 'with-archived']
      onChange([...valueRef.current, newTag]);
      setTimeout(() => inputElRef.current?.focus(), 0);
    },
    onError: (err) => {
      pendingCreateRef.current = false;
      console.error('Tag konnte nicht erstellt werden.', err);
      setCreateError(true);
    },
  });

  const tryCreate = (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return;
    if (value.some((v) => v.name.toLowerCase() === trimmed.toLowerCase())) return;
    createMutation.mutate(trimmed);
  };

  const removeTag = (tag: TagValue) => {
    if (isPendingTag(tag)) {
      onChange(value.filter((v) => isPendingTag(v) ? v.name !== tag.name : true));
    } else {
      onChange(value.filter((v) => isPendingTag(v) ? true : (v as Tag).id !== tag.id));
    }
  };

  const handleCreate = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    if (value.some((v) => v.name.toLowerCase() === trimmed.toLowerCase())) return;

    // Archiviert-Check: sofortiges Feedback ohne API-Call
    const archivedMatch = allTagsWithArchived.find(
      (t) => t.is_archived && t.name.toLowerCase() === trimmed.toLowerCase()
    );
    if (archivedMatch) {
      setArchivedWarning(archivedMatch.name);
      setDropdownOpen(false);
      return;
    }

    if (deferCreation) {
      onChange([...valueRef.current, { __pending: true as const, name: trimmed }]);
      flushSync(() => setInputValue(''));
      inputElRef.current?.focus();
      return;
    }

    pendingCreateRef.current = true;
    tryCreate(trimmed);
    flushSync(() => setInputValue(''));
    inputElRef.current?.focus();
  };

  const tagChipStyle = {
    bgcolor: (theme: any) => `${theme.palette.secondary.light}22`,
    color: 'secondary.dark',
    border: '1px solid',
    borderColor: (theme: any) => `${theme.palette.secondary.light}66`,
    '& .MuiChip-icon': { color: 'secondary.light', fontSize: 14 },
    '& .MuiChip-deleteIcon': {
      color: (theme: any) => `${theme.palette.secondary.light}99`,
      '&:hover': { color: 'secondary.main' },
    },
  };

  return (
    <Box>
      <Autocomplete<TagOption, false, false, false>
        value={null}
        inputValue={inputValue}
        open={dropdownOpen}
        onOpen={() => setDropdownOpen(true)}
        onClose={() => setDropdownOpen(false)}
        noOptionsText={
          inputValue.trim() &&
          value.some((v) => v.name.toLowerCase() === inputValue.trim().toLowerCase())
            ? `"${inputValue.trim()}" ist bereits ausgewählt`
            : 'Keine Optionen'
        }
        componentsProps={{
          paper: {
            sx: {
              border: '1px solid',
              borderColor: 'grey.300',
              boxShadow: 4,
            },
          },
        }}
        onInputChange={(_, v, reason) => {
          if (reason === 'reset') {
            if (createError) setCreateError(false);
            return;
          }
          setInputValue(v);
          if (archivedWarning) setArchivedWarning(null);
          if (createError) setCreateError(false);
        }}
        disabled={disabled}
        loading={isLoading}
        autoHighlight
        blurOnSelect={false}
        options={allTags as TagOption[]}
        groupBy={(option) =>
          !isCreateOption(option) && (option as Tag).scope === 'global'
            ? 'Vorgegebene Tags'
            : 'Tags dieser Institution'
        }
        renderGroup={(params) => (
          <React.Fragment key={params.key}>
            <Box
              component="li"
              aria-hidden
              sx={{
                position: 'sticky',
                top: -8,
                zIndex: 10,
                listStyle: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                px: 1.5,
                py: 0.75,
                fontSize: '0.65rem',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: params.group === 'Tags dieser Institution' ? '#1565c0' : '#757575',
                bgcolor: params.group === 'Tags dieser Institution' ? '#e8f4ff' : '#f5f5f5',
                borderBottom: '1px solid',
                borderColor: 'divider',
              }}
            >
              {params.group === 'Vorgegebene Tags' && (
                <PublicIcon sx={{ fontSize: 12 }} />
              )}
              {params.group}
            </Box>
            {params.children}
          </React.Fragment>
        )}
        getOptionLabel={(option) =>
          isCreateOption(option) ? option.inputValue : option.name
        }
        filterOptions={(options, params) => {
          const filtered = filter(options, params);
          const trimmed = params.inputValue.trim();
          const trimmedLower = trimmed.toLowerCase();
          const alreadyExists =
            allTags.some((o) => o.name.toLowerCase() === trimmedLower) ||
            value.some((v) => v.name.toLowerCase() === trimmedLower);
          if (trimmedLower && !alreadyExists) {
            return [{ inputValue: trimmed, name: `"${trimmed}" erstellen` }, ...filtered];
          }
          return filtered;
        }}
        onChange={(_, selected) => {
          if (!selected) return;
          if (isCreateOption(selected)) {
            handleCreate(selected.inputValue);
          } else {
            const tag = selected as Tag;
            if (!valueRef.current.some((v) => !isPendingTag(v) && (v as Tag).id === tag.id)) {
              onChange([...valueRef.current, tag]);
            }
            flushSync(() => setInputValue(''));
          }
        }}
        isOptionEqualToValue={(option, val) => {
          if (isCreateOption(option) || isCreateOption(val)) return false;
          return (option as Tag).id === (val as Tag).id;
        }}
        renderOption={(props, option) => {
          const isAssigned =
            !isCreateOption(option) &&
            value.some((v) =>
              isPendingTag(v)
                ? v.name === (option as Tag).name
                : (v as Tag).id === (option as Tag).id
            );
          return (
            <ListItem
              {...props}
              key={
                isCreateOption(option)
                  ? `create-${option.inputValue}`
                  : (option as Tag).id
              }
              dense
            >
              <ListItemIcon sx={{ minWidth: 32 }}>
                {isAssigned && <CheckIcon fontSize="small" color="secondary" />}
              </ListItemIcon>
              <ListItemText
                primary={isCreateOption(option) ? option.name : (option as Tag).name}
                sx={{ color: isAssigned ? 'text.secondary' : 'text.primary' }}
              />
            </ListItem>
          );
        }}
        renderInput={(params) => {
          const muiKeyDown = (
            params.inputProps as { onKeyDown?: React.KeyboardEventHandler }
          ).onKeyDown;

          return (
            <TextField
              {...params}
              label={label}
              size="small"
              inputRef={(el) => {
                inputElRef.current = el;
              }}
              inputProps={{
                ...params.inputProps,
                onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => {
                  if (e.key === 'Enter' && inputValue.trim()) {
                    const trimmedLower = inputValue.trim().toLowerCase();
                    const alreadyExists =
                      allTags.some((t) => t.name.toLowerCase() === trimmedLower) ||
                      value.some((v) => v.name.toLowerCase() === trimmedLower);
                    if (!alreadyExists) {
                      e.preventDefault();
                      e.stopPropagation();
                      handleCreate(inputValue.trim());
                      return;
                    }
                  }
                  muiKeyDown?.(e);
                },
              }}
              InputProps={{
                ...params.InputProps,
                endAdornment: (
                  <>
                    {(isLoading || createMutation.isPending) && (
                      <CircularProgress size={16} />
                    )}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          );
        }}
      />

      {/* Archiviert-Warnung */}
      {archivedWarning && (
        <Box
          sx={{
            mt: 1,
            p: 1.5,
            bgcolor: 'error.50',
            border: '1px solid',
            borderColor: 'error.200',
            borderRadius: 1,
          }}
        >
          <Typography variant="body2" color="error.dark">
            🚫 Tag &ldquo;{archivedWarning}&rdquo; ist archiviert und kann nicht verwendet werden.
          </Typography>
        </Box>
      )}

      {/* Erstellungs-Fehler */}
      {createError && (
        <Box sx={{ mt: 1, p: 1.5, bgcolor: 'error.50', border: '1px solid', borderColor: 'error.200', borderRadius: 1 }}>
          <Typography variant="body2" color="error.dark">
            Tag konnte nicht erstellt werden. Bitte versuche es erneut.
          </Typography>
        </Box>
      )}

      {value.length > 0 && (
        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {[...value]
            .sort((a, b) => {
              if (isPendingTag(a) && isPendingTag(b)) return a.name.localeCompare(b.name);
              if (isPendingTag(a)) return 1;
              if (isPendingTag(b)) return -1;
              if (a.scope === b.scope) return a.name.localeCompare(b.name);
              return a.scope === 'global' ? 1 : -1;
            })
            .map((tag) => {
              if (isPendingTag(tag)) {
                return (
                  <Chip
                    key={`pending-${tag.name}`}
                    icon={<LocalOfferOutlinedIcon />}
                    label={tag.name}
                    size="small"
                    onDelete={disabled ? undefined : () => removeTag(tag)}
                    sx={{
                      ...tagChipStyle,
                      borderStyle: 'dashed',
                      fontStyle: 'italic',
                    }}
                  />
                );
              }
              return (
                <Chip
                  key={tag.id}
                  icon={tag.scope === 'global' ? <PublicIcon /> : <LocalOfferOutlinedIcon />}
                  label={tag.name}
                  size="small"
                  onDelete={disabled ? undefined : () => removeTag(tag)}
                  sx={tag.scope === 'global' ? {
                    ...tagChipStyle,
                    bgcolor: (theme: any) => `${theme.palette.primary.light}22`,
                    color: 'primary.dark',
                    borderColor: (theme: any) => `${theme.palette.primary.light}66`,
                    '& .MuiChip-icon': { color: 'primary.light', fontSize: 14 },
                    '& .MuiChip-deleteIcon': {
                      color: (theme: any) => `${theme.palette.primary.light}99`,
                      '&:hover': { color: 'primary.main' },
                    },
                  } : tagChipStyle}
                />
              );
            })}
        </Box>
      )}
    </Box>
  );
};

export default TagAutocomplete;
