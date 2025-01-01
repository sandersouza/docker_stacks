import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  // Adicione a tag testid
  tags: {
    testid: 'openquiz_create_http',
  },
  // Ignora a validação do certificado
  insecureSkipTLSVerify: true,

  vus: 20,          // 20 usuários virtuais
  duration: '5m',   // duração de 5 minutos
};

export default function () {
  const url = 'https://localhost:4433/quizzes/';
  const headers = {
    'Content-Type': 'application/json',
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'K6 Load Test',
    'Connection': 'keep-alive',
    // Substitua o token abaixo pelo seu token válido
    'Authorization': 'Bearer f575e88935ac5bfeaf7047d1d90da343a20fb16822abe5d0188369b91e09efdf',
  };

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

  // Faz a requisição POST para criar o recurso
  const res = http.post(url, payload, { headers });

  // Verifica se o status da resposta é 2002
  check(res, {
    'POST status is 200': (r) => r.status === 200,
  });

  sleep(1);
}
