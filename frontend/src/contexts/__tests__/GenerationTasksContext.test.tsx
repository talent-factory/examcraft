import React from 'react';
import { render, screen } from '@testing-library/react';
import { GenerationTasksProvider, useGenerationTasks } from '../GenerationTasksContext';

// Mock AuthContext
jest.mock('../AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    accessToken: null,
  }),
}));

// Mock componentLoader
jest.mock('../../utils/componentLoader', () => ({
  loadRAGService: jest.fn().mockResolvedValue(null),
}));

const TestConsumer: React.FC = () => {
  const { activeTasks, tasks } = useGenerationTasks();
  return (
    <div>
      <span data-testid="active-count">{activeTasks.length}</span>
      <span data-testid="total-count">{Object.keys(tasks).length}</span>
    </div>
  );
};

describe('GenerationTasksContext', () => {
  it('provides empty state initially', () => {
    render(
      <GenerationTasksProvider>
        <TestConsumer />
      </GenerationTasksProvider>
    );

    expect(screen.getByTestId('active-count')).toHaveTextContent('0');
    expect(screen.getByTestId('total-count')).toHaveTextContent('0');
  });

  it('throws when used outside provider', () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow('useGenerationTasks must be used within GenerationTasksProvider');
    consoleError.mockRestore();
  });
});
