import http from 'k6/http';
import { group } from 'k6';

export const options = {
  vus: 20,
  duration: '5m',
};

export default function () {
  const url = 'http://localhost:5005/';
  const headers = { 'Content-Type': 'application/json' };

  group('FastAPI Test', () => {
    http.get(url, { headers });
  });
}
