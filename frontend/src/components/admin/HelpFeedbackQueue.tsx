import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Select, MenuItem, FormControl,
  InputLabel, Button,
} from '@mui/material';
import { useAuth } from '../../contexts/AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface FeedbackItem {
  id: number;
  question: string;
  answer: string | null;
  confidence: number | null;
  rating: string | null;
  user_role: string | null;
  status: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success'> = {
  offen: 'warning',
  in_bearbeitung: 'default',
  dokumentiert: 'success',
};

const HelpFeedbackQueue: React.FC = () => {
  const { accessToken } = useAuth();
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchQueue = async () => {
    if (!accessToken) return;
    setLoading(true);
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/help/admin/feedback-queue?${params}`,
        { headers: { Authorization: `Bearer ${accessToken}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setItems(data.items);
        setTotal(data.total);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, statusFilter]);

  const updateStatus = async (id: number, newStatus: string) => {
    if (!accessToken) return;
    await fetch(`${API_BASE_URL}/api/v1/help/admin/feedback/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ status: newStatus }),
    });
    fetchQueue();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Hilfe-Feedback Queue ({total})</Typography>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="">Alle</MenuItem>
            <MenuItem value="offen">Offen</MenuItem>
            <MenuItem value="in_bearbeitung">In Bearbeitung</MenuItem>
            <MenuItem value="dokumentiert">Dokumentiert</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Frage</TableCell>
              <TableCell>Rolle</TableCell>
              <TableCell>Rating</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Aktion</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id}>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {item.question}
                </TableCell>
                <TableCell>{item.user_role || '—'}</TableCell>
                <TableCell>
                  {item.rating ? (
                    <Chip
                      label={item.rating === 'up' ? '👍' : '👎'}
                      size="small"
                      color={item.rating === 'up' ? 'success' : 'error'}
                    />
                  ) : '—'}
                </TableCell>
                <TableCell>
                  <Chip
                    label={item.status}
                    size="small"
                    color={STATUS_COLORS[item.status] ?? 'default'}
                  />
                </TableCell>
                <TableCell>
                  {item.status === 'offen' && (
                    <Button size="small" onClick={() => updateStatus(item.id, 'in_bearbeitung')}>
                      Bearbeiten
                    </Button>
                  )}
                  {item.status === 'in_bearbeitung' && (
                    <Button size="small" color="success" onClick={() => updateStatus(item.id, 'dokumentiert')}>
                      Dokumentiert
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {items.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={5} align="center">
                  <Typography color="text.secondary">Keine Einträge</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default HelpFeedbackQueue;
