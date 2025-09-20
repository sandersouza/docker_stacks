"""Label metadata generation for synthetic kube-state-metrics series."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .entities import (
    CertificateSigningRequestState,
    ClusterState,
    ConfigMapState,
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
    NodeState,
    PersistentVolumeClaimState,
    PersistentVolumeState,
    PodDisruptionBudgetState,
    PodState,
    POD_PHASES,
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
)


_SANITIZE_RE = re.compile(r"[^0-9A-Za-z_]")


def _sanitize_label_key(key: str) -> str:
    """Transform Kubernetes label keys into valid Prometheus label names."""

    cleaned = _SANITIZE_RE.sub("_", key)
    if not cleaned:
        cleaned = "label"
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return f"label_{cleaned}"


@dataclass
class MetricLabelMetadata:
    labelnames: Tuple[str, ...]
    labelsets: Tuple[Tuple[str, ...], ...]


class KubeStateMetricLabelProvider:
    """Provide label definitions for kube-state-metrics style metrics."""

    def __init__(self, clusters: Sequence[ClusterState], rng) -> None:
        self.clusters = clusters
        self.random = rng
        base_path = Path(__file__).resolve().parent.parent
        mapping_file = base_path / "ksm.csv"
        self.metric_groups = self._load_metric_groups(mapping_file)
        self.metadata: Dict[str, MetricLabelMetadata] = {}
        self._build_metadata()

    def _load_metric_groups(self, path: Path) -> Dict[str, str]:
        if not path.exists():
            return {}
        mapping: Dict[str, str] = {}
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                metric = row.get("metric")
                group = row.get("resource_group")
                if metric and group:
                    mapping[metric.strip()] = group.strip()
        return mapping

    def _build_metadata(self) -> None:
        builders = {
            "node": self._build_node_metadata,
            "namespace": self._build_namespace_metadata,
            "deployment": self._build_deployment_metadata,
            "daemonset": self._build_daemonset_metadata,
            "statefulset": self._build_statefulset_metadata,
            "pod": self._build_pod_metadata,
            "poddisruptionbudget": self._build_pdb_metadata,
            "cronjob": self._build_cronjob_metadata,
            "job": self._build_job_metadata,
            "horizontalpodautoscaler": self._build_hpa_metadata,
            "networkpolicy": self._build_networkpolicy_metadata,
            "configmap": self._build_configmap_metadata,
            "secret": self._build_secret_metadata,
            "service": self._build_service_metadata,
            "endpoint": self._build_endpoint_metadata,
            "persistentvolume": self._build_pv_metadata,
            "persistentvolumeclaim": self._build_pvc_metadata,
            "resourcequota": self._build_resourcequota_metadata,
            "lease": self._build_lease_metadata,
            "limitrange": self._build_limitrange_metadata,
            "mutatingwebhookconfiguration": self._build_mutating_webhook_metadata,
            "validatingwebhookconfiguration": self._build_validating_webhook_metadata,
            "storageclass": self._build_storageclass_metadata,
            "customresource": self._build_vpa_metadata,
            "volumeattachment": self._build_volumeattachment_metadata,
            "certificatesigningrequest": self._build_csr_metadata,
            "apiserver": self._build_apiserver_metadata,
            "state": self._build_state_metadata,
            "ingress": self._build_ingress_metadata,
            "replicaset": self._build_replicaset_metadata,
            "replicationcontroller": self._build_replicationcontroller_metadata,
            "persistentvolumeclaim": self._build_pvc_metadata,
            "persistentvolume": self._build_pv_metadata,
            "poddisruptionbudget": self._build_pdb_metadata,
            "running": self._build_running_metadata,
        }
        # ensure builders exist for each group referenced in mapping
        for metric, group in self.metric_groups.items():
            builder = builders.get(group)
            if builder is None:
                continue
            metadata = builder(metric)
            if metadata:
                self.metadata[metric] = metadata

    def metadata_for(self, metric_name: str) -> Optional[MetricLabelMetadata]:
        return self.metadata.get(metric_name)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def _collect_nodes(self) -> Iterable[Tuple[ClusterState, NodeState]]:
        for cluster in self.clusters:
            for node in cluster.nodes:
                yield cluster, node

    def _collect_pods(self) -> Iterable[Tuple[str, PodState]]:
        for cluster in self.clusters:
            for pod in cluster.iter_pods():
                yield cluster.name, pod

    # ------------------------------------------------------------------
    # Resource specific builders
    # ------------------------------------------------------------------
    def _build_node_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        base_labels = (
            "cluster",
            "namespace",
            "service",
            "pod",
            "container",
            "job",
            "endpoint",
            "prometheus",
            "node",
        )
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_node_info":
            labelnames = base_labels + (
                "internal_ip",
                "kernel_version",
                "os_image",
                "container_runtime_version",
                "kubelet_version",
                "kubeproxy_version",
                "system_uuid",
            )
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                labelsets.append(
                    (
                        cluster.name,
                        target.namespace,
                        target.service,
                        target.pod,
                        target.container,
                        target.job,
                        target.endpoint,
                        target.prometheus,
                        node.name,
                        node.internal_ip,
                        node.kernel_version,
                        node.os_image,
                        node.container_runtime_version,
                        node.kubelet_version,
                        node.kubeproxy_version,
                        node.system_uuid,
                    )
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_labels":
            label_key_map: Dict[str, str] = {}
            for cluster, node in self._collect_nodes():
                for key in node.labels:
                    label_key_map.setdefault(_sanitize_label_key(key), key)
            extra_labels = tuple(sorted(label_key_map))
            labelnames = base_labels + extra_labels
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                values = [
                    cluster.name,
                    target.namespace,
                    target.service,
                    target.pod,
                    target.container,
                    target.job,
                    target.endpoint,
                    target.prometheus,
                    node.name,
                ]
                for label in extra_labels:
                    original = label_key_map[label]
                    values.append(node.labels.get(original, ""))
                labelsets.append(tuple(values))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_role":
            labelnames = base_labels + ("role",)
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                for role in node.roles or ["worker"]:
                    labelsets.append(
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            role,
                        )
                    )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_spec_taint":
            labelnames = base_labels + ("key", "value", "effect")
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                if not node.taints:
                    labelsets.append(
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "",
                            "",
                            "",
                        )
                    )
                else:
                    for key, value, effect in node.taints:
                        labelsets.append(
                            (
                                cluster.name,
                                target.namespace,
                                target.service,
                                target.pod,
                                target.container,
                                target.job,
                                target.endpoint,
                                target.prometheus,
                                node.name,
                                key,
                                value,
                                effect,
                            )
                        )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_spec_unschedulable":
            labelnames = base_labels
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                labelsets.append(
                    (
                        cluster.name,
                        target.namespace,
                        target.service,
                        target.pod,
                        target.container,
                        target.job,
                        target.endpoint,
                        target.prometheus,
                        node.name,
                    )
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_status_addresses":
            labelnames = base_labels + ("type", "address")
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                for addr_type, addr in node.addresses:
                    labelsets.append(
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            addr_type,
                            addr,
                        )
                    )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_status_allocatable":
            labelnames = base_labels + ("resource", "unit")
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                labelsets.extend(
                    [
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "cpu",
                            "core",
                        ),
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "memory",
                            "byte",
                        ),
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "pods",
                            "count",
                        ),
                    ]
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_status_capacity":
            labelnames = base_labels + ("resource", "unit")
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                labelsets.extend(
                    [
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "cpu",
                            "core",
                        ),
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "memory",
                            "byte",
                        ),
                        (
                            cluster.name,
                            target.namespace,
                            target.service,
                            target.pod,
                            target.container,
                            target.job,
                            target.endpoint,
                            target.prometheus,
                            node.name,
                            "pods",
                            "count",
                        ),
                    ]
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_node_status_condition":
            labelnames = base_labels + ("condition", "status")
            statuses = ("true", "false", "unknown")
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                for condition in node.conditions:
                    for status in statuses:
                        labelsets.append(
                            (
                                cluster.name,
                                target.namespace,
                                target.service,
                                target.pod,
                                target.container,
                                target.job,
                                target.endpoint,
                                target.prometheus,
                                node.name,
                                condition,
                                status,
                            )
                        )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_node_status_allocatable_cpu_cores",
            "kube_node_status_capacity_memory_bytes",
        }:
            labelnames = base_labels
            for cluster, node in self._collect_nodes():
                target = cluster.kube_state_target
                labelsets.append(
                    (
                        cluster.name,
                        target.namespace,
                        target.service,
                        target.pod,
                        target.container,
                        target.job,
                        target.endpoint,
                        target.prometheus,
                        node.name,
                    )
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_namespace_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_namespace_labels":
            labelnames = ("cluster", "namespace", "label_key", "label_value")
            for cluster in self.clusters:
                for namespace in cluster.namespaces:
                    labelsets.append((cluster.name, namespace, "env", self.random.choice(["dev", "prod", "test"])))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_namespace_status_condition":
            labelnames = ("cluster", "namespace", "condition", "status")
            for cluster in self.clusters:
                for namespace in cluster.namespaces:
                    for condition in ("Active", "Terminating"):
                        for status in ("true", "false"):
                            labelsets.append((cluster.name, namespace, condition, status))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_deployment_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_deployment_metadata_generation":
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_deployment_spec_paused":
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_deployment_spec_replicas":
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_deployment_spec_strategy_rollingupdate_max_surge",
            "kube_deployment_spec_strategy_rollingupdate_max_unavailable",
        }:
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_deployment_status_condition":
            labelnames = ("cluster", "namespace", "deployment", "condition", "status")
            conditions = ("Available", "Progressing", "ReplicaFailure")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    for condition in conditions:
                        for status in ("true", "false"):
                            labelsets.append((cluster.name, deployment.namespace, deployment.name, condition, status))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_deployment_status_observed_generation":
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_deployment_status_replicas"):
            labelnames = ("cluster", "namespace", "deployment")
            for cluster in self.clusters:
                for deployment in cluster.deployments:
                    labelsets.append((cluster.name, deployment.namespace, deployment.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_daemonset_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        labelnames = ("cluster", "namespace", "daemonset")
        if metric.startswith("kube_daemonset"):
            for cluster in self.clusters:
                for daemonset in cluster.daemonsets:
                    labelsets.append((cluster.name, daemonset.namespace, daemonset.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_statefulset_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "statefulset")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for statefulset in cluster.statefulsets:
                labelsets.append((cluster.name, statefulset.namespace, statefulset.name))
        if labelsets:
            if metric == "kube_statefulset_persistentvolumeclaim_retention_policy":
                labelnames = ("cluster", "namespace", "statefulset", "policy")
                labelsets = [
                    (cluster, namespace, name, "Retain")
                    for cluster, namespace, name in labelsets
                ]
            elif metric == "kube_statefulset_status_current_revision":
                labelnames = ("cluster", "namespace", "statefulset", "revision")
                labelsets = [
                    (cluster.name, statefulset.namespace, statefulset.name, statefulset.current_revision)
                    for cluster in self.clusters
                    for statefulset in cluster.statefulsets
                ]
            elif metric == "kube_statefulset_status_update_revision":
                labelnames = ("cluster", "namespace", "statefulset", "revision")
                labelsets = [
                    (cluster.name, statefulset.namespace, statefulset.name, statefulset.update_revision)
                    for cluster in self.clusters
                    for statefulset in cluster.statefulsets
                ]
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_pod_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_pod_info":
            labelnames = ("cluster", "namespace", "pod", "node", "host_ip", "pod_ip")
            for cluster_name, pod in self._collect_pods():
                labelsets.append(
                    (cluster_name, pod.namespace, pod.name, pod.node_name, pod.host_ip, pod.pod_ip)
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_labels":
            labelnames = ("cluster", "namespace", "pod", "label_key", "label_value")
            for cluster_name, pod in self._collect_pods():
                for key, value in pod.labels.items():
                    labelsets.append((cluster_name, pod.namespace, pod.name, key, value))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_owner":
            labelnames = (
                "cluster",
                "namespace",
                "pod",
                "owner_kind",
                "owner_name",
                "owner_is_controller",
            )
            for cluster_name, pod in self._collect_pods():
                labelsets.append(
                    (
                        cluster_name,
                        pod.namespace,
                        pod.name,
                        pod.owner_kind,
                        pod.owner_name,
                        "true",
                    )
                )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_service_account":
            labelnames = ("cluster", "namespace", "pod", "serviceaccount")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, pod.service_account))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_scheduler":
            labelnames = ("cluster", "namespace", "pod", "scheduler")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, pod.scheduler))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_start_time":
            labelnames = ("cluster", "namespace", "pod")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_ips":
            labelnames = ("cluster", "namespace", "pod", "ip")
            for cluster_name, pod in self._collect_pods():
                for ip in pod.pod_ips:
                    labelsets.append((cluster_name, pod.namespace, pod.name, ip))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_tolerations":
            labelnames = ("cluster", "namespace", "pod", "key", "effect")
            for cluster_name, pod in self._collect_pods():
                if not pod.tolerations:
                    labelsets.append((cluster_name, pod.namespace, pod.name, "", ""))
                else:
                    for key, effect in pod.tolerations:
                        labelsets.append((cluster_name, pod.namespace, pod.name, key, effect))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_spec_volumes_persistentvolumeclaims_info":
            labelnames = ("cluster", "namespace", "pod", "volume", "persistentvolumeclaim")
            for cluster_name, pod in self._collect_pods():
                if not pod.volumes:
                    labelsets.append((cluster_name, pod.namespace, pod.name, "config", ""))
                else:
                    for volume_name, claim, _ in pod.volumes:
                        labelsets.append((cluster_name, pod.namespace, pod.name, volume_name, claim))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_spec_volumes_persistentvolumeclaims_readonly":
            labelnames = ("cluster", "namespace", "pod", "volume", "persistentvolumeclaim")
            for cluster_name, pod in self._collect_pods():
                if not pod.volumes:
                    labelsets.append((cluster_name, pod.namespace, pod.name, "config", ""))
                else:
                    for volume_name, claim, read_only in pod.volumes:
                        labelsets.append((cluster_name, pod.namespace, pod.name, volume_name, claim))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.endswith("_status_ready"):
            labelnames = ("cluster", "namespace", "pod", "condition")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, "Ready"))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_pod_resource_limit",
            "kube_pod_resource_request",
        }:
            labelnames = ("cluster", "namespace", "pod", "resource", "unit")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, "cpu", "core"))
                labelsets.append((cluster_name, pod.namespace, pod.name, "memory", "byte"))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_pod_container_"):
            labelsets = []
            if metric == "kube_pod_container_info":
                labelnames = ("cluster", "namespace", "pod", "container", "image")
                for cluster_name, pod in self._collect_pods():
                    for container in pod.containers:
                        labelsets.append(
                            (
                                cluster_name,
                                pod.namespace,
                                pod.name,
                                container.name,
                                container.image,
                            )
                        )
                return MetricLabelMetadata(labelnames, tuple(labelsets))
            if metric in {
                "kube_pod_container_resource_limits",
                "kube_pod_container_resource_requests",
            }:
                labelnames = ("cluster", "namespace", "pod", "container", "resource", "unit")
                for cluster_name, pod in self._collect_pods():
                    for container in pod.containers:
                        labelsets.append(
                            (
                                cluster_name,
                                pod.namespace,
                                pod.name,
                                container.name,
                                "cpu",
                                "core",
                            )
                        )
                        labelsets.append(
                            (
                                cluster_name,
                                pod.namespace,
                                pod.name,
                                container.name,
                                "memory",
                                "byte",
                            )
                        )
                return MetricLabelMetadata(labelnames, tuple(labelsets))
            if metric == "kube_pod_container_state_started":
                labelnames = ("cluster", "namespace", "pod", "container")
                for cluster_name, pod in self._collect_pods():
                    for container in pod.containers:
                        labelsets.append((cluster_name, pod.namespace, pod.name, container.name))
                return MetricLabelMetadata(labelnames, tuple(labelsets))
            if metric.startswith("kube_pod_container_status"):
                if metric.endswith("_reason"):
                    labelnames = ("cluster", "namespace", "pod", "container", "reason")
                    for cluster_name, pod in self._collect_pods():
                        for container in pod.containers:
                            if metric.endswith("waiting_reason"):
                                reason = container.waiting_reason or ""
                            elif "terminated" in metric:
                                reason = container.last_terminated_reason or ""
                            else:
                                reason = pod.reason
                            labelsets.append(
                                (
                                    cluster_name,
                                    pod.namespace,
                                    pod.name,
                                    container.name,
                                    reason,
                                )
                            )
                    return MetricLabelMetadata(labelnames, tuple(labelsets))
                labelnames = ("cluster", "namespace", "pod", "container")
                for cluster_name, pod in self._collect_pods():
                    for container in pod.containers:
                        labelsets.append((cluster_name, pod.namespace, pod.name, container.name))
                return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_pod_init_container"):
            labelnames = ("cluster", "namespace", "pod", "container")
            for cluster_name, pod in self._collect_pods():
                for container in pod.init_containers:
                    labelsets.append((cluster_name, pod.namespace, pod.name, container.name))
            if labelsets:
                if metric.endswith("_resource_limits") or metric.endswith("_resource_requests"):
                    labelnames = ("cluster", "namespace", "pod", "container", "resource", "unit")
                    expanded: List[Tuple[str, ...]] = []
                    for cluster, namespace, pod_name, container in labelsets:
                        expanded.append((cluster, namespace, pod_name, container, "cpu", "core"))
                        expanded.append((cluster, namespace, pod_name, container, "memory", "byte"))
                    labelsets = expanded
                return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_deletion_timestamp":
            labelnames = ("cluster", "namespace", "pod")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_status_ready":
            labelnames = ("cluster", "namespace", "pod", "condition", "status")
            for cluster_name, pod in self._collect_pods():
                for status in ("true", "false"):
                    labelsets.append((cluster_name, pod.namespace, pod.name, "Ready", status))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_status_phase":
            labelnames = ("cluster", "namespace", "pod", "phase")
            for cluster_name, pod in self._collect_pods():
                for phase in POD_PHASES:
                    labelsets.append((cluster_name, pod.namespace, pod.name, phase))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_status_reason":
            labelnames = ("cluster", "namespace", "pod", "reason")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, pod.reason))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_pod_status_unschedulable":
            labelnames = ("cluster", "namespace", "pod", "reason")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name, "") )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_pod_status_initialized_time",
            "kube_pod_status_ready_time",
            "kube_pod_status_container_ready_time",
            "kube_pod_status_scheduled_time",
        }:
            labelnames = ("cluster", "namespace", "pod")
            for cluster_name, pod in self._collect_pods():
                labelsets.append((cluster_name, pod.namespace, pod.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_running_pod_ready":
            labelnames = ("cluster", "namespace", "pod")
            for cluster_name, pod in self._collect_pods():
                if pod.phase == "Running":
                    labelsets.append((cluster_name, pod.namespace, pod.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_cronjob_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "cronjob")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for cronjob in cluster.cronjobs:
                labelsets.append((cluster.name, cronjob.namespace, cronjob.name))
        if not labelsets:
            return None
        if metric == "kube_cronjob_info":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_cronjob_spec_suspend":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_cronjob_spec"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_cronjob_status"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_cronjob_next_schedule_time":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_job_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "job")
        labelsets: List[Tuple[str, ...]] = []
        owners: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for job in cluster.jobs:
                labelsets.append((cluster.name, job.namespace, job.name))
                owners.append((cluster.name, job.namespace, job.name, job.owner_kind, job.owner_name))
        if metric == "kube_job_info":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_job_owner":
            return MetricLabelMetadata(
                ("cluster", "namespace", "job", "owner_kind", "owner_name"),
                tuple(owners),
            )
        if metric.startswith("kube_job_spec") or metric.startswith("kube_job_status") or metric in {
            "kube_job_complete",
            "kube_job_failed",
        }:
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_hpa_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        labelnames = ("cluster", "namespace", "horizontalpodautoscaler")
        for cluster in self.clusters:
            for hpa in cluster.horizontalpodautoscalers:
                labelsets.append((cluster.name, hpa.namespace, hpa.name))
        if not labelsets:
            return None
        if metric == "kube_horizontalpodautoscaler_info":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_horizontalpodautoscaler_status_condition":
            expanded: List[Tuple[str, ...]] = []
            labelnames = (
                "cluster",
                "namespace",
                "horizontalpodautoscaler",
                "condition",
                "status",
            )
            for cluster in self.clusters:
                for hpa in cluster.horizontalpodautoscalers:
                    for condition, status in hpa.conditions:
                        expanded.append((cluster.name, hpa.namespace, hpa.name, condition, status))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric.startswith("kube_horizontalpodautoscaler_spec") or metric.startswith(
            "kube_horizontalpodautoscaler_status"
        ):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_networkpolicy_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "networkpolicy")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for policy in cluster.networkpolicies:
                labelsets.append((cluster.name, policy.namespace, policy.name))
        if metric in {
            "kube_networkpolicy_spec_egress_rules",
            "kube_networkpolicy_spec_ingress_rules",
        }:
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_configmap_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric != "kube_configmap_info":
            return None
        labelnames = ("cluster", "namespace", "configmap")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for configmap in cluster.configmaps:
                labelsets.append((cluster.name, configmap.namespace, configmap.name))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_secret_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_secret_info":
            labelnames = ("cluster", "namespace", "secret", "type")
            for cluster in self.clusters:
                for secret in cluster.secrets:
                    labelsets.append((cluster.name, secret.namespace, secret.name, secret.secret_type))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_secret_owner":
            labelnames = ("cluster", "namespace", "secret", "owner_kind", "owner_name")
            for cluster in self.clusters:
                for secret in cluster.secrets:
                    labelsets.append(
                        (cluster.name, secret.namespace, secret.name, secret.owner_kind, secret.owner_name)
                    )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_secret_type":
            return self._build_secret_metadata("kube_secret_info")
        return None

    def _build_service_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelsets: List[Tuple[str, ...]] = []
        if metric == "kube_service_info":
            labelnames = ("cluster", "namespace", "service", "cluster_ip")
            for cluster in self.clusters:
                for service in cluster.services:
                    labelsets.append((cluster.name, service.namespace, service.name, service.cluster_ip))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_service_spec_type":
            labelnames = ("cluster", "namespace", "service", "type")
            for cluster in self.clusters:
                for service in cluster.services:
                    labelsets.append((cluster.name, service.namespace, service.name, service.service_type))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_service_spec_external_ip":
            labelnames = ("cluster", "namespace", "service", "external_ip")
            for cluster in self.clusters:
                for service in cluster.services:
                    if service.external_ips:
                        for ip in service.external_ips:
                            labelsets.append((cluster.name, service.namespace, service.name, ip))
                    else:
                        labelsets.append((cluster.name, service.namespace, service.name, ""))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_endpoint_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric == "kube_endpoint_info":
            labelnames = ("cluster", "namespace", "endpoint")
            labelsets: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for endpoint in cluster.endpoints:
                    labelsets.append((cluster.name, endpoint.namespace, endpoint.name))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_endpoint_address",
            "kube_endpoint_address_available",
            "kube_endpoint_address_not_ready",
        }:
            labelnames = ("cluster", "namespace", "endpoint", "address")
            labelsets: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for endpoint in cluster.endpoints:
                    for address in endpoint.addresses:
                        labelsets.append((cluster.name, endpoint.namespace, endpoint.name, address))
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_endpoint_ports":
            labelnames = ("cluster", "namespace", "endpoint", "port_name", "port", "protocol")
            labelsets: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for endpoint in cluster.endpoints:
                    for port_name, port, protocol in endpoint.ports:
                        labelsets.append(
                            (cluster.name, endpoint.namespace, endpoint.name, port_name, str(port), protocol)
                        )
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_pv_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "persistentvolume")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for pv in cluster.persistentvolumes:
                labelsets.append((cluster.name, pv.name))
        if metric == "kube_persistentvolume_info":
            labelnames = ("cluster", "persistentvolume", "storageclass")
            labelsets = [
                (cluster.name, pv.name, pv.storage_class)
                for cluster in self.clusters
                for pv in cluster.persistentvolumes
            ]
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_persistentvolume_labels":
            labelnames = ("cluster", "persistentvolume", "label_key", "label_value")
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for pv in cluster.persistentvolumes:
                    for key, value in pv.labels.items():
                        expanded.append((cluster.name, pv.name, key, value))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric == "kube_persistentvolume_claim_ref":
            labelnames = ("cluster", "persistentvolume", "namespace", "persistentvolumeclaim")
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for pv in cluster.persistentvolumes:
                    expanded.append((cluster.name, pv.name, pv.claim_namespace, pv.claim_name))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric in {
            "kube_persistentvolume_capacity_bytes",
            "kube_persistentvolume_status_phase",
            "kube_persistentvolume_deletion_timestamp",
        }:
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_pvc_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "persistentvolumeclaim")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for pvc in cluster.persistentvolumeclaims:
                labelsets.append((cluster.name, pvc.namespace, pvc.name))
        if metric == "kube_persistentvolumeclaim_info":
            labelnames = ("cluster", "namespace", "persistentvolumeclaim", "storageclass")
            labelsets = [
                (cluster.name, pvc.namespace, pvc.name, pvc.storage_class)
                for cluster in self.clusters
                for pvc in cluster.persistentvolumeclaims
            ]
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_persistentvolumeclaim_labels":
            labelnames = ("cluster", "namespace", "persistentvolumeclaim", "label_key", "label_value")
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for pvc in cluster.persistentvolumeclaims:
                    for key, value in pvc.labels.items():
                        expanded.append((cluster.name, pvc.namespace, pvc.name, key, value))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric == "kube_persistentvolumeclaim_access_mode":
            labelnames = ("cluster", "namespace", "persistentvolumeclaim", "access_mode")
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for pvc in cluster.persistentvolumeclaims:
                    for mode in pvc.access_modes:
                        expanded.append((cluster.name, pvc.namespace, pvc.name, mode))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric in {
            "kube_persistentvolumeclaim_resource_requests_storage_bytes",
            "kube_persistentvolumeclaim_status_phase",
            "kube_persistentvolumeclaim_deletion_timestamp",
        }:
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_pdb_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "poddisruptionbudget")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for pdb in cluster.pod_disruption_budgets:
                labelsets.append((cluster.name, pdb.namespace, pdb.name))
        if metric == "kube_poddisruptionbudget_labels":
            labelnames = (
                "cluster",
                "namespace",
                "poddisruptionbudget",
                "label_key",
                "label_value",
            )
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for pdb in cluster.pod_disruption_budgets:
                    for key, value in pdb.labels.items():
                        expanded.append((cluster.name, pdb.namespace, pdb.name, key, value))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric.startswith("kube_poddisruptionbudget_status"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_resourcequota_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric != "kube_resourcequota":
            return None
        labelnames = ("cluster", "namespace", "resourcequota", "resource")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for quota in cluster.resourcequotas:
                labelsets.append((cluster.name, quota.namespace, quota.name, quota.resource))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_lease_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric not in {"kube_lease_owner", "kube_lease_renew_time"}:
            return None
        labelnames = ("cluster", "namespace", "lease")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for lease in cluster.leases:
                labelsets.append((cluster.name, lease.namespace, lease.name))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_limitrange_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric != "kube_limitrange":
            return None
        labelnames = ("cluster", "namespace", "limitrange", "resource", "type")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for limitrange in cluster.limitranges:
                labelsets.append(
                    (
                        cluster.name,
                        limitrange.namespace,
                        limitrange.name,
                        limitrange.resource,
                        limitrange.limit_type,
                    )
                )
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_mutating_webhook_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric not in {
            "kube_mutatingwebhookconfiguration_info",
            "kube_mutatingwebhookconfiguration_webhook_clientconfig_service",
        }:
            return None
        labelnames = ("cluster", "mutatingwebhookconfiguration", "service_namespace", "service_name")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for webhook in cluster.mutating_webhooks:
                labelsets.append((cluster.name, webhook.name, webhook.service_namespace, webhook.service_name))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_validating_webhook_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric not in {
            "kube_validatingwebhookconfiguration_info",
            "kube_validatingwebhookconfiguration_webhook_clientconfig_service",
        }:
            return None
        labelnames = ("cluster", "validatingwebhookconfiguration", "service_namespace", "service_name")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for webhook in cluster.validating_webhooks:
                labelsets.append((cluster.name, webhook.name, webhook.service_namespace, webhook.service_name))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_storageclass_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric != "kube_storageclass_info":
            return None
        labelnames = ("cluster", "storageclass", "provisioner")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for storageclass in cluster.storageclasses:
                labelsets.append((cluster.name, storageclass.name, storageclass.provisioner))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_vpa_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "verticalpodautoscaler", "container")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for vpa in cluster.vertical_pod_autoscalers:
                labelsets.append((cluster.name, vpa.namespace, vpa.name, vpa.container_name))
        if metric == "kube_customresource_verticalpodautoscaler_spec_updatepolicy_updatemode":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric.startswith("kube_customresource_verticalpodautoscaler_status"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_volumeattachment_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "volumeattachment")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for attachment in cluster.volume_attachments:
                labelsets.append((cluster.name, attachment.name))
        if metric == "kube_volumeattachment_info":
            labelnames = ("cluster", "volumeattachment", "node")
            labelsets = [
                (cluster.name, attachment.name, attachment.node)
                for cluster in self.clusters
                for attachment in cluster.volume_attachments
            ]
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_volumeattachment_labels":
            labelnames = ("cluster", "volumeattachment", "label_key", "label_value")
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for attachment in cluster.volume_attachments:
                    for key, value in attachment.metadata_entries.items():
                        expanded.append((cluster.name, attachment.name, key, value))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        if metric == "kube_volumeattachment_spec_source_persistentvolume":
            labelnames = ("cluster", "volumeattachment", "persistentvolume")
            labelsets = [
                (cluster.name, attachment.name, attachment.persistent_volume)
                for cluster in self.clusters
                for attachment in cluster.volume_attachments
            ]
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric in {
            "kube_volumeattachment_status_attached",
            "kube_volumeattachment_status_attachment_metadata",
        }:
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_csr_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "certificatesigningrequest")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for csr in cluster.certificate_signing_requests:
                labelsets.append((cluster.name, csr.name))
        if metric == "kube_certificatesigningrequest_cert_length":
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        if metric == "kube_certificatesigningrequest_condition":
            labelnames = (
                "cluster",
                "certificatesigningrequest",
                "condition",
                "status",
            )
            expanded: List[Tuple[str, ...]] = []
            for cluster in self.clusters:
                for csr in cluster.certificate_signing_requests:
                    expanded.append((cluster.name, csr.name, csr.condition, csr.status))
            return MetricLabelMetadata(labelnames, tuple(expanded))
        return None

    def _build_apiserver_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster",)
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            labelsets.append((cluster.name,))
        return MetricLabelMetadata(labelnames, tuple(labelsets)) if labelsets else None

    def _build_state_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster",)
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            labelsets.append((cluster.name,))
        return MetricLabelMetadata(labelnames, tuple(labelsets))

    def _build_ingress_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "ingress")
        labelsets: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for ingress in cluster.ingresses:
                labelsets.append((cluster.name, ingress.namespace, ingress.name))
        if metric == "kube_ingress_tls":
            labelnames = ("cluster", "namespace", "ingress", "tls")
            labelsets = [
                (cluster.name, ingress.namespace, ingress.name, "enabled")
                for cluster in self.clusters
                for ingress in cluster.ingresses
            ]
        if metric == "kube_ingress_path":
            labelnames = ("cluster", "namespace", "ingress", "path")
            labelsets = [
                (cluster.name, ingress.namespace, ingress.name, "/")
                for cluster in self.clusters
                for ingress in cluster.ingresses
            ]
        return MetricLabelMetadata(labelnames, tuple(labelsets)) if labelsets else None

    def _build_replicaset_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "replicaset")
        labelsets: List[Tuple[str, ...]] = []
        owners: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for rs in cluster.replicasets:
                labelsets.append((cluster.name, rs.namespace, rs.name))
                owners.append((cluster.name, rs.namespace, rs.name, rs.owner_kind, rs.owner_name))
        if metric == "kube_replicaset_owner":
            labelnames = (
                "cluster",
                "namespace",
                "replicaset",
                "owner_kind",
                "owner_name",
            )
            return MetricLabelMetadata(labelnames, tuple(owners))
        if metric.startswith("kube_replicaset"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_replicationcontroller_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        labelnames = ("cluster", "namespace", "replicationcontroller")
        labelsets: List[Tuple[str, ...]] = []
        owners: List[Tuple[str, ...]] = []
        for cluster in self.clusters:
            for rc in cluster.replicationcontrollers:
                labelsets.append((cluster.name, rc.namespace, rc.name))
                owners.append((cluster.name, rc.namespace, rc.name, rc.owner_kind, rc.owner_name))
        if metric == "kube_replicationcontroller_owner":
            labelnames = (
                "cluster",
                "namespace",
                "replicationcontroller",
                "owner_kind",
                "owner_name",
            )
            return MetricLabelMetadata(labelnames, tuple(owners))
        if metric.startswith("kube_replicationcontroller"):
            return MetricLabelMetadata(labelnames, tuple(labelsets))
        return None

    def _build_running_metadata(self, metric: str) -> Optional[MetricLabelMetadata]:
        if metric != "kube_running_pod_ready":
            return None
        labelnames = ("cluster", "namespace", "pod")
        labelsets: List[Tuple[str, ...]] = []
        for cluster_name, pod in self._collect_pods():
            if pod.phase == "Running":
                labelsets.append((cluster_name, pod.namespace, pod.name))
        return MetricLabelMetadata(labelnames, tuple(labelsets))
