import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Trend, Rate } from "k6/metrics";

// Custom Performance Metrics
const errorRate = new Rate("error_rate");
const saturatedRate = new Rate("saturation_429_rate");
const inferenceDuration = new Trend("inference_latency_ms");
const tokensGenerated = new Counter("tokens_generated_total");

export const options = {
  stages: [
    { duration: "10s", target: 2 },  // Ramp-up to light concurrent load
    { duration: "30s", target: 4 },  // Plateau at saturation threshold
    { duration: "20s", target: 8 },  // Stress spike to trigger backpressure (429)
    { duration: "10s", target: 0 },  // Cool down
  ],
  thresholds: {
    // 95% of non-saturated requests should complete within realistic CPU threshold
    "http_req_duration{status:200}": ["p(95)<30000"],
    // Error rate (excluding intentional 429 backpressure) must remain below 1%
    "error_rate": ["rate<0.01"],
  },
};

const PROMPTS = [
  "Explain Kubernetes horizontal pod autoscaling in one concise sentence.",
  "What is the difference between latency and throughput in MLOps?",
  "Why is 4-bit GGUF quantization effective for CPU inference?",
  "Explain how Prometheus scrapes pull-based metrics from /metrics.",
  "What are the benefits of multi-stage Docker builds for Python apps?",
];

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export default function () {
  const prompt = PROMPTS[Math.floor(Math.random() * PROMPTS.length)];
  const payload = JSON.stringify({
    prompt: prompt,
    max_tokens: 32,
    temperature: 0.2,
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": `k6-${__VU}-${__ITER}-${Date.now()}`,
    },
    timeout: "65s",
  };

  const response = http.post(`${BASE_URL}/generate`, payload, params);

  if (response.status === 200) {
    errorRate.add(0);
    saturatedRate.add(0);
    try {
      const data = JSON.parse(response.body);
      check(data, {
        "has generated text": (r) => r.text && r.text.length > 0,
        "has valid latency_ms": (r) => r.latency_ms > 0,
      });
      if (data.tokens_generated) {
        tokensGenerated.add(data.tokens_generated);
      }
      if (data.latency_ms) {
        inferenceDuration.add(data.latency_ms);
      }
    } catch (e) {
      errorRate.add(1);
    }
  } else if (response.status === 429) {
    // Backpressure successfully triggered
    saturatedRate.add(1);
    errorRate.add(0);
    check(response, {
      "has Retry-After header": (r) => r.headers["Retry-After"] !== undefined,
    });
  } else {
    // Unexpected 5xx or connection error
    errorRate.add(1);
  }

  sleep(1);
}
