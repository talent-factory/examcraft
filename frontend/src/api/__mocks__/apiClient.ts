export const API_BASE_URL = 'http://localhost:8000';

export const apiClient = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  },
};

export const setLogoutCallback = jest.fn();
export const setupFetchInterceptor = jest.fn();
export const triggerAuthLogout = jest.fn();
