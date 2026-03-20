import React from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { ExamQuestion } from '../../types/composer';

interface ExamQuestionsPanelProps {
  questions: ExamQuestion[];
  disabled: boolean;
  onRemove: (eqId: number) => void;
  onUpdatePoints: (eqId: number, points: number) => void;
  onReorder: (order: { id: number; position: number }[]) => void;
}

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  hard: 'bg-red-100 text-red-700',
};

const ExamQuestionsPanel: React.FC<ExamQuestionsPanelProps> = ({
  questions,
  disabled,
  onRemove,
  onUpdatePoints,
  onReorder,
}) => {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor)
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = questions.findIndex((q) => q.id === active.id);
    const newIndex = questions.findIndex((q) => q.id === over.id);

    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = arrayMove(questions, oldIndex, newIndex);
    const order = reordered.map((q, index) => ({ id: q.id, position: index + 1 }));
    onReorder(order);
  };

  return (
    <div className="card p-4 bg-white rounded-lg border border-gray-200 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900">Prüfungsfragen</h3>
        <span className="text-sm text-gray-500">{questions.length} Fragen</span>
      </div>

      {questions.length === 0 ? (
        <div className="flex-1 flex items-center justify-center border-2 border-dashed border-gray-200 rounded-lg">
          <div className="text-center p-8">
            <p className="text-gray-400 text-sm">
              Noch keine Fragen hinzugefügt.
            </p>
            <p className="text-gray-400 text-sm mt-1">
              Wähle Fragen aus dem Pool links aus.
            </p>
          </div>
        </div>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={questions.map((q) => q.id)}
            strategy={verticalListSortingStrategy}
          >
            <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
              {questions.map((q, index) => (
                <SortableExamQuestionItem
                  key={q.id}
                  question={q}
                  position={index + 1}
                  disabled={disabled}
                  onRemove={onRemove}
                  onUpdatePoints={onUpdatePoints}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>
      )}

      {questions.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100 text-sm text-gray-600 flex justify-between">
          <span>Gesamt</span>
          <span className="font-semibold">
            {questions.reduce((sum, q) => sum + q.points, 0)} Punkte
          </span>
        </div>
      )}
    </div>
  );
};

interface SortableExamQuestionItemProps {
  question: ExamQuestion;
  position: number;
  disabled: boolean;
  onRemove: (eqId: number) => void;
  onUpdatePoints: (eqId: number, points: number) => void;
}

const SortableExamQuestionItem: React.FC<SortableExamQuestionItemProps> = ({
  question,
  position,
  disabled,
  onRemove,
  onUpdatePoints,
}) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: question.id,
    disabled,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="p-3 rounded-lg border border-gray-200 bg-white"
    >
      <div className="flex items-start gap-2">
        {/* Drag handle */}
        {!disabled && (
          <button
            {...attributes}
            {...listeners}
            className="mt-0.5 text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing flex-shrink-0 focus:outline-none"
            aria-label="Verschieben"
          >
            <svg width="12" height="16" viewBox="0 0 12 16" fill="currentColor">
              <circle cx="4" cy="3" r="1.5" />
              <circle cx="8" cy="3" r="1.5" />
              <circle cx="4" cy="8" r="1.5" />
              <circle cx="8" cy="8" r="1.5" />
              <circle cx="4" cy="13" r="1.5" />
              <circle cx="8" cy="13" r="1.5" />
            </svg>
          </button>
        )}

        {/* Position number */}
        <span className="text-sm font-semibold text-gray-400 flex-shrink-0 w-5 text-right">
          {position}.
        </span>

        {/* Question content */}
        <div className="flex-1 min-w-0">
          {question.review_status !== 'approved' && (
            <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded mb-1">
              &#9888; Nicht genehmigt
            </span>
          )}
          <p className="text-sm text-gray-800 line-clamp-2">{question.question_text}</p>
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span
              className={`text-xs px-1.5 py-0.5 rounded-full ${
                DIFFICULTY_COLORS[question.difficulty] || 'bg-gray-100 text-gray-600'
              }`}
            >
              {question.difficulty}
            </span>
            <span className="text-xs text-gray-400">{question.question_type}</span>
          </div>
        </div>

        {/* Points input */}
        <input
          type="number"
          min={0}
          step={0.5}
          value={question.points}
          disabled={disabled}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            if (!isNaN(val) && val >= 0) {
              onUpdatePoints(question.id, val);
            }
          }}
          className="w-14 text-sm text-center border border-gray-300 rounded px-1 py-0.5 disabled:bg-gray-50 disabled:text-gray-400 flex-shrink-0"
          aria-label="Punkte"
          title="Punkte"
        />
        <span className="text-xs text-gray-400 flex-shrink-0">Pkt</span>

        {/* Remove button */}
        {!disabled && (
          <button
            onClick={() => onRemove(question.id)}
            className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0 text-lg leading-none"
            aria-label="Frage entfernen"
          >
            &times;
          </button>
        )}
      </div>
    </div>
  );
};

export default ExamQuestionsPanel;
