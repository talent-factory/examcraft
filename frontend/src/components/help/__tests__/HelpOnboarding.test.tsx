import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';

// Capture driver.js calls so tests can trigger callbacks
let capturedHighlightConfig: any = null;
const mockDestroy = jest.fn();
const mockHighlight = jest.fn((config: any) => { capturedHighlightConfig = config; });
const mockDriverInstance = { highlight: mockHighlight, destroy: mockDestroy };

jest.mock('driver.js', () => ({
  driver: jest.fn(() => mockDriverInstance),
}));
jest.mock('driver.js/dist/driver.css', () => {});

import HelpOnboarding, { OnboardingStep } from '../HelpOnboarding';

const mockStatus = { id: 1, role: 'teacher', current_step: 1, completed_steps: [0], completed: false };

const navStep: OnboardingStep = {
  step: 1,
  title_de: 'Dokumente',
  title_en: 'Documents',
  description_de: 'Beschreibung',
  description_en: 'Description',
  route: '/documents',
  highlight_selector: "[data-testid='upload-area']",
  nav_selector: "[data-testid='nav-documents']",
  tab_selector: null,
};

const doneStep: OnboardingStep = {
  step: 2,
  title_de: 'Fertig',
  title_en: 'Done',
  description_de: '',
  description_en: '',
  route: null,
  highlight_selector: null,
  nav_selector: null,
  tab_selector: null,
};

const renderOnboarding = (overrides: Partial<React.ComponentProps<typeof HelpOnboarding>> = {}) => {
  const props = {
    status: mockStatus,
    steps: [doneStep, navStep, doneStep],
    active: false,
    onCompleteStep: jest.fn().mockResolvedValue(undefined),
    onSkipStep: jest.fn().mockResolvedValue(undefined),
    onTourComplete: jest.fn(),
    onTourCancel: jest.fn(),
    ...overrides,
  };
  return { ...render(<MemoryRouter><HelpOnboarding {...props} /></MemoryRouter>), props };
};

let navDocumentsEl: HTMLElement;

beforeEach(() => {
  capturedHighlightConfig = null;
  mockDestroy.mockClear();
  mockHighlight.mockClear();
  // Inject nav element so highlightNavStep doesn't skip (new upfront DOM check)
  navDocumentsEl = document.createElement('a');
  navDocumentsEl.setAttribute('data-testid', 'nav-documents');
  document.body.appendChild(navDocumentsEl);
});

afterEach(() => {
  navDocumentsEl?.remove();
});

describe('HelpOnboarding — confirmation dialog', () => {
  it('calls onTourCancel (not onTourComplete) when user clicks "Ja, beenden"', async () => {
    const { props } = renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    expect(mockHighlight).toHaveBeenCalled();
    const closeClick = capturedHighlightConfig?.popover?.onCloseClick;
    expect(closeClick).toBeDefined();

    await act(async () => { closeClick(); });

    expect(screen.getByText(/Tour beenden\?/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Ja, beenden/i }));

    expect(props.onTourCancel).toHaveBeenCalledTimes(1);
    expect(props.onTourComplete).not.toHaveBeenCalled();
  });

  it('hides dialog when user clicks "Abbrechen"', async () => {
    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
    });

    const closeClick = capturedHighlightConfig?.popover?.onCloseClick;
    await act(async () => { closeClick(); });

    expect(screen.getByText(/Tour beenden\?/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Abbrechen/i }));

    expect(screen.queryByText(/Tour beenden\?/i)).not.toBeInTheDocument();
  });
});

describe('HelpOnboarding — nav_selector not in DOM', () => {
  it('calls onSkipStep to skip when nav_selector element is absent', async () => {
    // Remove the nav element injected by beforeEach so this test has it absent
    navDocumentsEl?.remove();

    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    renderOnboarding({
      active: true,
      status: { ...mockStatus, current_step: 1 },
      steps: [doneStep, navStep, doneStep],
      onSkipStep,
    });

    await act(async () => {
      await new Promise(r => setTimeout(r, 50));
    });

    expect(onSkipStep).toHaveBeenCalledWith(1);
  });
});

const tabStep: OnboardingStep = {
  step: 7,
  title_de: 'Institutionen',
  title_en: 'Institutions',
  description_de: 'Tab-Beschreibung',
  description_en: 'Tab description',
  route: '/admin',
  highlight_selector: "[data-testid='admin-tab-content-institutions']",
  nav_selector: null,
  tab_selector: "[data-testid='admin-tab-btn-institutions']",
};

describe('HelpOnboarding — TAB_NAVIGATING mode', () => {
  it('skips tab step when tab_selector element is not in DOM', async () => {
    const onSkipStep = jest.fn().mockResolvedValue(undefined);

    render(
      <MemoryRouter initialEntries={['/admin']}>
        <HelpOnboarding
          status={{ ...mockStatus, current_step: 7 }}
          steps={[...Array(7).fill(doneStep), tabStep, doneStep]}
          active={true}
          onCompleteStep={jest.fn().mockResolvedValue(undefined)}
          onSkipStep={onSkipStep}
          onTourComplete={jest.fn()}
          onTourCancel={jest.fn()}
        />
      </MemoryRouter>
    );

    await act(async () => {
      await new Promise(r => setTimeout(r, 600));
    });

    expect(onSkipStep).toHaveBeenCalledWith(7);
  });

  it('highlights tab_selector element when on correct route and tab button exists', async () => {
    const tabBtn = document.createElement('button');
    tabBtn.setAttribute('data-testid', 'admin-tab-btn-institutions');
    document.body.appendChild(tabBtn);

    try {
      render(
        <MemoryRouter initialEntries={['/admin']}>
          <HelpOnboarding
            status={{ ...mockStatus, current_step: 7 }}
            steps={[...Array(7).fill(doneStep), tabStep, doneStep]}
            active={true}
            onCompleteStep={jest.fn().mockResolvedValue(undefined)}
            onSkipStep={jest.fn().mockResolvedValue(undefined)}
            onTourComplete={jest.fn()}
            onTourCancel={jest.fn()}
          />
        </MemoryRouter>
      );

      await act(async () => {
        await new Promise(r => setTimeout(r, 600));
      });

      expect(mockHighlight).toHaveBeenCalled();
      expect(capturedHighlightConfig?.element).toBe("[data-testid='admin-tab-btn-institutions']");
    } finally {
      document.body.removeChild(tabBtn);
    }
  });
});
