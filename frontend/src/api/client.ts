import axios, { type AxiosError, type AxiosInstance, type AxiosRequestConfig, type CancelTokenSource } from "axios";
import { toastError } from "@/components/common/Toast";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Retry configuration
const MAX_RETRIES = 3;
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];
const RETRYABLE_ERROR_CODES = ["ERR_NETWORK", "ECONNABORTED", "ETIMEDOUT"];
const RETRY_DELAY_BASE = 1000;

function isRetryableError(error: unknown): error is AxiosError {
  if (!axios.isAxiosError(error)) return false;

  // Retry on network errors
  if (RETRYABLE_ERROR_CODES.includes(error.code as string)) {
    return true;
  }

  // Retry on specific status codes
  const status = error.response?.status;
  if (status && RETRYABLE_STATUS_CODES.includes(status)) {
    return true;
  }

  return false;
}

function getRetryDelay(attemptNumber: number): number {
  return RETRY_DELAY_BASE * Math.pow(2, attemptNumber - 1);
}

interface ApiClientConfig extends AxiosRequestConfig {
  _retryCount?: number;
  _cancelToken?: CancelTokenSource;
}

class ApiClient {
  private client: AxiosInstance;
  private cancelTokens = new Map<string, CancelTokenSource>();

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem("jwt");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add cancellation token
        const source = axios.CancelToken.source();
        config.cancelToken = source.token;
        this.cancelTokens.set(config.url || "", source);

        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiClientConfig>) => {
        const config = error.config as ApiClientConfig;

        // Handle 401 (auth error)
        if (error.response?.status === 401) {
          this.clearAuth();
          return Promise.reject(error);
        }

        // Don't retry if explicitly disabled
        if (config._retryCount === 0) {
          this.showError(error);
          return Promise.reject(error);
        }

        // Retry logic
        if (isRetryableError(error) && (!config._retryCount || config._retryCount < MAX_RETRIES)) {
          config._retryCount = config._retryCount || 0;
          config._retryCount += 1;

          const delay = getRetryDelay(config._retryCount);
          console.warn(`Retrying request (${config._retryCount}/${MAX_RETRIES}) after ${delay}ms`, config.url);

          await new Promise((resolve) => setTimeout(resolve, delay));

          return this.client(config);
        }

        // Show error toast for non-retryable or exhausted retries
        this.showError(error);

        return Promise.reject(error);
      }
    );
  }

  private clearAuth() {
    localStorage.removeItem("jwt");
    localStorage.removeItem("user");
    toastError("Session expired. Please log in again.");
    // Use window.location.href for auth errors (full reload needed to clear state)
    window.location.href = "/login";
  }

  private showError(error: AxiosError) {
    const status = error.response?.status;

    // Only show toast for network errors and server errors (5xx)
    // Don't show for client errors (4xx) - these should be handled by pages
    const isServerError = !status || status >= 500 || error.code === "ERR_NETWORK";

    if (isServerError) {
      const message = this.extractErrorMessage(error);
      toastError(message);
    }
  }

  private extractErrorMessage(error: AxiosError): string {
    const responseData = error.response?.data as { message?: string; detail?: string } | undefined;
    const apiMessage = responseData?.message || responseData?.detail;
    if (apiMessage) return String(apiMessage);

    if (error.code === "ERR_NETWORK") {
      return "Network error. Please check your connection.";
    }

    if (error.code === "ECONNABORTED") {
      return "Request timed out. Please try again.";
    }

    const status = error.response?.status;
    if (status) {
      switch (status) {
        case 400:
          return "Invalid request. Please check your input.";
        case 401:
          return "Please log in to continue.";
        case 403:
          return "You don't have permission to do this.";
        case 404:
          return "The requested resource was not found.";
        case 429:
          return "Too many requests. Please slow down.";
        case 500:
        case 502:
        case 503:
          return "Server error. Please try again later.";
      }
    }

    return error.message || "An error occurred";
  }

  // Cancel a pending request by URL
  cancelRequest(url: string) {
    const token = this.cancelTokens.get(url);
    if (token) {
      token.cancel(`Request cancelled: ${url}`);
      this.cancelTokens.delete(url);
    }
  }

  // Cancel all pending requests
  cancelAllRequests() {
    this.cancelTokens.forEach((token) => token.cancel("Cancelled all requests"));
    this.cancelTokens.clear();
  }

  get<T>(url: string, config?: AxiosRequestConfig) {
    return this.client.get<T>(url, config);
  }

  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return this.client.post<T>(url, data, config);
  }

  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return this.client.put<T>(url, data, config);
  }

  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig) {
    return this.client.patch<T>(url, data, config);
  }

  delete<T>(url: string, config?: AxiosRequestConfig) {
    return this.client.delete<T>(url, config);
  }
}

export const api = new ApiClient();
export { API_BASE_URL };
