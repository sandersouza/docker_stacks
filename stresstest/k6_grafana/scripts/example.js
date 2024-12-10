import http from 'k6/http';
import { sleep, check, group } from 'k6';

export let options = {
    stages: [
        { duration: '1m', target: 25 },
        { duration: '1m', target: 30 },
        { duration: '1m', target: 35 },
        { duration: '1m', target: 40 },
        { duration: '1m', target: 45 },
        { duration: '1m', target: 50 },
    ],
    tags: {
        env: "production"
    }
};

export default function () {
    group('Test k6.io', function() {
        let paramsK6 = {
            tags: {
                testid: "k6-io-test"
            }
        };
        let resK6 = http.get('http://test.k6.io', paramsK6);
        check(resK6, {
            "status is 200": (r) => r.status === 200,
            "transaction time OK": (r) => r.timings.duration < 200
        });
    });

    group('Test Grafana', function() {
        let paramsGrafana = {
            tags: {
                testid: "grafana-test"
            }
        };
        let resGrafana = http.get('http://grafana:3000', paramsGrafana);
        check(resGrafana, {
            "status is 200": (r) => r.status === 200,
            "transaction time OK": (r) => r.timings.duration < 200
        });
    });

    sleep(1);
}
