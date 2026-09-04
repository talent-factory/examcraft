// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock scrollTo
Object.defineProperty(window, 'scrollTo', {
  writable: true,
  value: jest.fn(),
});

// Mock localStorage with actual storage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    },
  };
})();
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Mock sessionStorage with actual storage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => {
      const keys = Object.keys(store);
      return keys[index] || null;
    },
  };
})();
Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
  writable: true
});

// Mock console methods to reduce noise in tests
const originalError = console.error;
const originalWarn = console.warn;
const originalDebug = console.debug;

beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: ReactDOM.render is deprecated') ||
       args[0].includes('Warning: componentWillReceiveProps') ||
       args[0].includes('Warning: componentWillMount'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('deprecated') ||
       args[0].includes('Warning:') ||
       // translateError (TF-671) logs the raw error text via console.warn on its two
       // genuine-problem branches (code has no translation / error wasn't an AppError
       // at all) so it is never silently dropped, but never rendered in the UI. That's
       // noise in test output; keep it silent here while it stays intact in production
       // console output. Matched by the exact prefixes translateError.ts uses (not a
       // bare '[i18n]' substring), so this does not also swallow i18n.ts's
       // missingKeyHandler ('[i18n] Missing translation key: …'), which is the only
       // runtime signal for missing keys. The third, expected-path branch (code
       // resolved cleanly) logs via console.debug instead — see below.
       args[0].startsWith('[i18n] AppError without translation key:') ||
       args[0].startsWith('[i18n] Untyped error surfaced, using fallback key:'))
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };

  console.debug = (...args: any[]) => {
    if (typeof args[0] === 'string' && args[0].startsWith('[i18n] AppError surfaced:')) {
      return;
    }
    originalDebug.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
  console.debug = originalDebug;
});

// Global test utilities
export const createMockFile = (name: string, size: number, type: string): File => {
  const file = new File(['test content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

export const waitForLoadingToFinish = () => {
  return new Promise(resolve => setTimeout(resolve, 0));
};

// Mock react-i18next with real German translations
jest.mock('react-i18next', () => {
  const mockTranslations = require('./locales/de/translation.json');

  function mockResolveKey(obj: Record<string, any>, key: string): any {
    const parts = key.split('.');
    let current: any = obj;
    for (const part of parts) {
      if (current == null || typeof current !== 'object') return key;
      current = current[part];
    }
    return typeof current === 'string' ? current : key;
  }

  // i18next picks `<key>_one` / `<key>_other` when a numeric `count` is passed
  // (JSON v4 plurals). Without this the mock returned the bare key, so every
  // pluralised key rendered as a raw key string in component tests — silently,
  // because nothing asserted on the five keys that were pluralised before
  // TF-670. The plural category follows the mock's own language ('de').
  //
  // Checking `value !== candidate` (not `typeof value === 'string'`) matters:
  // `mockResolveKey` returns the candidate string itself, unchanged, whenever
  // resolution fails partway through (a missing middle segment, or a leaf that
  // isn't a string) — which is also typeof 'string'. A plain type check would
  // treat that failure as success and render the raw, unresolved candidate.
  function mockResolvePlural(key: string, params?: Record<string, any>): any {
    if (params && typeof params.count === 'number') {
      const category = new Intl.PluralRules('de').select(params.count);
      for (const candidate of [`${key}_${category}`, `${key}_other`]) {
        const value = mockResolveKey(mockTranslations, candidate);
        if (value !== candidate) return value;
      }
    }
    return mockResolveKey(mockTranslations, key);
  }

  // Stable across every `useTranslation()` call within one test file (Jest
  // isolates the module registry per file, so this still resets between
  // files). Real react-i18next memoizes `t`/`i18n` by language; a mock that
  // hands out a fresh `t` closure per render breaks any `useCallback`/
  // `useEffect` that lists `t` in its deps — the effect re-fires every
  // render under test even though it wouldn't in production.
  const stableT = (key: string, params?: Record<string, any>) => {
    const rawValue = mockResolvePlural(key, params);
    if (params?.returnObjects) {
      return rawValue;
    }
    let value = typeof rawValue === 'string' ? rawValue : key;
    if (params && typeof value === 'string') {
      Object.entries(params).forEach(([k, v]) => {
        value = (value as string).replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      });
    }
    return value;
  };
  const stableI18n = {
    changeLanguage: jest.fn().mockResolvedValue(undefined),
    language: 'de',
  };

  return {
    useTranslation: () => ({ t: stableT, i18n: stableI18n }),
    Trans: ({ children }: { children: React.ReactNode }) => children,
    initReactI18next: { type: '3rdParty', init: jest.fn() },
  };
});

// Mock environment variables
process.env.REACT_APP_API_URL = 'http://localhost:8000';

// Increase timeout for async tests
jest.setTimeout(10000);
