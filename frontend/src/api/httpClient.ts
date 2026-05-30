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
  const requestHeaders = new Headers(headers);

  if (json !== undefined && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: requestHeaders,
    body: json === undefined ? init.body : JSON.stringify(json),
  });

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
