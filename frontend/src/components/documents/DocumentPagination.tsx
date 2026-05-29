import React from 'react';
import Box from '@mui/material/Box';
import Pagination from '@mui/material/Pagination';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import { useTranslation } from 'react-i18next';

const PAGE_SIZES = [12, 24, 48, 96];

interface DocumentPaginationProps {
  page: number;
  totalPages: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (s: number) => void;
}

const DocumentPagination: React.FC<DocumentPaginationProps> = ({
  page,
  totalPages,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}) => {
  const { t } = useTranslation();

  if (total === 0) return null;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 2,
      }}
    >
      <Pagination
        count={totalPages}
        page={page}
        onChange={(_, p) => onPageChange(p)}
        color="primary"
        shape="rounded"
      />
      <FormControl size="small">
        <InputLabel id="page-size-label">
          {t('components.documentLibrary.pagination.pageSizeLabel', 'Pro Seite')}
        </InputLabel>
        <Select
          labelId="page-size-label"
          value={pageSize}
          label={t('components.documentLibrary.pagination.pageSizeLabel', 'Pro Seite')}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {PAGE_SIZES.map((size) => (
            <MenuItem key={size} value={size}>
              {size}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
};

export default DocumentPagination;
