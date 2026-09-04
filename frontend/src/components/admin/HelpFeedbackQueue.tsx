import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Paper, Chip, Select, MenuItem, FormControl,
  InputLabel, Button, Tabs, Tab, TextField, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert,
} from '@mui/material';
import { CheckCircle, Cancel, Warning } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { translateError } from '../../errors';

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

interface ClusterItem {
  id: number;
  topic_label: string;
  positive_count: number;
  negative_count: number;
  total_count: number;
  docs_gap: boolean;
}

interface FaqCandidate {
  id: number;
  question_text: string;
  answer_de: string;
  answer_en: string;
  faq_status: string;
  cluster_id: number | null;
  hit_count: number;
}

const STATUS_COLORS: Record<string, 'default' | 'warning' | 'success'> = {
  offen: 'warning',
  in_bearbeitung: 'default',
  dokumentiert: 'success',
};

const HelpFeedbackQueue: React.FC = () => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [tabIndex, setTabIndex] = useState(0);

  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');

  const [clusters, setClusters] = useState<ClusterItem[]>([]);

  const [candidates, setCandidates] = useState<FaqCandidate[]>([]);
  const [editDialog, setEditDialog] = useState<FaqCandidate | null>(null);
  const [editAnswerDe, setEditAnswerDe] = useState('');
  const [editAnswerEn, setEditAnswerEn] = useState('');
  const [error, setError] = useState<string | null>(null);

  const headers = { Authorization: `Bearer ${accessToken}` };

  const fetchQueue = async () => {
    if (!accessToken) return;
    setError(null);
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/feedback-queue?${params}`, { headers });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to load feedback:', res.status);
        setError(t('admin.helpFeedbackQueue.errorLoadFeedback'));
        return;
      }
      const data = await res.json();
      setItems(data.items);
      setTotal(data.total);
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  const fetchClusters = async () => {
    if (!accessToken) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/clusters`, { headers });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to load clusters:', res.status);
        setError(t('admin.helpFeedbackQueue.errorLoadClusters'));
        return;
      }
      const data = await res.json();
      setClusters(data.items);
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  const fetchCandidates = async () => {
    if (!accessToken) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/faq-candidates`, { headers });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to load FAQ candidates:', res.status);
        setError(t('admin.helpFeedbackQueue.errorLoadCandidates'));
        return;
      }
      const data = await res.json();
      setCandidates(data.items);
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  useEffect(() => {
    if (tabIndex === 0) fetchQueue();
    if (tabIndex === 1) fetchCandidates();
    if (tabIndex === 2) fetchClusters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, tabIndex, statusFilter]);

  const updateStatus = async (id: number, newStatus: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/feedback/${id}`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to update status:', res.status);
        setError(t('admin.helpFeedbackQueue.errorStatusUpdate'));
        return;
      }
      setError(null);
      fetchQueue();
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  const approveFaq = async (id: number, answerDe?: string, answerEn?: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/faq-candidates/${id}/approve`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ answer_de: answerDe || null, answer_en: answerEn || null }),
      });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to approve FAQ:', res.status);
        setError(t('admin.helpFeedbackQueue.errorFaqApprove'));
        return;
      }
      setError(null);
      setEditDialog(null);
      fetchCandidates();
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  const rejectFaq = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/faq-candidates/${id}/reject`, {
        method: 'POST',
        headers: { ...headers },
      });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to reject FAQ:', res.status);
        setError(t('admin.helpFeedbackQueue.errorFaqReject'));
        return;
      }
      setError(null);
      fetchCandidates();
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  const markDocsGap = async (clusterId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/help/admin/clusters/${clusterId}/mark-docs-gap`, {
        method: 'POST',
        headers: { ...headers },
      });
      if (!res.ok) {
        console.error('[HelpFeedbackQueue] Failed to mark docs gap:', res.status);
        setError(t('admin.helpFeedbackQueue.errorMarkDocsGap'));
        return;
      }
      setError(null);
      fetchClusters();
    } catch (err) { setError(translateError(err, t, 'errors.network')); }
  };

  return (
    <Box>
      <Tabs value={tabIndex} onChange={(_, v) => setTabIndex(v)} sx={{ mb: 2 }}>
        <Tab label={t('admin.helpFeedbackQueue.tabFeedback', { count: total })} />
        <Tab label={t('admin.helpFeedbackQueue.tabCandidates', { count: candidates.length })} />
        <Tab label={t('admin.helpFeedbackQueue.tabClusters')} />
      </Tabs>

      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}

      {/* Tab 0: Feedback Queue */}
      {tabIndex === 0 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>{t('admin.helpFeedbackQueue.status')}</InputLabel>
              <Select value={statusFilter} label={t('admin.helpFeedbackQueue.status')} onChange={(e) => setStatusFilter(e.target.value)}>
                <MenuItem value="">{t('admin.helpFeedbackQueue.statusAll')}</MenuItem>
                <MenuItem value="offen">{t('admin.helpFeedbackQueue.statusOpen')}</MenuItem>
                <MenuItem value="in_bearbeitung">{t('admin.helpFeedbackQueue.statusInProgress')}</MenuItem>
                <MenuItem value="dokumentiert">{t('admin.helpFeedbackQueue.statusDocumented')}</MenuItem>
              </Select>
            </FormControl>
          </Box>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('admin.helpFeedbackQueue.colQuestion')}</TableCell>
                  <TableCell>{t('admin.helpFeedbackQueue.colRole')}</TableCell>
                  <TableCell>{t('admin.helpFeedbackQueue.colRating')}</TableCell>
                  <TableCell>{t('admin.helpFeedbackQueue.colStatus')}</TableCell>
                  <TableCell>{t('admin.helpFeedbackQueue.colAction')}</TableCell>
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
                        <Chip label={item.rating === 'up' ? '👍' : '👎'} size="small" color={item.rating === 'up' ? 'success' : 'error'} />
                      ) : '—'}
                    </TableCell>
                    <TableCell>
                      <Chip label={item.status} size="small" color={STATUS_COLORS[item.status] ?? 'default'} />
                    </TableCell>
                    <TableCell>
                      {item.status === 'offen' && (
                        <Button size="small" onClick={() => updateStatus(item.id, 'in_bearbeitung')}>{t('admin.helpFeedbackQueue.actionEdit')}</Button>
                      )}
                      {item.status === 'in_bearbeitung' && (
                        <Button size="small" color="success" onClick={() => updateStatus(item.id, 'dokumentiert')}>{t('admin.helpFeedbackQueue.actionDocumented')}</Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">{t('admin.helpFeedbackQueue.emptyFeedback')}</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Tab 1: FAQ Candidates */}
      {tabIndex === 1 && (
        <Box>
          {candidates.length === 0 ? (
            <Alert severity="info">{t('admin.helpFeedbackQueue.emptyCandidates')}</Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('admin.helpFeedbackQueue.colQuestion')}</TableCell>
                    <TableCell>{t('admin.helpFeedbackQueue.colAnswerDe')}</TableCell>
                    <TableCell>{t('admin.helpFeedbackQueue.colHits')}</TableCell>
                    <TableCell>{t('admin.helpFeedbackQueue.colActions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {candidates.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell sx={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.question_text}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.answer_de}
                      </TableCell>
                      <TableCell>{c.hit_count}</TableCell>
                      <TableCell>
                        <Button size="small" color="success" startIcon={<CheckCircle />} onClick={() => approveFaq(c.id)} sx={{ mr: 1 }}>
                          {t('admin.helpFeedbackQueue.actionApprove')}
                        </Button>
                        <Button size="small" color="warning" onClick={() => { setEditDialog(c); setEditAnswerDe(c.answer_de); setEditAnswerEn(c.answer_en); }}>
                          {t('admin.helpFeedbackQueue.actionEdit')}
                        </Button>
                        <Button size="small" color="error" startIcon={<Cancel />} onClick={() => rejectFaq(c.id)}>
                          {t('admin.helpFeedbackQueue.actionReject')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          <Dialog open={!!editDialog} onClose={() => setEditDialog(null)} maxWidth="md" fullWidth>
            <DialogTitle>{t('admin.helpFeedbackQueue.dialogEditTitle')}</DialogTitle>
            <DialogContent>
              <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>{t('admin.helpFeedbackQueue.colQuestion')}</Typography>
              <Typography variant="body2" color="text.secondary">{editDialog?.question_text}</Typography>
              <TextField fullWidth multiline rows={4} label={t('admin.helpFeedbackQueue.fieldAnswerDe')} value={editAnswerDe} onChange={(e) => setEditAnswerDe(e.target.value)} sx={{ mt: 2 }} />
              <TextField fullWidth multiline rows={4} label={t('admin.helpFeedbackQueue.fieldAnswerEn')} value={editAnswerEn} onChange={(e) => setEditAnswerEn(e.target.value)} sx={{ mt: 2 }} />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setEditDialog(null)}>{t('admin.helpFeedbackQueue.actionCancel')}</Button>
              <Button variant="contained" color="success" onClick={() => editDialog && approveFaq(editDialog.id, editAnswerDe, editAnswerEn)}>
                {t('admin.helpFeedbackQueue.actionApprove')}
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      )}

      {/* Tab 2: Clusters & Docs Gaps */}
      {tabIndex === 2 && (
        <Box>
          {clusters.length === 0 ? (
            <Alert severity="info">{t('admin.helpFeedbackQueue.emptyClusters')}</Alert>
          ) : (
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('admin.helpFeedbackQueue.colTopic')}</TableCell>
                    <TableCell align="center">👍</TableCell>
                    <TableCell align="center">👎</TableCell>
                    <TableCell align="center">{t('admin.helpFeedbackQueue.colTotal')}</TableCell>
                    <TableCell>{t('admin.helpFeedbackQueue.colStatus')}</TableCell>
                    <TableCell>{t('admin.helpFeedbackQueue.colActions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {clusters.map((c) => (
                    <TableRow key={c.id}>
                      <TableCell>{c.topic_label}</TableCell>
                      <TableCell align="center">{c.positive_count}</TableCell>
                      <TableCell align="center">{c.negative_count}</TableCell>
                      <TableCell align="center">{c.total_count}</TableCell>
                      <TableCell>
                        {c.docs_gap ? (
                          <Chip label={t('admin.helpFeedbackQueue.statusDocsGap')} size="small" color="error" icon={<Warning />} />
                        ) : (
                          <Chip label={t('admin.helpFeedbackQueue.statusOk')} size="small" color="success" />
                        )}
                      </TableCell>
                      <TableCell>
                        {!c.docs_gap && c.negative_count > 0 && (
                          <Button size="small" color="warning" onClick={() => markDocsGap(c.id)}>
                            {t('admin.helpFeedbackQueue.actionMarkDocsGap')}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Box>
      )}
    </Box>
  );
};

export default HelpFeedbackQueue;
