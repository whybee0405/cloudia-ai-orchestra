import { API_BASE } from './config.js';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * Core fetch wrapper. All API calls go through this function.
 * @param {string} method  HTTP method
 * @param {string} path    Path relative to API_BASE (must start with /)
 * @param {object} [body]  Optional JSON body
 * @returns {Promise<any>}
 */
async function request(method, path, body) {
  const options = {
    method,
    headers: {},
  };

  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch (err) {
    // Network failure (API offline, CORS, etc.)
    throw new ApiError('Unable to reach API server. Check that the backend is running.', 0);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const payload = await res.json();
      detail = payload.detail || payload.message || detail;
    } catch {
      // Non-JSON error body — keep statusText
    }
    throw new ApiError(detail, res.status);
  }

  // 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

export const api = {
  /** HTTP GET */
  get(path) {
    return request('GET', path);
  },

  /** HTTP POST with JSON body */
  post(path, body) {
    return request('POST', path, body);
  },

  /** HTTP PUT with JSON body */
  put(path, body) {
    return request('PUT', path, body);
  },

  /** HTTP PATCH with JSON body */
  patch(path, body) {
    return request('PATCH', path, body);
  },

  /** HTTP DELETE */
  del(path) {
    return request('DELETE', path);
  },
};
