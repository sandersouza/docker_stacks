import redis from 'k6/experimental/redis';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

const keys = new SharedArray('keys', function() {
    return Array.from({length: 1000}, (_, i) => `key${i}`);
});

export const options = {
    scenarios: {
        ramping_test: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '1m', target: 50 },
                { duration: '1m', target: 50 },
                { duration: '1m', target: 0 },
            ],
            gracefulRampDown: '30s',
        },
    },
    thresholds: {
        http_req_failed: ['rate<0.01'],
        http_req_duration: ['p(95)<500'],
    },
};

export default function () {
    const client = new redis.Client({
        socket: {
            host: 'localhost',
            port: 6385,
        },
        username: 'default',
        password: '7zEzcCJGDnZFxiIp8z',
    });

    const randomKey = keys[Math.floor(Math.random() * keys.length)];
    
    try {
        const exists = client.exists(randomKey);
        if (!exists) {
            console.warn(`Key ${randomKey} does not exist.`);
        } else {
            const value = client.hget('operation-results-table', randomKey);
            check(value, {
                'valor não é nulo': (v) => v !== null,
            });
        }
    } catch (error) {
        console.error(`Error retrieving key ${randomKey}:`, error);
    }

    sleep(Math.random() * 2 + 1);
}