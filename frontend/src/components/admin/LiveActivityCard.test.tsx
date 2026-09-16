import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LiveActivityCard from './LiveActivityCard';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key} ${JSON.stringify(options)}` : key,
  }),
}));

describe('LiveActivityCard', () => {
  it('renders the exact value when exact is true, including a genuine zero', () => {
    render(<LiveActivityCard bucketId="documents_upload" bucket={{ value: 0, exact: true }} />);

    expect(screen.getByTestId('live-activity-card-value-documents_upload')).toHaveTextContent('0');
  });

  it('renders "< N" via the lessThan i18n key when exact is false', () => {
    render(<LiveActivityCard bucketId="questions_review" bucket={{ value: 5, exact: false }} />);

    expect(screen.getByTestId('live-activity-card-value-questions_review')).toHaveTextContent(
      'pages.admin.liveActivity.lessThan {"value":5}',
    );
  });

  it('renders the unavailable state instead of a value when the bucket is missing from the snapshot', () => {
    render(<LiveActivityCard bucketId="exam_compose" bucket={undefined} />);

    expect(screen.getByTestId('live-activity-card-unavailable-exam_compose')).toBeInTheDocument();
    expect(screen.queryByTestId('live-activity-card-value-exam_compose')).not.toBeInTheDocument();
  });
});
