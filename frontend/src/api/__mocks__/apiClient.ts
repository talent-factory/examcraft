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

export const setTokenRefreshCallback = jest.fn();
export const setLogoutCallback = jest.fn();
export const setAdoptStoredTokensCallback = jest.fn();
export const setupFetchInterceptor = jest.fn();
export const executeTokenRefresh = jest.fn().mockResolvedValue(undefined);
export const triggerAuthLogout = jest.fn();
