"""Core logic responsible for synthesising Kubernetes metrics."""

from __future__ import annotations

import itertools
import logging
import random
import string
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

from prometheus_client import CollectorRegistry, start_http_server

from .config import Config
from .dynamic_metrics import ChaosEngine, DynamicMetricRegistry
from .ksm_labels import KubeStateMetricLabelProvider
from .entities import (
    CertificateSigningRequestState,
    ClusterState,
    ConfigMapState,
    ContainerState,
    CronJobState,
    DaemonSetState,
    DeploymentState,
    EndpointState,
    HorizontalPodAutoscalerState,
    IngressState,
    JobState,
    LeaseState,
    LimitRangeState,
    NetworkPolicyState,
    NODE_CONDITIONS,
    POD_PHASES,
    KubeStateScrapeTarget,
    PersistentVolumeClaimState,
    PersistentVolumeState,
    PodDisruptionBudgetState,
    PodState,
    ReplicaSetState,
    ReplicationControllerState,
    ResourceQuotaState,
    SecretState,
    ServiceState,
    StatefulSetState,
    StorageClassState,
    VerticalPodAutoscalerState,
    VolumeAttachmentState,
    WebhookConfigurationState,
    NodeState,
)
from .metrics import MetricSet

logger = logging.getLogger(__name__)

NAMESPACE_POOL: Sequence[str] = (
    "kube-system",
    "default",
    "observability",
    "payments",
    "frontend",
    "backend",
    "dev",
    "qa",
    "data",
    "messaging",
)

QOS_CLASSES: Sequence[str] = ("Guaranteed", "Burstable", "BestEffort")
CONTAINER_NAMES: Sequence[str] = (
    "istio-proxy",
    "app",
    "sidecar",
    "collector",
    "init",
    "adapter",
    "service",
)
NETWORK_INTERFACES: Sequence[str] = ("eth0", "eth1")
NODE_DISK_DEVICES: Sequence[str] = ("sda", "sdb")
NODE_SENSORS: Sequence[str] = ("cpu", "chassis")
KSM_CONTAINER_CHOICES: Sequence[str] = ("kube-state-metrics", "kube-rbac-proxy-main")
KSM_ENDPOINT_CHOICES: Sequence[str] = ("https-main", "https", "https-metrics")
KSM_NAMESPACE_CHOICES: Sequence[str] = (
    "kube-system",
    "monitoring",
    "observability",
    "openshift-monitoring",
)
NODE_KERNEL_VERSIONS: Sequence[str] = (
    "5.14.0-427.50.1.el9_4.x86_64",
    "5.10.0-60.54.0.el7.x86_64",
    "5.15.0-1057-azure",
)
NODE_OS_IMAGES: Sequence[str] = (
    "Red Hat Enterprise Linux CoreOS 416.94.202501270445-0",
    "Ubuntu 22.04.4 LTS",
    "Flatcar Container Linux by Kinvolk 3510.2.1",
)
NODE_CONTAINER_RUNTIMES: Sequence[str] = (
    "cri-o://1.29.1",
    "containerd://1.6.24",
    "docker://24.0.2",
)
NODE_KUBE_VERSIONS: Sequence[str] = (
    "v1.29.3",
    "v1.28.6",
    "v1.27.10",
)

APISERVER_VERBS: Sequence[str] = ("GET", "LIST", "WATCH", "CREATE", "PATCH", "DELETE")
APISERVER_RESOURCES: Sequence[str] = (
    "pods",
    "deployments",
    "nodes",
    "services",
    "events",
    "namespaces",
)
HTTP_STATUS_CODES: Sequence[str] = ("200", "201", "202", "400", "404", "429", "500")
SCHEDULER_RESULTS: Sequence[str] = ("scheduled", "error", "unschedulable")
CONTROLLER_RESULTS: Sequence[str] = ("success", "error", "requeue")

VOLUME_NAMES: Sequence[str] = ("config", "cache", "logs", "data")


class FakeMetricsGenerator:
    """Generate synthetic Prometheus metrics representing Kubernetes activity."""

    def __init__(self, config: Config, registry: CollectorRegistry | None = None) -> None:
        self.config = config
        self.registry = registry or CollectorRegistry()
        self.metrics = MetricSet(self.registry)
        self.random = random.Random(config.random_seed)
        self.clusters: List[ClusterState] = []
        self.chaos = ChaosEngine(self.random)
        self._create_environment()
        metric_file = Path(__file__).resolve().parent.parent / "metric-label.json"
        existing_metric_names = self._collect_registered_metric_names()
        label_provider = self._build_label_provider()
        self.dynamic_metrics = DynamicMetricRegistry(
            registry=self.registry,
            rng=self.random,
            metrics_file=metric_file,
            excluded_names=sorted(existing_metric_names),
            label_provider=label_provider,
        )

    # ------------------------------------------------------------------
    # Environment construction
    # ------------------------------------------------------------------
    def _create_environment(self) -> None:
        for cluster_index in range(self.config.cluster_count):
            cluster_name = f"cluster-{cluster_index + 1}"
            namespaces = self._select_namespaces()
            nodes = self._create_nodes(cluster_name)
            kube_state_target = self._create_kube_state_target(cluster_name)
            deployments = self._create_deployments(cluster_name, namespaces)
            daemonsets = self._create_daemonsets(cluster_name, namespaces, nodes)
            ingresses = self._create_ingresses(cluster_name, namespaces)
            cronjobs = self._create_cronjobs(cluster_name, namespaces)
            jobs = self._create_jobs(cluster_name, namespaces, cronjobs)
            statefulsets = self._create_statefulsets(cluster_name, namespaces)
            replicasets = self._create_replicasets(deployments)
            replicationcontrollers = self._create_replicationcontrollers(cluster_name, namespaces)
            hpas = self._create_horizontalpodautoscalers(cluster_name, deployments)
            networkpolicies = self._create_networkpolicies(namespaces)
            configmaps = self._create_configmaps(namespaces)
            secrets = self._create_secrets(namespaces)
            services = self._create_services(cluster_name, namespaces)
            endpoints = self._create_endpoints(services)
            persistentvolumes = self._create_persistentvolumes(cluster_name, namespaces)
            persistentvolumeclaims = self._create_persistentvolumeclaims(cluster_name, namespaces)
            pod_budgets = self._create_pod_disruption_budgets(namespaces)
            resourcequotas = self._create_resourcequotas(cluster_name, namespaces)
            leases = self._create_leases(namespaces)
            limitranges = self._create_limitranges(namespaces)
            mutating_webhooks, validating_webhooks = self._create_webhook_configurations(cluster_name)
            storageclasses = self._create_storageclasses(cluster_name)
            vertical_pod_autoscalers = self._create_vertical_pod_autoscalers(namespaces)
            volume_attachments = self._create_volume_attachments(persistentvolumes, nodes)
            certificate_signing_requests = self._create_certificate_signing_requests(cluster_name)
            cluster = ClusterState(
                name=cluster_name,
                namespaces=namespaces,
                nodes=nodes,
                deployments=deployments,
                daemonsets=daemonsets,
                ingresses=ingresses,
                cronjobs=cronjobs,
                jobs=jobs,
                statefulsets=statefulsets,
                replicasets=replicasets,
                replicationcontrollers=replicationcontrollers,
                horizontalpodautoscalers=hpas,
                networkpolicies=networkpolicies,
                configmaps=configmaps,
                secrets=secrets,
                services=services,
                endpoints=endpoints,
                persistentvolumes=persistentvolumes,
                persistentvolumeclaims=persistentvolumeclaims,
                pod_disruption_budgets=pod_budgets,
                resourcequotas=resourcequotas,
                leases=leases,
                limitranges=limitranges,
                mutating_webhooks=mutating_webhooks,
                validating_webhooks=validating_webhooks,
                storageclasses=storageclasses,
                vertical_pod_autoscalers=vertical_pod_autoscalers,
                volume_attachments=volume_attachments,
                certificate_signing_requests=certificate_signing_requests,
                kube_state_target=kube_state_target,
            )
            self._populate_pods(cluster)
            self.clusters.append(cluster)
            logger.debug("Created cluster %s with %s nodes", cluster.name, len(cluster.nodes))

    def _select_namespaces(self) -> List[str]:
        namespaces = set(["kube-system", "default"])
        available = [ns for ns in NAMESPACE_POOL if ns not in namespaces]
        while len(namespaces) < max(self.config.namespaces_per_cluster, 2):
            namespaces.add(self.random.choice(available))
        return sorted(namespaces)

    def _create_kube_state_target(self, cluster_name: str) -> KubeStateScrapeTarget:
        namespace = self.random.choice(KSM_NAMESPACE_CHOICES)
        service = "kube-state-metrics"
        suffix = "".join(
            self.random.choices(string.ascii_lowercase + string.digits, k=5)
        )
        pod = f"kube-state-metrics-{suffix}"
        container = self.random.choice(KSM_CONTAINER_CHOICES)
        endpoint = self.random.choice(KSM_ENDPOINT_CHOICES)
        job = "kube-state-metrics"
        prometheus = f"{cluster_name}/k8s"
        return KubeStateScrapeTarget(
            namespace=namespace,
            service=service,
            pod=pod,
            container=container,
            endpoint=endpoint,
            job=job,
            prometheus=prometheus,
        )

    def _create_nodes(self, cluster_name: str) -> List[NodeState]:
        nodes: List[NodeState] = []
        for node_index in range(self.config.nodes_per_cluster):
            cpu = self.random.choice([4, 8, 16])
            memory_gib = self.random.uniform(8, 64)
            storage_gib = self.random.uniform(100, 500)
            name = f"{cluster_name}-node-{node_index + 1}"
            region = self.random.choice(["us-east-1", "us-west-2", "eu-central-1"])
            zone = f"{region}{self.random.choice(['a', 'b', 'c'])}"
            role = "control-plane" if node_index == 0 else "worker"
            ip_address = f"10.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}"
            instance_type = self.random.choice(["c5.large", "m5.xlarge", "t3.medium"])
            node_labels = {
                "beta.kubernetes.io/arch": "amd64",
                "beta.kubernetes.io/os": "linux",
                "topology.kubernetes.io/region": region,
                "topology.kubernetes.io/zone": zone,
                "kubernetes.io/hostname": name,
                "kubernetes.io/os": "linux",
                "node.kubernetes.io/instance-type": instance_type,
                "node.openshift.io/os_id": self.random.choice(["rhcos", "ubuntu", "flatcar"]),
                "cluster_scanner": "true",
                "dynatrace": self.random.choice(["infra", "app", "router"]),
            }
            if role == "control-plane":
                node_labels["node-role.kubernetes.io/control-plane"] = "true"
            else:
                node_labels["node-role.kubernetes.io/worker"] = "true"
            speciality = self.random.choice(["worker", "infra", "router"])
            node_labels["type"] = speciality
            system_uuid_raw = "".join(self.random.choices("0123456789abcdef", k=32))
            system_uuid = (
                f"{system_uuid_raw[0:8]}-"
                f"{system_uuid_raw[8:12]}-"
                f"{system_uuid_raw[12:16]}-"
                f"{system_uuid_raw[16:20]}-"
                f"{system_uuid_raw[20:32]}"
            )
            node = NodeState(
                name=name,
                cluster=cluster_name,
                cpu_cores=cpu,
                memory_bytes=memory_gib * 1024**3,
                ephemeral_storage_bytes=storage_gib * 1024**3,
                labels=node_labels,
                roles=[role] if role != "worker" else ["worker"],
                taints=[("node-role.kubernetes.io/control-plane", "true", "NoSchedule")] if role == "control-plane" else [],
                addresses=[("InternalIP", ip_address), ("Hostname", name)],
                allocatable_cpu_cores=max(cpu - self.random.uniform(0.5, 1.5), 1.0),
                allocatable_memory_bytes=memory_gib * 1024**3 * self.random.uniform(0.7, 0.95),
                capacity_pods=self.random.randint(80, 120),
                allocatable_pods=self.random.randint(60, 110),
                kernel_version=self.random.choice(NODE_KERNEL_VERSIONS),
                os_image=self.random.choice(NODE_OS_IMAGES),
                container_runtime_version=self.random.choice(NODE_CONTAINER_RUNTIMES),
                kubelet_version=self.random.choice(NODE_KUBE_VERSIONS),
                kubeproxy_version=self.random.choice(NODE_KUBE_VERSIONS),
                system_uuid=system_uuid,
                internal_ip=ip_address,
            )
            nodes.append(node)
        return nodes

    def _create_deployments(self, cluster_name: str, namespaces: Sequence[str]) -> List[DeploymentState]:
        deployments: List[DeploymentState] = []
        for namespace in namespaces:
            for index in range(self.config.deployments_per_namespace):
                desired = self.random.randint(2, max(self.config.pods_per_node, 2))
                deployments.append(
                    DeploymentState(
                        name=f"{namespace}-deploy-{index + 1}",
                        namespace=namespace,
                        desired_replicas=desired,
                        updated_replicas=desired,
                        ready_replicas=desired,
                        available_replicas=desired,
                    )
                )
        return deployments

    def _create_daemonsets(
        self, cluster_name: str, namespaces: Sequence[str], nodes: Sequence[NodeState]
    ) -> List[DaemonSetState]:
        daemonsets: List[DaemonSetState] = []
        for namespace in namespaces:
            if namespace == "default":
                continue
            if self.random.random() < 0.5:
                name = f"{namespace}-ds"
                daemonsets.append(
                    DaemonSetState(
                        name=name,
                        namespace=namespace,
                        desired_number_scheduled=len(nodes),
                        number_available=len(nodes),
                    )
                )
        if not daemonsets:
            daemonsets.append(
                DaemonSetState(
                    name=f"{cluster_name}-node-exporter",
                    namespace="kube-system",
                    desired_number_scheduled=len(nodes),
                    number_available=len(nodes),
                )
            )
        return daemonsets

    def _create_ingresses(self, cluster_name: str, namespaces: Sequence[str]) -> List[IngressState]:
        ingresses: List[IngressState] = []
        if not self.config.enable_ingress_controllers:
            return ingresses
        for namespace in namespaces:
            if namespace in {"kube-system", "default"}:
                continue
            if self.random.random() < 0.4:
                controller = "nginx"
                if self.config.enable_traefik_metrics and self.random.random() < 0.3:
                    controller = "traefik"
                ingresses.append(
                    IngressState(
                        name=f"{namespace}-ingress",
                        namespace=namespace,
                        controller=controller,
                    )
                )
        if not ingresses:
            ingresses.append(
                IngressState(name=f"{cluster_name}-ingress", namespace="default", controller="nginx")
            )
        return ingresses

    def _create_cronjobs(self, cluster_name: str, namespaces: Sequence[str]) -> List[CronJobState]:
        cronjobs: List[CronJobState] = []
        for namespace in namespaces:
            if namespace == "kube-system" and self.random.random() < 0.3:
                continue
            count = max(1, self.random.randint(1, 2))
            for index in range(count):
                name = f"{namespace}-cronjob-{index + 1}"
                schedule = f"*/{self.random.randint(5, 30)} * * * *"
                suspend = self.random.random() < 0.1
                starting_deadline = self.random.choice([None, self.random.randint(30, 300)])
                successful_limit = self.random.randint(1, 5)
                failed_limit = self.random.randint(1, 5)
                now = time.time() - self.random.uniform(60.0, 3600.0)
                last_success = now - self.random.uniform(0.0, 1800.0)
                cronjobs.append(
                    CronJobState(
                        name=name,
                        namespace=namespace,
                        schedule=schedule,
                        suspend=suspend,
                        starting_deadline_seconds=starting_deadline,
                        successful_job_history_limit=successful_limit,
                        failed_job_history_limit=failed_limit,
                        next_schedule_time=now + self.random.uniform(60.0, 600.0),
                        last_schedule_time=now,
                        last_successful_time=max(last_success, 0.0),
                        active_jobs=self.random.randint(0, 2),
                    )
                )
        return cronjobs

    def _create_jobs(
        self, cluster_name: str, namespaces: Sequence[str], cronjobs: Sequence[CronJobState]
    ) -> List[JobState]:
        jobs: List[JobState] = []
        for cronjob in cronjobs:
            job_name = f"{cronjob.name}-job"
            start = time.time() - self.random.uniform(120.0, 7200.0)
            completion = start + self.random.uniform(30.0, 900.0)
            parallelism = self.random.randint(1, 3)
            succeeded = self.random.randint(0, parallelism)
            failed = self.random.randint(0, max(parallelism - succeeded, 1)) if succeeded < parallelism else 0
            active = max(parallelism - succeeded - failed, 0)
            jobs.append(
                JobState(
                    name=job_name,
                    namespace=cronjob.namespace,
                    completions=self.random.choice([None, parallelism]),
                    parallelism=parallelism,
                    active_deadline_seconds=self.random.choice([None, self.random.randint(300, 1800)]),
                    start_time=start,
                    completion_time=completion,
                    succeeded=succeeded,
                    failed=failed,
                    active=active,
                    owner_name=cronjob.name,
                )
            )
        # add standalone jobs per namespace
        for namespace in namespaces:
            if namespace == "kube-system" and self.random.random() < 0.5:
                continue
            name = f"{namespace}-job"
            start = time.time() - self.random.uniform(60.0, 3600.0)
            completion = start + self.random.uniform(15.0, 600.0)
            jobs.append(
                JobState(
                    name=name,
                    namespace=namespace,
                    completions=self.random.randint(1, 5),
                    parallelism=self.random.randint(1, 3),
                    active_deadline_seconds=None,
                    start_time=start,
                    completion_time=completion,
                    succeeded=self.random.randint(0, 3),
                    failed=self.random.randint(0, 2),
                    active=self.random.randint(0, 2),
                    owner_kind="Deployment",
                    owner_name=f"{namespace}-deploy-1",
                )
            )
        return jobs

    def _create_statefulsets(self, cluster_name: str, namespaces: Sequence[str]) -> List[StatefulSetState]:
        statefulsets: List[StatefulSetState] = []
        for namespace in namespaces:
            if namespace == "kube-system" and self.random.random() < 0.6:
                continue
            name = f"{namespace}-statefulset"
            replicas = self.random.randint(1, 5)
            ready = self.random.randint(0, replicas)
            current_revision = f"{name}-rev-{self.random.randint(1, 5)}"
            update_revision = f"{name}-rev-{self.random.randint(6, 10)}"
            statefulsets.append(
                StatefulSetState(
                    name=name,
                    namespace=namespace,
                    replicas=replicas,
                    ready_replicas=ready,
                    current_replicas=max(ready - self.random.randint(0, 1), 0),
                    updated_replicas=max(ready - self.random.randint(0, 1), 0),
                    current_revision=current_revision,
                    update_revision=update_revision,
                    observed_generation=self.random.randint(1, 5),
                    pvc_retention_policy=self.random.choice(["Delete", "Retain"]),
                )
            )
        return statefulsets

    def _create_replicasets(self, deployments: Sequence[DeploymentState]) -> List[ReplicaSetState]:
        replicasets: List[ReplicaSetState] = []
        for deployment in deployments:
            rs_name = f"{deployment.name}-rs"
            desired = deployment.desired_replicas
            ready = max(deployment.ready_replicas + self.random.randint(-1, 1), 0)
            fully_labeled = max(min(ready, desired), 0)
            replicasets.append(
                ReplicaSetState(
                    name=rs_name,
                    namespace=deployment.namespace,
                    desired_replicas=desired,
                    ready_replicas=ready,
                    fully_labeled_replicas=fully_labeled,
                    observed_generation=self.random.randint(1, 5),
                    owner_name=deployment.name,
                )
            )
        return replicasets

    def _create_replicationcontrollers(
        self, cluster_name: str, namespaces: Sequence[str]
    ) -> List[ReplicationControllerState]:
        controllers: List[ReplicationControllerState] = []
        for namespace in namespaces:
            name = f"{namespace}-rc"
            desired = self.random.randint(1, 4)
            ready = max(desired - self.random.randint(0, 1), 0)
            controllers.append(
                ReplicationControllerState(
                    name=name,
                    namespace=namespace,
                    desired_replicas=desired,
                    ready_replicas=ready,
                    fully_labeled_replicas=max(ready - 1, 0),
                    available_replicas=ready,
                    observed_generation=self.random.randint(1, 4),
                    owner_kind="Deployment",
                    owner_name=f"{namespace}-deploy-1",
                )
            )
        return controllers

    def _create_horizontalpodautoscalers(
        self, cluster_name: str, deployments: Sequence[DeploymentState]
    ) -> List[HorizontalPodAutoscalerState]:
        hpas: List[HorizontalPodAutoscalerState] = []
        for deployment in deployments:
            if self.random.random() < 0.5:
                continue
            min_replicas = max(1, deployment.desired_replicas // 2)
            max_replicas = max(min_replicas + self.random.randint(1, 5), deployment.desired_replicas)
            current = deployment.ready_replicas
            desired = max(min(current + self.random.randint(-1, 1), max_replicas), min_replicas)
            conditions = (
                ("AbleToScale", self.random.choice(["True", "False"])),
                ("ScalingActive", self.random.choice(["True", "False"])),
                ("ScalingLimited", self.random.choice(["True", "False"])),
            )
            hpas.append(
                HorizontalPodAutoscalerState(
                    name=f"{deployment.name}-hpa",
                    namespace=deployment.namespace,
                    min_replicas=min_replicas,
                    max_replicas=max_replicas,
                    current_replicas=current,
                    desired_replicas=desired,
                    target_metric=self.random.uniform(0.4, 0.9),
                    target_metric_name=self.random.choice(["cpu", "memory"]),
                    generation=self.random.randint(1, 5),
                    conditions=conditions,
                )
            )
        return hpas

    def _create_networkpolicies(self, namespaces: Sequence[str]) -> List[NetworkPolicyState]:
        policies: List[NetworkPolicyState] = []
        for namespace in namespaces:
            if namespace == "kube-system" and self.random.random() < 0.5:
                continue
            policies.append(
                NetworkPolicyState(
                    name=f"{namespace}-netpol",
                    namespace=namespace,
                    ingress_rules=self.random.randint(0, 5),
                    egress_rules=self.random.randint(0, 5),
                )
            )
        return policies

    def _create_configmaps(self, namespaces: Sequence[str]) -> List[ConfigMapState]:
        configmaps: List[ConfigMapState] = []
        for namespace in namespaces:
            count = self.random.randint(1, 3)
            for index in range(count):
                configmaps.append(ConfigMapState(name=f"{namespace}-config-{index + 1}", namespace=namespace))
        return configmaps

    def _create_secrets(self, namespaces: Sequence[str]) -> List[SecretState]:
        secrets: List[SecretState] = []
        for namespace in namespaces:
            count = self.random.randint(1, 3)
            for index in range(count):
                name = f"{namespace}-secret-{index + 1}"
                secrets.append(
                    SecretState(
                        name=name,
                        namespace=namespace,
                        secret_type=self.random.choice(["Opaque", "kubernetes.io/tls", "kubernetes.io/dockerconfigjson"]),
                        owner_kind="ServiceAccount",
                        owner_name=f"{namespace}-sa",
                    )
                )
        return secrets

    def _create_services(self, cluster_name: str, namespaces: Sequence[str]) -> List[ServiceState]:
        services: List[ServiceState] = []
        for namespace in namespaces:
            cluster_ip = f"10.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}"
            service_type = self.random.choice(["ClusterIP", "NodePort", "LoadBalancer"])
            external_ips: Sequence[str] = ()
            if service_type == "LoadBalancer":
                external_ips = (
                    f"35.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}",
                )
            services.append(
                ServiceState(
                    name=f"{namespace}-service",
                    namespace=namespace,
                    service_type=service_type,
                    cluster_ip=cluster_ip,
                    external_ips=external_ips,
                )
            )
        return services

    def _create_endpoints(self, services: Sequence[ServiceState]) -> List[EndpointState]:
        endpoints: List[EndpointState] = []
        for service in services:
            address_count = self.random.randint(1, 3)
            addresses = [
                f"10.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}"
                for _ in range(address_count)
            ]
            not_ready = addresses[: self.random.randint(0, len(addresses) // 2)]
            ports = [
                (
                    f"port-{index}",
                    8000 + index * 10,
                    self.random.choice(["TCP", "UDP"]),
                )
                for index in range(1, self.random.randint(2, 4))
            ]
            endpoints.append(
                EndpointState(
                    name=f"{service.name}-ep",
                    namespace=service.namespace,
                    addresses=tuple(addresses),
                    not_ready_addresses=tuple(not_ready),
                    ports=tuple(ports),
                )
            )
        return endpoints

    def _create_persistentvolumes(
        self, cluster_name: str, namespaces: Sequence[str]
    ) -> List[PersistentVolumeState]:
        pvs: List[PersistentVolumeState] = []
        for index, namespace in enumerate(namespaces, start=1):
            pv_name = f"{cluster_name}-pv-{index}"
            capacity = self.random.uniform(10, 200) * 1024**3
            claim_name = f"{namespace}-pvc-{index}"
            pvs.append(
                PersistentVolumeState(
                    name=pv_name,
                    capacity_bytes=capacity,
                    storage_class=self.random.choice(["standard", "gold", "fast"]),
                    access_modes=("ReadWriteOnce",),
                    status_phase=self.random.choice(["Bound", "Available", "Released"]),
                    labels={"environment": self.random.choice(["dev", "prod", "qa"])},
                    claim_namespace=namespace,
                    claim_name=claim_name,
                    deletion_timestamp=None,
                )
            )
        return pvs

    def _create_persistentvolumeclaims(
        self, cluster_name: str, namespaces: Sequence[str]
    ) -> List[PersistentVolumeClaimState]:
        pvcs: List[PersistentVolumeClaimState] = []
        for index, namespace in enumerate(namespaces, start=1):
            name = f"{namespace}-pvc-{index}"
            request = self.random.uniform(5, 50) * 1024**3
            pvcs.append(
                PersistentVolumeClaimState(
                    name=name,
                    namespace=namespace,
                    storage_request_bytes=request,
                    access_modes=("ReadWriteOnce",),
                    volume_name=f"{cluster_name}-pv-{index}",
                    status_phase=self.random.choice(["Bound", "Pending", "Lost"]),
                    storage_class=self.random.choice(["standard", "gold", "fast"]),
                    deletion_timestamp=None,
                    labels={"team": self.random.choice(["payments", "observability", "core"])}
                )
            )
        return pvcs

    def _create_pod_disruption_budgets(self, namespaces: Sequence[str]) -> List[PodDisruptionBudgetState]:
        budgets: List[PodDisruptionBudgetState] = []
        for namespace in namespaces:
            total_pods = self.random.randint(3, 15)
            desired_healthy = max(total_pods - self.random.randint(0, 3), 0)
            budgets.append(
                PodDisruptionBudgetState(
                    name=f"{namespace}-pdb",
                    namespace=namespace,
                    current_healthy=max(desired_healthy - self.random.randint(0, 2), 0),
                    desired_healthy=desired_healthy,
                    expected_pods=total_pods,
                    disruptions_allowed=self.random.randint(0, 2),
                    observed_generation=self.random.randint(1, 5),
                    labels={"app": namespace},
                )
            )
        return budgets

    def _create_resourcequotas(self, cluster_name: str, namespaces: Sequence[str]) -> List[ResourceQuotaState]:
        quotas: List[ResourceQuotaState] = []
        for namespace in namespaces:
            cpu_hard = self.random.uniform(2.0, 20.0)
            mem_hard = self.random.uniform(4.0, 64.0) * 1024**3
            quotas.append(
                ResourceQuotaState(
                    name=f"{namespace}-quota",
                    namespace=namespace,
                    resource="cpu",
                    hard=cpu_hard,
                    used=cpu_hard * self.random.uniform(0.3, 0.9),
                )
            )
            quotas.append(
                ResourceQuotaState(
                    name=f"{namespace}-quota",
                    namespace=namespace,
                    resource="memory",
                    hard=mem_hard,
                    used=mem_hard * self.random.uniform(0.3, 0.9),
                )
            )
        return quotas

    def _create_leases(self, namespaces: Sequence[str]) -> List[LeaseState]:
        leases: List[LeaseState] = []
        for namespace in namespaces:
            leases.append(
                LeaseState(
                    name=f"{namespace}-lease",
                    namespace=namespace,
                    renew_time=time.time(),
                    owner=f"{namespace}-controller",
                )
            )
        return leases

    def _create_limitranges(self, namespaces: Sequence[str]) -> List[LimitRangeState]:
        limitranges: List[LimitRangeState] = []
        for namespace in namespaces:
            limitranges.append(
                LimitRangeState(
                    name=f"{namespace}-limits",
                    namespace=namespace,
                    resource="memory",
                    limit_type="Container",
                    min_value=128 * 1024**2,
                    max_value=8 * 1024**3,
                )
            )
        return limitranges

    def _create_webhook_configurations(
        self, cluster_name: str
    ) -> Tuple[List[WebhookConfigurationState], List[WebhookConfigurationState]]:
        mutating = [
            WebhookConfigurationState(
                name=f"{cluster_name}-mutating",
                service_namespace="kube-system",
                service_name="mutating-webhook",
                webhook="webhook.mutate.k8s.io",
            )
        ]
        validating = [
            WebhookConfigurationState(
                name=f"{cluster_name}-validating",
                service_namespace="kube-system",
                service_name="validating-webhook",
                webhook="webhook.validate.k8s.io",
            )
        ]
        return mutating, validating

    def _create_storageclasses(self, cluster_name: str) -> List[StorageClassState]:
        provisioners = ("kubernetes.io/aws-ebs", "kubernetes.io/gce-pd", "csi.trident.netapp.io")
        return [
            StorageClassState(name=f"{cluster_name}-sc-{index}", provisioner=self.random.choice(provisioners))
            for index in range(1, 3)
        ]

    def _create_vertical_pod_autoscalers(self, namespaces: Sequence[str]) -> List[VerticalPodAutoscalerState]:
        vpas: List[VerticalPodAutoscalerState] = []
        for namespace in namespaces:
            if namespace == "kube-system" and self.random.random() < 0.7:
                continue
            container_name = self.random.choice(["app", "worker", "sidecar"])
            target_cpu = self.random.uniform(0.2, 2.0)
            target_memory = self.random.uniform(256, 2048) * 1024**2
            vpas.append(
                VerticalPodAutoscalerState(
                    name=f"{namespace}-vpa",
                    namespace=namespace,
                    container_name=container_name,
                    target_cpu=target_cpu,
                    target_memory_bytes=target_memory,
                    lower_cpu=target_cpu * 0.5,
                    lower_memory_bytes=target_memory * 0.5,
                    upper_cpu=target_cpu * 1.5,
                    upper_memory_bytes=target_memory * 1.5,
                    uncapped_cpu=target_cpu * 1.2,
                    uncapped_memory_bytes=target_memory * 1.2,
                    update_mode=self.random.choice(["Auto", "Off", "Initial"]),
                )
            )
        return vpas

    def _create_volume_attachments(
        self, persistentvolumes: Sequence[PersistentVolumeState], nodes: Sequence[NodeState]
    ) -> List[VolumeAttachmentState]:
        attachments: List[VolumeAttachmentState] = []
        for pv in persistentvolumes:
            node = self.random.choice(nodes)
            metadata = {"device": f"/dev/{self.random.choice(['sda', 'sdb', 'nvme0n1'])}"}
            attachments.append(
                VolumeAttachmentState(
                    name=f"attach-{pv.name}",
                    persistent_volume=pv.name,
                    attached=self.random.random() > 0.1,
                    node=node.name,
                    metadata_entries=metadata,
                )
            )
        return attachments

    def _create_certificate_signing_requests(
        self, cluster_name: str
    ) -> List[CertificateSigningRequestState]:
        csrs: List[CertificateSigningRequestState] = []
        for index in range(1, 3):
            csrs.append(
                CertificateSigningRequestState(
                    name=f"{cluster_name}-csr-{index}",
                    signer_name=self.random.choice([
                        "kubernetes.io/kube-apiserver-client",
                        "kubernetes.io/legacy-unknown",
                    ]),
                    condition=self.random.choice(["Approved", "Denied", "Pending"]),
                    status=self.random.choice(["True", "False"]),
                    cert_length=self.random.randint(1024, 4096),
                )
            )
        return csrs

    def _populate_pods(self, cluster: ClusterState) -> None:
        for node in cluster.nodes:
            pods: List[PodState] = []
            for _ in range(self.config.pods_per_node):
                namespace = self.random.choice(cluster.namespaces)
                deployment = self.random.choice(
                    [d for d in cluster.deployments if d.namespace == namespace]
                )
                pod_name = self._random_pod_name(namespace)
                containers, init_containers = self._create_containers()
                phase = "Running" if self.random.random() > 0.1 else self.random.choice(
                    ["Pending", "Running", "Failed"]
                )
                start_time = time.time() - self.random.uniform(60.0, 7200.0)
                scheduled_time = start_time - self.random.uniform(1.0, 15.0)
                initialized_time = start_time + self.random.uniform(1.0, 30.0)
                ready_time = start_time + self.random.uniform(5.0, 120.0)
                container_ready_time = ready_time + self.random.uniform(1.0, 30.0)
                pod_ip = f"10.{self.random.randint(0, 255)}.{self.random.randint(0, 255)}.{self.random.randint(1, 254)}"
                host_ip = next((addr for typ, addr in node.addresses if typ == "InternalIP"), node.name)
                labels = {
                    "app": deployment.name,
                    "tier": self.random.choice(["frontend", "backend", "batch"]),
                    "version": f"v{self.random.randint(1, 5)}",
                }
                tolerations = [("node.kubernetes.io/not-ready", "NoExecute")]
                pvc_candidates = [pvc for pvc in cluster.persistentvolumeclaims if pvc.namespace == namespace]
                volumes: List[Tuple[str, str, bool]] = []
                if pvc_candidates:
                    pvc = self.random.choice(pvc_candidates)
                    volumes.append(("data", pvc.name, False))
                pod = PodState(
                    name=pod_name,
                    namespace=namespace,
                    node_name=node.name,
                    deployment=deployment.name,
                    containers=containers,
                    phase=phase,
                    qos_class=self.random.choice(QOS_CLASSES),
                    labels=labels,
                    owner_kind="ReplicaSet",
                    owner_name=f"{deployment.name}-rs",
                    service_account=f"{namespace}-sa",
                    scheduler="default-scheduler",
                    start_time=start_time,
                    host_ip=host_ip,
                    pod_ip=pod_ip,
                    pod_ips=[pod_ip, f"fd00::{self.random.randint(1, 65535):x}"],
                    tolerations=tolerations,
                    deletion_timestamp=None,
                    reason="Running" if phase == "Running" else self.random.choice(["CrashLoopBackOff", "ImagePullBackOff", "Completed"]),
                    ready_time=ready_time,
                    initialized_time=initialized_time,
                    scheduled_time=scheduled_time,
                    container_ready_time=container_ready_time,
                    volumes=volumes,
                    init_containers=init_containers,
                )
                pod.update_ready_containers()
                pods.append(pod)
            node.pods = pods

    def _random_pod_name(self, namespace: str) -> str:
        suffix = "".join(self.random.choices(string.ascii_lowercase + string.digits, k=5))
        return f"{namespace}-{suffix}"

    def _create_containers(self) -> Tuple[List[ContainerState], List[ContainerState]]:
        containers: List[ContainerState] = []
        init_containers: List[ContainerState] = []
        min_containers = max(1, self.config.containers_per_pod_min)
        max_containers = max(min_containers, self.config.containers_per_pod_max)
        container_count = self.random.randint(min_containers, max_containers)
        for index in range(container_count):
            name = self.random.choice(CONTAINER_NAMES)
            base_memory_limit_gib = self.random.uniform(0.25, 2.0)
            fs_limit_gib = self.random.uniform(1.0, 10.0)
            containers.append(
                ContainerState(
                    name=f"{name}-{index}",
                    cpu_seconds_total=self.random.uniform(0.0, 1000.0),
                    memory_usage_bytes=base_memory_limit_gib * 1024**3 * self.random.uniform(0.2, 0.9),
                    memory_limit_bytes=base_memory_limit_gib * 1024**3,
                    filesystem_usage_bytes=fs_limit_gib * 1024**3 * self.random.uniform(0.1, 0.8),
                    filesystem_limit_bytes=fs_limit_gib * 1024**3,
                    restarts=self.random.randint(0, 5),
                    network_rx_bytes_total=self.random.uniform(1e6, 5e9),
                    network_tx_bytes_total=self.random.uniform(1e6, 5e9),
                    image=f"registry.example.com/{name}:v{self.random.randint(1, 5)}",
                    request_cpu_cores=self.random.uniform(0.1, 0.5),
                    request_memory_bytes=base_memory_limit_gib * 1024**3 * self.random.uniform(0.2, 0.6),
                    limit_cpu_cores=self.random.uniform(0.5, 2.0),
                    last_terminated_reason=self.random.choice(["Completed", "OOMKilled", "Error", ""]),
                    last_terminated_exit_code=self.random.randint(0, 137),
                    last_terminated_timestamp=time.time() - self.random.uniform(0.0, 3600.0),
                    waiting_reason=self.random.choice(["CrashLoopBackOff", "ContainerCreating", ""]),
                    started_at=time.time() - self.random.uniform(0.0, 7200.0),
                )
            )
        init_count = self.random.randint(0, 2)
        for index in range(init_count):
            name = f"init-{index}"
            memory_limit = self.random.uniform(0.1, 0.5)
            init_containers.append(
                ContainerState(
                    name=name,
                    cpu_seconds_total=self.random.uniform(0.0, 100.0),
                    memory_usage_bytes=memory_limit * 1024**3 * self.random.uniform(0.1, 0.6),
                    memory_limit_bytes=memory_limit * 1024**3,
                    filesystem_usage_bytes=self.random.uniform(0.0, 1.0) * 1024**3,
                    filesystem_limit_bytes=1.0 * 1024**3,
                    restarts=self.random.randint(0, 2),
                    network_rx_bytes_total=self.random.uniform(1e4, 1e6),
                    network_tx_bytes_total=self.random.uniform(1e4, 1e6),
                    image=f"registry.example.com/{name}:v{self.random.randint(1, 3)}",
                    request_cpu_cores=self.random.uniform(0.05, 0.2),
                    request_memory_bytes=memory_limit * 1024**3 * self.random.uniform(0.2, 0.5),
                    limit_cpu_cores=self.random.uniform(0.1, 0.5),
                    last_terminated_reason="Completed",
                    last_terminated_exit_code=0,
                    last_terminated_timestamp=time.time() - self.random.uniform(0.0, 3600.0),
                    waiting_reason="",
                    started_at=time.time() - self.random.uniform(0.0, 7200.0),
                )
            )
        return containers, init_containers

    # ------------------------------------------------------------------
    # Metrics update loop
    # ------------------------------------------------------------------
    def run(self, iterations: int | None = None) -> None:
        logger.info(
            "Starting fake metrics generator for %s clusters (port %s)",
            self.config.cluster_count,
            self.config.metrics_port,
        )
        start_http_server(self.config.metrics_port, addr=self.config.metrics_host, registry=self.registry)
        loop = itertools.count() if iterations is None else range(iterations)
        for iteration in loop:
            start = time.time()
            logger.debug("Updating metrics iteration %s", iteration)
            self.update_metrics()
            elapsed = time.time() - start
            sleep_time = max(self.config.update_interval_seconds - elapsed, 0.0)
            if iterations is None:
                time.sleep(sleep_time)
            else:
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def update_metrics(self) -> None:
        for cluster in self.clusters:
            self._update_cluster_metrics(cluster)
        self.dynamic_metrics.update_all(self.chaos)

    # ------------------------------------------------------------------
    # Cluster metric updates
    # ------------------------------------------------------------------
    def _update_cluster_metrics(self, cluster: ClusterState) -> None:
        self._update_namespace_metrics(cluster)
        self._update_node_metrics(cluster)
        self._update_pod_metrics(cluster)
        self._update_deployment_metrics(cluster)
        self._update_daemonset_metrics(cluster)
        self._update_control_plane_metrics(cluster)
        if self.config.enable_ingress_controllers:
            self._update_ingress_metrics(cluster)

    def _collect_registered_metric_names(self) -> Set[str]:
        names: Set[str] = set()
        for metric in vars(self.metrics).values():
            metric_name = getattr(metric, "_name", None)
            metric_type = getattr(metric, "_type", None)
            if metric_name is None:
                continue
            if metric_type == "counter":
                if not metric_name.endswith("_total"):
                    metric_name = f"{metric_name}_total"
                names.add(metric_name)
            elif metric_type == "histogram":
                names.add(f"{metric_name}_bucket")
                names.add(f"{metric_name}_count")
                names.add(f"{metric_name}_sum")
            else:
                names.add(metric_name)
        return names

    def _build_label_provider(self) -> KubeStateMetricLabelProvider:
        return KubeStateMetricLabelProvider(self.clusters, self.random)

    def _update_namespace_metrics(self, cluster: ClusterState) -> None:
        for namespace in cluster.namespaces:
            phase = "Active" if self.random.random() > 0.05 else "Terminating"
            self.metrics.kube_namespace_status_phase.labels(
                cluster=cluster.name, namespace=namespace, phase="Active"
            ).set(1 if phase == "Active" else 0)
            self.metrics.kube_namespace_status_phase.labels(
                cluster=cluster.name, namespace=namespace, phase="Terminating"
            ).set(1 if phase == "Terminating" else 0)
            quota_name = f"{namespace}-quota"
            cpu_used = self.random.uniform(0.1, 0.9) * len(cluster.nodes) * 2
            mem_used = self.random.uniform(0.1, 0.9) * len(cluster.nodes) * 4 * 1024**3
            self.metrics.cluster_resource_quota_cpu.labels(
                cluster=cluster.name, namespace=namespace, quota=quota_name
            ).set(cpu_used)
            self.metrics.cluster_resource_quota_memory.labels(
                cluster=cluster.name, namespace=namespace, quota=quota_name
            ).set(mem_used)

    def _update_node_metrics(self, cluster: ClusterState) -> None:
        target = cluster.kube_state_target
        base_labels = {
            "cluster": cluster.name,
            "namespace": target.namespace,
            "service": target.service,
            "pod": target.pod,
            "container": target.container,
            "job": target.job,
            "endpoint": target.endpoint,
            "prometheus": target.prometheus,
        }
        for node in cluster.nodes:
            node_labelset = {**base_labels, "node": node.name}
            for mode in node.cpu_modes_seconds:
                delta = self.random.uniform(0.5, 5.0) * self.config.update_interval_seconds
                node.cpu_modes_seconds[mode] += delta
                self.metrics.node_cpu_seconds_total.labels(
                    cluster=cluster.name, node=node.name, mode=mode
                ).inc(delta)
            total_memory = node.memory_bytes
            usage = self.random.uniform(0.4, 0.95) * total_memory
            node.memory_available_bytes = max(total_memory - usage, total_memory * 0.05)
            self.metrics.node_memory_total_bytes.labels(cluster=cluster.name, node=node.name).set(
                total_memory
            )
            self.metrics.node_memory_available_bytes.labels(
                cluster=cluster.name, node=node.name
            ).set(node.memory_available_bytes)

            mountpoint = "/"
            device = "rootfs"
            filesystem_size = node.ephemeral_storage_bytes
            usage_ratio = self.random.uniform(0.3, 0.95)
            node.filesystem_usage_bytes = filesystem_size * usage_ratio
            free_bytes = filesystem_size - node.filesystem_usage_bytes
            avail_bytes = max(free_bytes * 0.9, 0)
            self.metrics.node_filesystem_size_bytes.labels(
                cluster=cluster.name, node=node.name, mountpoint=mountpoint, device=device
            ).set(filesystem_size)
            self.metrics.node_filesystem_free_bytes.labels(
                cluster=cluster.name, node=node.name, mountpoint=mountpoint, device=device
            ).set(free_bytes)
            self.metrics.node_filesystem_avail_bytes.labels(
                cluster=cluster.name, node=node.name, mountpoint=mountpoint, device=device
            ).set(avail_bytes)

            for interface in NETWORK_INTERFACES:
                rx_delta = self.random.uniform(1e5, 5e7)
                tx_delta = self.random.uniform(1e5, 5e7)
                node.network_rx_bytes_total += rx_delta
                node.network_tx_bytes_total += tx_delta
                self.metrics.node_network_receive_bytes_total.labels(
                    cluster=cluster.name, node=node.name, interface=interface
                ).inc(rx_delta)
                self.metrics.node_network_transmit_bytes_total.labels(
                    cluster=cluster.name, node=node.name, interface=interface
                ).inc(tx_delta)

            for device in NODE_DISK_DEVICES:
                read_delta = self.random.uniform(1e6, 5e8)
                write_delta = self.random.uniform(1e6, 5e8)
                node.disk_read_bytes_total += read_delta
                node.disk_written_bytes_total += write_delta
                self.metrics.node_disk_read_bytes_total.labels(
                    cluster=cluster.name, node=node.name, device=device
                ).inc(read_delta)
                self.metrics.node_disk_written_bytes_total.labels(
                    cluster=cluster.name, node=node.name, device=device
                ).inc(write_delta)

            for sensor in NODE_SENSORS:
                temp = self.random.uniform(40.0, 85.0)
                self.metrics.node_temperature_celsius.labels(
                    cluster=cluster.name, node=node.name, sensor=sensor
                ).set(temp)

            self.metrics.kube_node_status_capacity_cpu_cores.labels(**node_labelset).set(
                node.cpu_cores
            )
            self.metrics.kube_node_status_capacity_memory_bytes.labels(
                **node_labelset
            ).set(node.memory_bytes)
            self.metrics.kube_node_status_allocatable_cpu_cores.labels(
                **node_labelset
            ).set(node.allocatable_cpu_cores)
            self.metrics.kube_node_status_allocatable_memory_bytes.labels(
                **node_labelset
            ).set(node.allocatable_memory_bytes)

            for condition in NODE_CONDITIONS:
                healthy = True if condition == "Ready" else self.random.random() > 0.1
                if condition == "Ready" and self.random.random() < 0.05:
                    healthy = False
                node.conditions[condition] = healthy
                self.metrics.kube_node_status_condition.labels(
                    **node_labelset, condition=condition, status="true"
                ).set(1 if healthy else 0)
                self.metrics.kube_node_status_condition.labels(
                    **node_labelset, condition=condition, status="false"
                ).set(0 if healthy else 1)
                self.metrics.kube_node_status_condition.labels(
                    **node_labelset, condition=condition, status="unknown"
                ).set(0)

    def _update_pod_metrics(self, cluster: ClusterState) -> None:
        for pod in cluster.iter_pods():
            # Update pod phase with small chance of change
            if pod.phase == "Running":
                if self.random.random() < 0.02:
                    pod.phase = self.random.choice(["Pending", "Failed", "Running"])
            else:
                if self.random.random() < 0.3:
                    pod.phase = "Running"

            pod.update_ready_containers()
            for phase in POD_PHASES:
                value = 1 if pod.phase == phase else 0
                self.metrics.kube_pod_status_phase.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    phase=phase,
                ).set(value)

            for container in pod.containers:
                cpu_delta = self.random.uniform(0.01, 0.2)
                container.update_cpu(cpu_delta)
                self.metrics.container_cpu_usage_seconds_total.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).inc(cpu_delta)

                memory_variation = container.memory_limit_bytes * self.random.uniform(-0.02, 0.03)
                container.set_memory_usage(container.memory_usage_bytes + memory_variation)
                self.metrics.container_memory_usage_bytes.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).set(container.memory_usage_bytes)

                fs_variation = container.filesystem_limit_bytes * self.random.uniform(-0.02, 0.05)
                container.set_filesystem_usage(container.filesystem_usage_bytes + fs_variation)
                self.metrics.container_fs_usage_bytes.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).set(container.filesystem_usage_bytes)

                if pod.phase != "Running" and self.random.random() < 0.2:
                    container.increment_restarts()
                restart_delta = container.restarts - container.reported_restarts
                if restart_delta > 0:
                    self.metrics.kube_pod_container_status_restarts_total.labels(
                        cluster=cluster.name,
                        namespace=pod.namespace,
                        pod=pod.name,
                        container=container.name,
                    ).inc(restart_delta)
                    container.reported_restarts = container.restarts

                ready_value = 1 if pod.phase == "Running" else 0
                self.metrics.kube_pod_container_status_ready.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).set(ready_value)

                rx_delta = self.random.uniform(1e4, 1e7)
                tx_delta = self.random.uniform(1e4, 1e7)
                container.add_network_traffic(rx_delta, tx_delta)
                self.metrics.container_network_receive_bytes_total.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).inc(rx_delta)
                self.metrics.container_network_transmit_bytes_total.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    container=container.name,
                ).inc(tx_delta)

                volume_name = self.random.choice(VOLUME_NAMES)
                volume_capacity = container.filesystem_limit_bytes * self.random.uniform(0.5, 1.0)
                volume_used = min(container.filesystem_usage_bytes, volume_capacity)
                self.metrics.kubelet_volume_stats_capacity_bytes.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    volume=volume_name,
                ).set(volume_capacity)
                self.metrics.kubelet_volume_stats_used_bytes.labels(
                    cluster=cluster.name,
                    namespace=pod.namespace,
                    pod=pod.name,
                    volume=volume_name,
                ).set(volume_used)

    def _update_deployment_metrics(self, cluster: ClusterState) -> None:
        pods_by_deployment: Dict[str, List[PodState]] = {}
        for pod in cluster.iter_pods():
            pods_by_deployment.setdefault(pod.deployment, []).append(pod)
        for deployment in cluster.deployments:
            pods = pods_by_deployment.get(deployment.name, [])
            ready = sum(1 for pod in pods if pod.phase == "Running")
            desired = max(deployment.desired_replicas + self.random.randint(-1, 1), 1)
            deployment.update_counts(ready=ready, desired=desired)
            for condition, value in (
                ("desired", deployment.desired_replicas),
                ("ready", deployment.ready_replicas),
                ("updated", deployment.updated_replicas),
                ("available", deployment.available_replicas),
            ):
                self.metrics.kube_deployment_status_replicas.labels(
                    cluster=cluster.name,
                    namespace=deployment.namespace,
                    deployment=deployment.name,
                    condition=condition,
                ).set(value)

    def _update_daemonset_metrics(self, cluster: ClusterState) -> None:
        ready_nodes = sum(1 for node in cluster.nodes if node.ready)
        for daemonset in cluster.daemonsets:
            desired = daemonset.desired_number_scheduled
            available = min(ready_nodes, desired)
            daemonset.update_availability(available)
            self.metrics.kube_daemonset_status_number_available.labels(
                cluster=cluster.name,
                namespace=daemonset.namespace,
                daemonset=daemonset.name,
            ).set(daemonset.number_available)

    def _update_control_plane_metrics(self, cluster: ClusterState) -> None:
        for _ in range(self.random.randint(50, 120)):
            verb = self.random.choice(APISERVER_VERBS)
            resource = self.random.choice(APISERVER_RESOURCES)
            code = self.random.choices(HTTP_STATUS_CODES, weights=[70, 5, 3, 5, 5, 5, 7])[0]
            self.metrics.apiserver_request_total.labels(
                cluster=cluster.name, verb=verb, resource=resource, code=code
            ).inc()
            latency = self.random.gammavariate(2.0, 0.02)
            self.metrics.apiserver_request_duration_seconds.labels(
                cluster=cluster.name, verb=verb, resource=resource
            ).observe(latency)
        for component in ("kube-controller-manager", "kube-scheduler", "kubelet"):
            code = self.random.choices(HTTP_STATUS_CODES, weights=[80, 3, 2, 3, 3, 3, 6])[0]
            self.metrics.rest_client_requests_total.labels(
                cluster=cluster.name, component=component, code=code
            ).inc(self.random.randint(5, 50))
        for result in SCHEDULER_RESULTS:
            increment = max(int(self.random.gammavariate(2.0, 3.0)), 1)
            self.metrics.scheduler_schedule_attempts_total.labels(
                cluster=cluster.name, result=result
            ).inc(increment if result != "error" else max(increment // 10, 1))
        for _ in range(self.random.randint(20, 60)):
            duration = self.random.gammavariate(2.0, 0.03)
            self.metrics.scheduler_e2e_scheduling_duration_seconds.labels(cluster=cluster.name).observe(
                duration
            )
        for controller in ("deployment", "statefulset", "daemonset", "cronjob"):
            result = self.random.choice(CONTROLLER_RESULTS)
            self.metrics.controller_manager_reconcile_total.labels(
                cluster=cluster.name, controller=controller, result=result
            ).inc(self.random.randint(1, 25))

    def _update_ingress_metrics(self, cluster: ClusterState) -> None:
        for ingress in cluster.ingresses:
            code = self.random.choices(HTTP_STATUS_CODES, weights=[85, 2, 1, 4, 4, 2, 2])[0]
            requests = self.random.randint(20, 200)
            ingress.requests_total += requests
            if ingress.controller == "nginx":
                self.metrics.nginx_ingress_controller_requests.labels(
                    cluster=cluster.name,
                    namespace=ingress.namespace,
                    ingress=ingress.name,
                    status=code,
                ).inc(requests)
                for _ in range(self.random.randint(5, 30)):
                    latency = self.random.gammavariate(2.0, 0.02)
                    self.metrics.nginx_ingress_controller_upstream_latency_seconds.labels(
                        cluster=cluster.name,
                        namespace=ingress.namespace,
                        ingress=ingress.name,
                    ).observe(latency)
            else:
                # Traefik controller metrics
                service = f"{ingress.namespace}-service"
                self.metrics.traefik_backend_requests_total.labels(
                    cluster=cluster.name, service=service, code=code
                ).inc(requests)


def build_generator(config: Config) -> FakeMetricsGenerator:
    """Helper to construct a generator with a dedicated CollectorRegistry."""

    registry = CollectorRegistry()
    return FakeMetricsGenerator(config=config, registry=registry)


def run_from_config(config: Config, iterations: int | None = None) -> None:
    """Run the generator with the provided configuration."""

    generator = FakeMetricsGenerator(config)
    generator.run(iterations=iterations)


__all__ = ["FakeMetricsGenerator", "build_generator", "run_from_config"]
