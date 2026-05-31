export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  accessToken?: string;
  body?: BodyInit | null;
  json?: unknown;
  okStatuses?: number[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── token refresh plumbing ─────────────────────────────────────

type RefreshFn = () => Promise<string | null>;
let _refreshTokenFn: RefreshFn | null = null;
let _refreshPromise: Promise<string | null> | null = null;

/** Register a callback that returns a new access token (or null). */
export const setTokenRefreshFn = (fn: RefreshFn) => {
  _refreshTokenFn = fn;
};

const _tryRefresh = async (): Promise<string | null> => {
  if (!_refreshTokenFn) return null;
  // deduplicate concurrent refresh attempts
  if (!_refreshPromise) {
    _refreshPromise = _refreshTokenFn().finally(() => {
      _refreshPromise = null;
    });
  }
  return _refreshPromise;
};

// ── public helpers ─────────────────────────────────────────────

export const readErrorMessage = async (response: Response) => {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (body.detail && typeof body.detail === "object" && "message" in body.detail) {
      return String((body.detail as { message: unknown }).message);
    }
  } catch {
    // Fall back to a status-only message when the response is not JSON.
  }

  return `请求失败：${response.status}`;
};

export const apiRequest = async <T>(
  apiBaseUrl: string,
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> => {
  const { accessToken, headers, json, okStatuses = [], ...init } = options;

  const _doFetch = async (token?: string): Promise<Response> => {
    const requestHeaders = new Headers(headers);

    if (json !== undefined && !requestHeaders.has("Content-Type")) {
      requestHeaders.set("Content-Type", "application/json");
    }

    const effectiveToken = token ?? accessToken;
    if (effectiveToken) {
      requestHeaders.set("Authorization", `Bearer ${effectiveToken}`);
    }

    return fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: requestHeaders,
      body: json === undefined ? init.body : JSON.stringify(json),
    });
  };

  let response = await _doFetch();

  // auto-refresh on 401
  if (response.status === 401 && !okStatuses.includes(401) && _refreshTokenFn) {
    const newToken = await _tryRefresh();
    if (newToken) {
      response = await _doFetch(newToken);
    }
  }

  if (!response.ok && !okStatuses.includes(response.status)) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
};
