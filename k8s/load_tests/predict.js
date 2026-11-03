
import http from "k6/http";
import { check } from "k6";

const payload = open("/scripts/request.json");

const url =
  "http://taxi-prediction.taxi-ml.svc.cluster.local/predict";

export const options = {
  scenarios: {
    fixed_load: {
      executor: "constant-arrival-rate",
      rate: 50,
      timeUnit: "1s",
      duration: "2m",
      preAllocatedVUs: 20,
      maxVUs: 60,
    },
  },

  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<200"],
    dropped_iterations: ["count==0"],
  },
};

export default function () {
  const response = http.post(url, payload, {
    headers: {
      "Content-Type": "application/json",
    },
    timeout: "10s",
  });

  check(response, {
    "status is 200": (r) => r.status === 200,
  });
}
