/**
 * KubeSentiment TypeScript/JavaScript SDK
 *
 * Official TypeScript/JavaScript client library for KubeSentiment API.
 *
 * @example
 * ```typescript
 * import { KubeSentimentClient } from 'kubesentiment-sdk';
 *
 * const client = new KubeSentimentClient({
 *   baseUrl: 'http://localhost:8000',
 *   apiKey: 'your-api-key'
 * });
 *
 * const result = await client.predict('This is amazing!');
 * console.log(result.label, result.confidence);
 * ```
 */

export const VERSION = '1.0.0';

/**
 * Sentiment prediction labels
 */
export enum PredictionLabel {
  POSITIVE = 'POSITIVE',
  NEGATIVE = 'NEGATIVE',
  NEUTRAL = 'NEUTRAL'
}

/**
 * Batch job priority levels
 */
export enum Priority {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

/**
 * Batch job status
 */
export enum JobStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

/**
 * Single prediction result
 */
export interface PredictionResult {
  label: string;
  confidence: number;
  inferenceTimeMs: number;
  modelName: string;
  backend: string;
  cached: boolean;
  textLength?: number;
  explanation?: Record<string, any>;
}

/**
 * Batch prediction job
 */
export interface BatchJob {
  jobId: string;
  status: string;
  createdAt: string;
  priority: string;
  totalTexts: number;
  processed?: number;
  results?: PredictionResult[];
  error?: string;
}

/**
 * Model information
 */
export interface ModelInfo {
  modelName: string;
  backend: string;
  version?: string;
  loaded: boolean;
}

/**
 * Health check response
 */
export interface HealthStatus {
  status: string;
  timestamp: string;
  version?: string;
}

/**
 * Client configuration options
 */
export interface ClientConfig {
  /** Base URL of the KubeSentiment API */
  baseUrl: string;
  /** Optional API key for authentication */
  apiKey?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Custom headers */
  headers?: Record<string, string>;
}

/**
 * Prediction options
 */
export interface PredictOptions {
  /** Whether to include model explanation */
  explain?: boolean;
  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * Batch prediction options
 */
export interface BatchPredictOptions {
  /** Job priority */
  priority?: Priority;
  /** Whether to wait for job completion */
  wait?: boolean;
  /** Polling interval in milliseconds (if wait=true) */
  pollInterval?: number;
}

/**
 * Custom error class for SDK errors
 */
export class KubeSentimentError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'KubeSentimentError';
  }
}

/**
 * API error class
 */
export class APIError extends KubeSentimentError {
  statusCode: number;

  constructor(statusCode: number, message: string) {
    super(`API Error ${statusCode}: ${message}`);
    this.statusCode = statusCode;
    this.name = 'APIError';
  }
}

/**
 * Official TypeScript/JavaScript client for KubeSentiment API
 *
 * @example
 * ```typescript
 * const client = new KubeSentimentClient({
 *   baseUrl: 'http://localhost:8000',
 *   apiKey: 'your-api-key'
 * });
 *
 * // Single prediction
 * const result = await client.predict('I love this product!');
 * console.log(`${result.label}: ${(result.confidence * 100).toFixed(2)}%`);
 *
 * // Batch prediction
 * const job = await client.batchPredict(['Great!', 'Terrible'], { wait: true });
 * job.results?.forEach(r => console.log(r.label));
 * ```
 */
export class KubeSentimentClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;
  private headers: Record<string, string>;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
    this.headers = {
      'Content-Type': 'application/json',
      'User-Agent': `kubesentiment-sdk/${VERSION}`,
      ...config.headers
    };

    if (this.apiKey) {
      this.headers['X-API-Key'] = this.apiKey;
    }
  }

  /**
   * Make HTTP request to API
   */
  private async request<T>(
    method: string,
    endpoint: string,
    body?: any,
    options?: { timeout?: number }
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const timeout = options?.timeout || this.timeout;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage: string;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || response.statusText;
        } catch {
          errorMessage = response.statusText;
        }
        throw new APIError(response.status, errorMessage);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof APIError) {
        throw error;
      }
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new KubeSentimentError(`Request timeout after ${timeout}ms`);
        }
        throw new KubeSentimentError(`Request failed: ${error.message}`);
      }
      throw new KubeSentimentError('Request failed with unknown error');
    }
  }

  /**
   * Predict sentiment for a single text
   *
   * @param text - Input text to analyze
   * @param options - Prediction options
   * @returns Promise resolving to PredictionResult
   *
   * @example
   * ```typescript
   * const result = await client.predict('This is great!');
   * console.log(result.label, result.confidence);
   * ```
   */
  async predict(text: string, options?: PredictOptions): Promise<PredictionResult> {
    const response = await this.request<any>(
      'POST',
      '/api/v1/predict',
      { text, explain: options?.explain || false },
      { timeout: options?.timeout }
    );

    return {
      label: response.label,
      confidence: response.score,
      inferenceTimeMs: response.inference_time_ms || 0,
      modelName: response.model_name || 'unknown',
      backend: response.backend || 'unknown',
      cached: response.cached || false,
      textLength: response.text_length,
      explanation: response.explanation
    };
  }

  /**
   * Submit batch prediction job
   *
   * @param texts - Array of texts to analyze
   * @param options - Batch prediction options
   * @returns Promise resolving to BatchJob
   *
   * @example
   * ```typescript
   * const job = await client.batchPredict(['Great!', 'Terrible'], { wait: true });
   * job.results?.forEach(r => console.log(r.label));
   * ```
   */
  async batchPredict(
    texts: string[],
    options?: BatchPredictOptions
  ): Promise<BatchJob> {
    const priority = options?.priority || Priority.MEDIUM;

    const response = await this.request<any>(
      'POST',
      '/api/v1/batch/predict',
      { texts, priority }
    );

    const job: BatchJob = {
      jobId: response.job_id,
      status: response.status,
      createdAt: response.created_at,
      priority: response.priority,
      totalTexts: response.total_texts
    };

    if (options?.wait) {
      return this.waitForJob(job.jobId, options.pollInterval);
    }

    return job;
  }

  /**
   * Get status of batch job
   *
   * @param jobId - Batch job ID
   * @returns Promise resolving to BatchJob
   */
  async getBatchStatus(jobId: string): Promise<BatchJob> {
    const response = await this.request<any>('GET', `/api/v1/batch/status/${jobId}`);

    return {
      jobId: response.job_id,
      status: response.status,
      createdAt: response.created_at,
      priority: response.priority,
      totalTexts: response.total_texts,
      processed: response.processed
    };
  }

  /**
   * Get results of completed batch job
   *
   * @param jobId - Batch job ID
   * @returns Promise resolving to BatchJob with results
   */
  async getBatchResults(jobId: string): Promise<BatchJob> {
    const response = await this.request<any>('GET', `/api/v1/batch/results/${jobId}`);

    const results: PredictionResult[] = response.results?.map((r: any) => ({
      label: r.label,
      confidence: r.score,
      inferenceTimeMs: r.inference_time_ms || 0,
      modelName: r.model_name || 'unknown',
      backend: r.backend || 'unknown',
      cached: r.cached || false
    })) || [];

    return {
      jobId: response.job_id,
      status: response.status,
      createdAt: response.created_at,
      priority: response.priority,
      totalTexts: response.total_texts,
      results
    };
  }

  /**
   * Wait for batch job to complete
   *
   * @param jobId - Batch job ID
   * @param pollInterval - Polling interval in milliseconds (default: 2000)
   * @param maxWait - Maximum wait time in milliseconds (default: 300000)
   * @returns Promise resolving to completed BatchJob
   */
  async waitForJob(
    jobId: string,
    pollInterval: number = 2000,
    maxWait: number = 300000
  ): Promise<BatchJob> {
    const startTime = Date.now();

    while (true) {
      const job = await this.getBatchStatus(jobId);

      if (job.status === JobStatus.COMPLETED) {
        return this.getBatchResults(jobId);
      } else if (job.status === JobStatus.FAILED) {
        throw new KubeSentimentError(`Batch job failed: ${job.error}`);
      }

      if (Date.now() - startTime > maxWait) {
        throw new KubeSentimentError(
          `Job did not complete within ${maxWait}ms`
        );
      }

      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }

  /**
   * Cancel a batch job
   *
   * @param jobId - Batch job ID
   * @returns Promise resolving to true if cancelled successfully
   */
  async cancelBatchJob(jobId: string): Promise<boolean> {
    try {
      await this.request('DELETE', `/api/v1/batch/${jobId}`);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get information about the loaded model
   *
   * @returns Promise resolving to model information
   */
  async getModelInfo(): Promise<ModelInfo> {
    return this.request<ModelInfo>('GET', '/api/v1/model-info');
  }

  /**
   * Check service health
   *
   * @returns Promise resolving to health status
   */
  async healthCheck(): Promise<HealthStatus> {
    return this.request<HealthStatus>('GET', '/api/v1/health');
  }

  /**
   * Get Prometheus metrics
   *
   * @returns Promise resolving to metrics in Prometheus format
   */
  async getMetrics(): Promise<string> {
    const url = `${this.baseUrl}/api/v1/metrics`;
    const response = await fetch(url, { headers: this.headers });
    if (!response.ok) {
      throw new APIError(response.status, response.statusText);
    }
    return response.text();
  }

  /**
   * Get drift detection summary
   *
   * @returns Promise resolving to drift detection statistics
   */
  async getDriftSummary(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('GET', '/api/v1/monitoring/drift');
  }

  /**
   * Get business KPIs
   *
   * @returns Promise resolving to business metrics
   */
  async getBusinessKPIs(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('GET', '/api/v1/monitoring/kpis/business');
  }
}

/**
 * Convenience function for quick predictions
 *
 * @param text - Text to analyze
 * @param baseUrl - API base URL (default: http://localhost:8000)
 * @param apiKey - Optional API key
 * @returns Promise resolving to PredictionResult
 *
 * @example
 * ```typescript
 * import { predict } from 'kubesentiment-sdk';
 * const result = await predict('I love this!');
 * console.log(result.label);
 * ```
 */
export async function predict(
  text: string,
  baseUrl: string = 'http://localhost:8000',
  apiKey?: string
): Promise<PredictionResult> {
  const client = new KubeSentimentClient({ baseUrl, apiKey });
  return client.predict(text);
}
