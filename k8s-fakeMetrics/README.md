# k8s-fakeMetrics

Gerador de métricas sintéticas de Kubernetes inspirado no projeto [Grafana fake-metrics-generator](https://github.com/grafana/fake-metrics-generator). O objetivo é fornecer um endpoint Prometheus repleto de métricas realistas de clusters, nós, pods e componentes do control plane para montar painéis de observabilidade sem necessidade de um cluster real.

## Funcionalidades

- Simulação de múltiplos clusters Kubernetes, cada um com nós, namespaces, deployments, daemonsets, ingress controllers e pods.
- Métricas detalhadas de utilização de recursos (CPU, memória, filesystem, rede) tanto para nós quanto para containers.
- Métricas lógicas de estado (kube-state-metrics) como fases de pods, réplicas de deployments e condições de nós.
- Métricas do control plane (apiserver, scheduler, controller-manager) incluindo histogramas de latência.
- Métricas de ingress controllers (NGINX e opcionalmente Traefik) com contadores e histogramas.
- Exportação via endpoint HTTP `/metrics` compatível com Prometheus.
- Catálogo dinâmico de métricas carregado de `metric-label.json`, permitindo simular todas as séries usadas em dashboards reais.
- Fator *chaos* configurado para gerar anomalias esporádicas de CPU, memória, tráfego de rede, disco e conexões.

## Requisitos

- Python 3.10+
- Dependências listadas em `requirements.txt`

Instale os requisitos com:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

As principais opções são definidas via variáveis de ambiente. Utilize o arquivo `.env.example` como base:

```bash
cp .env.example .env
```

Variáveis suportadas:

| Variável | Descrição | Valor padrão |
| --- | --- | --- |
| `CLUSTER_COUNT` | Número de clusters simulados | `1` |
| `NODES_PER_CLUSTER` | Nós por cluster | `3` |
| `PODS_PER_NODE` | Pods por nó | `8` |
| `UPDATE_INTERVAL_SECONDS` | Intervalo entre atualizações | `5` |
| `METRICS_PORT` | Porta do endpoint HTTP | `8000` |
| `METRICS_HOST` | Host/interface do endpoint | `0.0.0.0` |
| `NAMESPACES_PER_CLUSTER` | Quantidade de namespaces aleatórios por cluster | `4` |
| `CONTAINERS_PER_POD_MIN`/`CONTAINERS_PER_POD_MAX` | Faixa de containers por pod | `1`/`3` |
| `DEPLOYMENTS_PER_NAMESPACE` | Deployments simulados por namespace | `2` |
| `ENABLE_INGRESS_CONTROLLERS` | Habilita métricas de ingress | `true` |
| `ENABLE_TRAEFIK_METRICS` | Emite métricas de Traefik além do NGINX | `false` |
| `RANDOM_SEED` | Seed opcional para reprodutibilidade | `None` |
| `LOG_LEVEL` | Nível de log da aplicação | `INFO` |

Também é possível sobrescrever as principais opções pela linha de comando (veja `python -m k8s_fake_metrics --help`).

## Execução

Após configurar o ambiente virtual e o `.env`, execute:

```bash
python -m k8s_fake_metrics
```

Por padrão o servidor ficará disponível em `http://localhost:8000/metrics`. Para testes rápidos é possível rodar apenas um ciclo de atualização:

```bash
python -m k8s_fake_metrics --once
```

## Métricas geradas

A lista a seguir descreve as principais famílias de métricas disponíveis:

### Métricas de nós (cAdvisor / kubelet)

- `node_cpu_seconds_total{cluster,node,mode}`
- `node_memory_MemAvailable_bytes{cluster,node}` e `node_memory_MemTotal_bytes{cluster,node}`
- `node_filesystem_{size,free,avail}_bytes{cluster,node,mountpoint,device}`
- `node_network_{receive,transmit}_bytes_total{cluster,node,interface}`
- `node_disk_{read,written}_bytes_total{cluster,node,device}`
- `node_hwmon_temp_celsius{cluster,node,sensor}`

### Métricas de containers/pods

- `container_cpu_usage_seconds_total{cluster,namespace,pod,container}`
- `container_memory_usage_bytes{...}`
- `container_fs_usage_bytes{...}`
- `container_network_{receive,transmit}_bytes_total{...}`
- `kube_pod_status_phase{cluster,namespace,pod,phase}`
- `kube_pod_container_status_{restarts_total,ready}{...}`
- `kubelet_volume_stats_{capacity,used}_bytes{cluster,namespace,pod,volume}`

### kube-state-metrics

- `kube_deployment_status_replicas{cluster,namespace,deployment,condition}`
- `kube_daemonset_status_number_available{cluster,namespace,daemonset}`
- `kube_node_status_condition{cluster,node,condition,status}`
- `kube_node_status_capacity_{cpu_cores,memory_bytes}{cluster,node}`
- `kube_namespace_status_phase{cluster,namespace,phase}`
- `kube_resourcequota_usage_{cpu_cores,memory_bytes}{cluster,namespace,quota}`

### Control plane

- `apiserver_request_total{cluster,verb,resource,code}` + `apiserver_request_duration_seconds{...}` (histograma)
- `rest_client_requests_total{cluster,component,code}`
- `scheduler_schedule_attempts_total{cluster,result}`
- `scheduler_e2e_scheduling_duration_seconds{cluster}` (histograma)
- `controller_runtime_reconcile_total{cluster,controller,result}`

### Ingress controllers

- `nginx_ingress_controller_requests{cluster,namespace,ingress,status}`
- `nginx_ingress_controller_upstream_latency_seconds{cluster,namespace,ingress}` (histograma)
- `traefik_backend_requests_total{cluster,service,code}` (quando habilitado)

A combinação dessas métricas cobre dashboards de infraestrutura (CPU, memória, disco, rede), estado lógico (réplicas, condições, reinícios) e componentes de tráfego.

## Desenvolvimento

- Execute `python -m k8s_fake_metrics --once` para validar rapidamente a geração de métricas.
- Para garantir que o código está sintaticamente correto utilize `python -m compileall k8s_fake_metrics`.
- Ajuste o arquivo `metric-label.json` para incluir novas métricas no catálogo dinâmico ou remover séries específicas.
- Utilize as variáveis de ambiente padrão em conjunto com o fator *chaos* embutido para observar como dashboards reagem a picos súbitos.

Contribuições são bem-vindas!
