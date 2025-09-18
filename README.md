![Descrição da Imagem](banner.png)
# Performance & Stress Testing Stacks 🚀

Este repositório é o point central para quem quer explorar, comparar e testar performance de diferentes databases e ferramentas
de stress testing. Tudo isso organizado em stacks simples e prontas para uso. Quer brincar com **MySQL**, **MongoDB**, ou até me
smo explorar o **RedisInsight**? Tá aqui! Curte um stress test com **k6 + Grafana**? Tá aqui também! E o melhor: mais stacks est
ão a caminho, então fique ligado.

Dentro de cada stack há um arquivo **README.md**, contendo as instruções de uso. Existem alguns scripts para gerar carga de dado
s, e medir o tempo dessas cargas. A stack k6_grafana está sendo preparada para medir os detalhes de cada um desses bancos; por
enquanto ela está desenhada para medir performance de sites, webservices, APIs e outros.

Agora o repositório também conta com uma stack de observabilidade completa com Grafana, Prometheus, Loki e o **Fake Metrics Generator**,
perfeita para simular um parque de servidores e preparar integrações com soluções de IA.

### Estrutura atual do repositório 📂
```plaintext
.
├── database
│   ├── mongodb
│   ├── mysql
│   └── redisinsight
├── grafana
│   └── observability
└── stresstest
    ├── k6_grafana
    └── tsdb_exporter
```

---

🎉 Aproveite, divirta-se e compartilhe suas ideias!
