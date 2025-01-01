import exec from 'k6/x/exec';    // Precisamos do k6 compilado com xk6-exec
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Opções do teste
// ---------------------------------------------------------------------------
export const options = {
  // Tag para identificação
  tags: { testid: 'openquiz_create_quic' },

  // Ignorar certificados self-signed
  insecureSkipTLSVerify: true,

  // Cenário: 20 VUs por 5 minutos
  vus: 20,
  duration: '5m',
};

// ---------------------------------------------------------------------------
// Métricas que recriam nomes nativos do k6/http
// Cada Trend já gera min, max, p(50,90,95,99), etc.
// ---------------------------------------------------------------------------
const http_req_blocked       = new Trend('http_req_blocked',       true);
const http_req_connecting    = new Trend('http_req_connecting',    true);
const http_req_tls_handshaking = new Trend('http_req_tls_handshaking', true);
const http_req_sending       = new Trend('http_req_sending',       true);
const http_req_waiting       = new Trend('http_req_waiting',       true);
const http_req_receiving     = new Trend('http_req_receiving',     true);
const http_req_duration      = new Trend('http_req_duration',      true);
const http_req_failed        = new Rate('http_req_failed'); // registra % de falhas

// ---------------------------------------------------------------------------
// Configurações do curl + HTTP/3
// ---------------------------------------------------------------------------
const baseUrl = 'https://localhost:4433/quizzes/';
const headers = [
  '-H', 'Content-Type: application/json',
  '-H', 'Accept-Encoding: gzip, deflate, br',
  '-H', 'User-Agent: k6-curl-http3',
  '-H', 'Connection: keep-alive',
  // Ajuste o token para o seu valor real
  '-H', 'Authorization: Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf',
];

const curlOptions = [
  '--insecure', // ignora certificado
  '--http3',    // força HTTP/3
];

// --write-out para extrair dados de timing do curl (em segundos)
const writeOutFormat = [
  '--write-out',
  // Ex.:  HTTP_CODE:201,CONNECT:0.01,TLS:0.02,START:0.05,TOTAL:0.15
  'HTTP_CODE:%{http_code},CONNECT:%{time_connect},TLS:%{time_appconnect},START:%{time_starttransfer},TOTAL:%{time_total}',
];

// Exemplo de payload JSON
const payload = JSON.stringify({
  name: "Exemplo de Quiz",
  questions: [
    {
      question_text: "O que é FastAPI?",
      points: 100,
      answers: [
        { answer_text: "Uma API rápida", is_correct: true },
        { answer_text: "Um framework lento", is_correct: false },
        { answer_text: "Todas as acima", is_correct: false },
      ],
    },
  ],
});

// Para emular as tags que o k6 costuma adicionar
function getDefaultTags(httpCode) {
  return {
    // Normalmente, k6 coloca method, nome do request, proto, status, etc.
    method: 'POST',
    name: `POST ${baseUrl}`,
    proto: 'HTTP/3',
    status: httpCode ? String(httpCode) : '0',
  };
}

export default function () {
  // Monta o comando do curl
  const postCmd = [
    'curl',
    ...curlOptions,
    ...headers,
    '-X', 'POST',
    '-d', payload,
    baseUrl,
    ...writeOutFormat,
    '-s',
    '-o', '/dev/null'
  ];

  // Executa via xk6-exec
  const res = exec.command(postCmd[0], postCmd.slice(1), {
    continueOnError: true,
  });

  // Captura saída do curl (stdout)
  const stdout = res ? (res.stdout || '') : '';

  // Vamos extrair o que veio do --write-out
  //  Formato esperado: HTTP_CODE:xxx,CONNECT:0.00,TLS:0.00,START:0.00,TOTAL:0.00
  const match = stdout.match(/HTTP_CODE:(\d+),CONNECT:([\d.]+),TLS:([\d.]+),START:([\d.]+),TOTAL:([\d.]+)/);

  let httpCode = 0;
  let connectSec = 0;      
  let tlsSec = 0;          
  let startSec = 0;        
  let totalSec = 0;        

  if (match) {
    httpCode = parseInt(match[1], 10);
    connectSec = parseFloat(match[2]) || 0;
    tlsSec = parseFloat(match[3]) || 0;
    startSec = parseFloat(match[4]) || 0;
    totalSec = parseFloat(match[5]) || 0;
  }

  // Converte tudo para ms (o K6 normalmente trabalha em ms)
  const connectMs = connectSec * 1000;
  const tlsMs = tlsSec * 1000;
  const startMs = startSec * 1000;
  const totalMs = totalSec * 1000;
  const blockedMs = 0;  
  const tcpMs = connectMs;  
  const tlsHandshakeMs = tlsMs > tcpMs ? (tlsMs - tcpMs) : 0;
  const sendingMs = 0;
  const waitingMs = startMs > tlsMs ? (startMs - tlsMs) : 0;
  const receivingMs = totalMs > startMs ? (totalMs - startMs) : 0;

  // Monta tags de requisição
  const tags = getDefaultTags(httpCode);

  // Popula as métricas
  http_req_blocked.add(blockedMs, tags);
  http_req_connecting.add(tcpMs, tags);
  http_req_tls_handshaking.add(tlsHandshakeMs, tags);
  http_req_sending.add(sendingMs, tags);
  http_req_waiting.add(waitingMs, tags);
  http_req_receiving.add(receivingMs, tags);
  http_req_duration.add(totalMs, tags);

  // Checa se retornou HTTP 201 = Created
  const success = httpCode === 201;
  check(success, { 'POST status is 201': (ok) => ok });

  // Atualiza a taxa de falhas
  if (!success) {
    http_req_failed.add(1, tags);
  }

  // Pequeno intervalo entre requisições
  sleep(1);
}
