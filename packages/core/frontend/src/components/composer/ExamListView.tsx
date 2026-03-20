import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
} from '@mui/material';
import { ComposerService } from '../../services/ComposerService';
import type { CreateExamRequest } from '../../types/composer';

interface ExamListViewProps {
  onSelectExam: (id: number) => void;
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  finalized: 'Finalisiert',
  exported: 'Exportiert',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-yellow-100 text-yellow-800',
  finalized: 'bg-green-100 text-green-800',
  exported: 'bg-blue-100 text-blue-800',
};

const ExamListView: React.FC<ExamListViewProps> = ({ onSelectExam }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<CreateExamRequest>({ title: '', language: 'de' });
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['exams', searchQuery],
    queryFn: () => ComposerService.listExams({ search: searchQuery || undefined }),
  });

  const createMutation = useMutation({
    mutationFn: ComposerService.createExam,
    onSuccess: (exam) => {
      queryClient.invalidateQueries({ queryKey: ['exams'] });
      setDialogOpen(false);
      setForm({ title: '', language: 'de' });
      onSelectExam(exam.id);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: ComposerService.deleteExam,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['exams'] }),
  });

  const handleCreate = () => {
    if (form.title.trim()) {
      createMutation.mutate(form);
    }
  };

  const handleDialogClose = () => {
    if (!createMutation.isPending) {
      setDialogOpen(false);
      setForm({ title: '', language: 'de' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Exam Composer</h1>
          <p className="text-gray-600 mt-2">
            Stelle Prüfungen aus genehmigten Fragen zusammen
          </p>
        </div>
        <button
          onClick={() => setDialogOpen(true)}
          className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
        >
          + Neue Prüfung
        </button>
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          placeholder="Prüfungen durchsuchen..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
      </div>

      {/* Exam Grid */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Lade Prüfungen...</div>
      ) : !data?.exams.length ? (
        <div className="card p-12 text-center">
          <p className="text-gray-500 text-lg">
            Noch keine Prüfungen erstellt. Klicke auf "Neue Prüfung" um zu starten.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.exams.map((exam) => (
            <div
              key={exam.id}
              onClick={() => onSelectExam(exam.id)}
              className="card p-4 cursor-pointer hover:shadow-md transition-shadow"
            >
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-gray-900 truncate flex-1">
                  {exam.title}
                </h3>
                <span
                  className={`text-xs px-2 py-1 rounded-full ml-2 ${
                    STATUS_COLORS[exam.status] || 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {STATUS_LABELS[exam.status] || exam.status}
                </span>
              </div>
              {exam.course && (
                <p className="text-sm text-gray-500 mt-1">{exam.course}</p>
              )}
              <div className="flex gap-4 mt-3 text-sm text-gray-600">
                <span>{exam.question_count} Fragen</span>
                <span>{exam.total_points} Punkte</span>
                {exam.exam_date && <span>{new Date(exam.exam_date).toLocaleDateString('de-CH')}</span>}
              </div>
              {exam.status === 'draft' && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Prüfung wirklich löschen?')) {
                      deleteMutation.mutate(exam.id);
                    }
                  }}
                  className="mt-2 text-xs text-red-500 hover:text-red-700"
                >
                  Löschen
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle>Neue Prüfung erstellen</DialogTitle>
        <DialogContent>
          <div className="space-y-4 mt-2">
            <TextField
              label="Titel"
              fullWidth
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
            <TextField
              label="Kurs / Modul"
              fullWidth
              value={form.course || ''}
              onChange={(e) => setForm({ ...form, course: e.target.value })}
            />
            <TextField
              label="Prüfungsdatum"
              type="date"
              fullWidth
              InputLabelProps={{ shrink: true }}
              value={form.exam_date || ''}
              onChange={(e) => setForm({ ...form, exam_date: e.target.value })}
            />
            <TextField
              label="Zeitlimit (Minuten)"
              type="number"
              fullWidth
              value={form.time_limit_minutes || ''}
              onChange={(e) =>
                setForm({ ...form, time_limit_minutes: parseInt(e.target.value) || undefined })
              }
            />
            <TextField
              label="Erlaubte Hilfsmittel"
              fullWidth
              multiline
              rows={2}
              value={form.allowed_aids || ''}
              onChange={(e) => setForm({ ...form, allowed_aids: e.target.value })}
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose} disabled={createMutation.isPending}>
            Abbrechen
          </Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={!form.title.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? 'Erstelle...' : 'Erstellen'}
          </Button>
        </DialogActions>
      </Dialog>
    </div>
  );
};

export default ExamListView;
