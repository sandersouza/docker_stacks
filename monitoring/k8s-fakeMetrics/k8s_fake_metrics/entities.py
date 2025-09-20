from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

POD_PHASES: tuple[str, ...] = ("Pending", "Running", "Succeeded", "Failed", "Unknown")
NODE_CONDITIONS: tuple[str, ...] = (
    "Ready",
    "DiskPressure",
    "MemoryPressure",
    "NetworkUnavailable",
)


@dataclass(slots=True)
class ContainerState:
    """Mutable state for a container inside a pod."""

    name: str
    cpu_seconds_total: float
    memory_usage_bytes: float
    memory_limit_bytes: float
    filesystem_usage_bytes: float
    filesystem_limit_bytes: float
    restarts: int
    network_rx_bytes_total: float
    network_tx_bytes_total: float
    image: str = ""
    request_cpu_cores: float = 0.0
    request_memory_bytes: float = 0.0
    limit_cpu_cores: float = 0.0
    reported_restarts: int = 0
    last_terminated_reason: str = ""
    last_terminated_exit_code: int = 0
    last_terminated_timestamp: float = 0.0
    waiting_reason: str = ""
    started_at: float = 0.0

    def update_cpu(self, delta: float) -> None:
        self.cpu_seconds_total += max(delta, 0.0)

    def set_memory_usage(self, usage: float) -> None:
        self.memory_usage_bytes = min(max(usage, 0.0), self.memory_limit_bytes)

    def set_filesystem_usage(self, usage: float) -> None:
        self.filesystem_usage_bytes = min(max(usage, 0.0), self.filesystem_limit_bytes)

    def increment_restarts(self, amount: int = 1) -> None:
        if amount > 0:
            self.restarts += amount

    def add_network_traffic(self, rx: float, tx: float) -> None:
        self.network_rx_bytes_total += max(rx, 0.0)
        self.network_tx_bytes_total += max(tx, 0.0)


@dataclass(slots=True)
class PodState:
    """Mutable state for a Kubernetes pod."""

    name: str
    namespace: str
    node_name: str
    deployment: str
    containers: List[ContainerState]
    phase: str = "Pending"
    qos_class: str = "Burstable"
    ready_containers: int = 0
    labels: Dict[str, str] = field(default_factory=dict)
    owner_kind: str = "Deployment"
    owner_name: str = ""
    service_account: str = "default"
    scheduler: str = "default-scheduler"
    start_time: float = 0.0
    host_ip: str = ""
    pod_ip: str = ""
    pod_ips: List[str] = field(default_factory=list)
    tolerations: List[Tuple[str, str]] = field(default_factory=list)
    deletion_timestamp: Optional[float] = None
    reason: str = "Running"
    ready_time: float = 0.0
    initialized_time: float = 0.0
    scheduled_time: float = 0.0
    container_ready_time: float = 0.0
    volumes: List[Tuple[str, str, bool]] = field(default_factory=list)
    init_containers: List[ContainerState] = field(default_factory=list)

    def set_phase(self, phase: str) -> None:
        if phase not in POD_PHASES:
            raise ValueError(f"Unsupported pod phase: {phase}")
        self.phase = phase

    @property
    def restart_count(self) -> int:
        return sum(container.restarts for container in self.containers)

    def update_ready_containers(self) -> None:
        self.ready_containers = sum(
            1 for container in self.containers if self.phase == "Running"
        )


@dataclass(slots=True)
class NodeState:
    """Mutable state for a Kubernetes node."""

    name: str
    cluster: str
    cpu_cores: int
    memory_bytes: float
    ephemeral_storage_bytes: float
    pods: List[PodState] = field(default_factory=list)
    cpu_modes_seconds: Dict[str, float] = field(
        default_factory=lambda: {"user": 0.0, "system": 0.0, "idle": 0.0, "iowait": 0.0}
    )
    memory_available_bytes: float = 0.0
    filesystem_usage_bytes: float = 0.0
    network_rx_bytes_total: float = 0.0
    network_tx_bytes_total: float = 0.0
    disk_read_bytes_total: float = 0.0
    disk_written_bytes_total: float = 0.0
    kernel_version: str = ""
    os_image: str = ""
    container_runtime_version: str = ""
    kubelet_version: str = ""
    kubeproxy_version: str = ""
    system_uuid: str = ""
    internal_ip: str = ""
    conditions: Dict[str, bool] = field(
        default_factory=lambda: {condition: True for condition in NODE_CONDITIONS}
    )
    labels: Dict[str, str] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)
    taints: List[Tuple[str, str, str]] = field(default_factory=list)
    addresses: List[Tuple[str, str]] = field(default_factory=list)
    allocatable_cpu_cores: float = 0.0
    allocatable_memory_bytes: float = 0.0
    capacity_pods: int = 0
    allocatable_pods: int = 0

    def __post_init__(self) -> None:
        self.memory_available_bytes = self.memory_bytes * 0.6
        self.filesystem_usage_bytes = self.ephemeral_storage_bytes * 0.4
        if not self.roles:
            self.roles = ["worker"]
        if not self.allocatable_cpu_cores:
            self.allocatable_cpu_cores = max(self.cpu_cores - 1, 1)
        if not self.allocatable_memory_bytes:
            self.allocatable_memory_bytes = self.memory_bytes * 0.9
        if not self.capacity_pods:
            self.capacity_pods = 110
        if not self.allocatable_pods:
            self.allocatable_pods = int(self.capacity_pods * 0.9)
        if not self.internal_ip:
            for addr_type, addr in self.addresses:
                if addr_type == "InternalIP":
                    self.internal_ip = addr
                    break

    @property
    def ready(self) -> bool:
        return self.conditions.get("Ready", False)


@dataclass(slots=True)
class DeploymentState:
    """Simplified representation of a deployment."""

    name: str
    namespace: str
    desired_replicas: int
    updated_replicas: int
    ready_replicas: int
    available_replicas: int

    def update_counts(self, ready: int, desired: Optional[int] = None) -> None:
        if desired is not None:
            self.desired_replicas = desired
        self.ready_replicas = ready
        self.available_replicas = max(min(ready, self.desired_replicas), 0)
        self.updated_replicas = min(self.desired_replicas, self.available_replicas)


@dataclass(slots=True)
class DaemonSetState:
    """Simplified representation of a daemonset."""

    name: str
    namespace: str
    desired_number_scheduled: int
    number_available: int

    def update_availability(self, available: int) -> None:
        self.number_available = max(min(available, self.desired_number_scheduled), 0)


@dataclass(slots=True)
class IngressState:
    """Representation for ingress controllers generating metrics."""

    name: str
    namespace: str
    controller: str = "nginx"
    requests_total: float = 0.0


@dataclass(slots=True)
class CronJobState:
    name: str
    namespace: str
    schedule: str
    suspend: bool
    starting_deadline_seconds: Optional[int]
    successful_job_history_limit: int
    failed_job_history_limit: int
    next_schedule_time: float
    last_schedule_time: float
    last_successful_time: float
    active_jobs: int


@dataclass(slots=True)
class JobState:
    name: str
    namespace: str
    completions: Optional[int]
    parallelism: int
    active_deadline_seconds: Optional[int]
    start_time: float
    completion_time: float
    succeeded: int
    failed: int
    active: int
    owner_kind: str = "CronJob"
    owner_name: str = ""


@dataclass(slots=True)
class StatefulSetState:
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    current_replicas: int
    updated_replicas: int
    current_revision: str
    update_revision: str
    observed_generation: int
    pvc_retention_policy: str


@dataclass(slots=True)
class ReplicaSetState:
    name: str
    namespace: str
    desired_replicas: int
    ready_replicas: int
    fully_labeled_replicas: int
    observed_generation: int
    owner_kind: str = "Deployment"
    owner_name: str = ""


@dataclass(slots=True)
class ReplicationControllerState:
    name: str
    namespace: str
    desired_replicas: int
    ready_replicas: int
    fully_labeled_replicas: int
    available_replicas: int
    observed_generation: int
    owner_kind: str = "Deployment"
    owner_name: str = ""


@dataclass(slots=True)
class HorizontalPodAutoscalerState:
    name: str
    namespace: str
    min_replicas: int
    max_replicas: int
    current_replicas: int
    desired_replicas: int
    target_metric: float
    target_metric_name: str
    generation: int
    conditions: Sequence[Tuple[str, str]]


@dataclass(slots=True)
class NetworkPolicyState:
    name: str
    namespace: str
    ingress_rules: int
    egress_rules: int


@dataclass(slots=True)
class ConfigMapState:
    name: str
    namespace: str


@dataclass(slots=True)
class SecretState:
    name: str
    namespace: str
    secret_type: str
    owner_kind: str
    owner_name: str


@dataclass(slots=True)
class ServiceState:
    name: str
    namespace: str
    service_type: str
    cluster_ip: str
    external_ips: Sequence[str]


@dataclass(slots=True)
class EndpointState:
    name: str
    namespace: str
    addresses: Sequence[str]
    not_ready_addresses: Sequence[str]
    ports: Sequence[Tuple[str, int, str]]


@dataclass(slots=True)
class PersistentVolumeState:
    name: str
    capacity_bytes: float
    storage_class: str
    access_modes: Sequence[str]
    status_phase: str
    labels: Dict[str, str]
    claim_namespace: str
    claim_name: str
    deletion_timestamp: Optional[float]


@dataclass(slots=True)
class PersistentVolumeClaimState:
    name: str
    namespace: str
    storage_request_bytes: float
    access_modes: Sequence[str]
    volume_name: str
    status_phase: str
    storage_class: str
    deletion_timestamp: Optional[float]
    labels: Dict[str, str]


@dataclass(slots=True)
class PodDisruptionBudgetState:
    name: str
    namespace: str
    current_healthy: int
    desired_healthy: int
    expected_pods: int
    disruptions_allowed: int
    observed_generation: int
    labels: Dict[str, str]


@dataclass(slots=True)
class ResourceQuotaState:
    name: str
    namespace: str
    resource: str
    hard: float
    used: float


@dataclass(slots=True)
class LeaseState:
    name: str
    namespace: str
    renew_time: float
    owner: str


@dataclass(slots=True)
class LimitRangeState:
    name: str
    namespace: str
    resource: str
    limit_type: str
    min_value: float
    max_value: float


@dataclass(slots=True)
class WebhookConfigurationState:
    name: str
    service_namespace: str
    service_name: str
    webhook: str


@dataclass(slots=True)
class StorageClassState:
    name: str
    provisioner: str


@dataclass(slots=True)
class VerticalPodAutoscalerState:
    name: str
    namespace: str
    container_name: str
    target_cpu: float
    target_memory_bytes: float
    lower_cpu: float
    lower_memory_bytes: float
    upper_cpu: float
    upper_memory_bytes: float
    uncapped_cpu: float
    uncapped_memory_bytes: float
    update_mode: str


@dataclass(slots=True)
class VolumeAttachmentState:
    name: str
    persistent_volume: str
    attached: bool
    node: str
    metadata_entries: Dict[str, str]


@dataclass(slots=True)
class CertificateSigningRequestState:
    name: str
    signer_name: str
    condition: str
    status: str
    cert_length: int


@dataclass(slots=True)
class KubeStateScrapeTarget:
    """Metadata describing the synthetic kube-state-metrics scrape target."""

    namespace: str
    service: str
    pod: str
    container: str
    endpoint: str
    job: str
    prometheus: str


@dataclass(slots=True)
class ClusterState:
    """Container for all simulated resources for a cluster."""

    name: str
    namespaces: List[str]
    nodes: List[NodeState]
    deployments: List[DeploymentState]
    daemonsets: List[DaemonSetState]
    ingresses: List[IngressState]
    cronjobs: List[CronJobState]
    jobs: List[JobState]
    statefulsets: List[StatefulSetState]
    replicasets: List[ReplicaSetState]
    replicationcontrollers: List[ReplicationControllerState]
    horizontalpodautoscalers: List[HorizontalPodAutoscalerState]
    networkpolicies: List[NetworkPolicyState]
    configmaps: List[ConfigMapState]
    secrets: List[SecretState]
    services: List[ServiceState]
    endpoints: List[EndpointState]
    persistentvolumes: List[PersistentVolumeState]
    persistentvolumeclaims: List[PersistentVolumeClaimState]
    pod_disruption_budgets: List[PodDisruptionBudgetState]
    resourcequotas: List[ResourceQuotaState]
    leases: List[LeaseState]
    limitranges: List[LimitRangeState]
    mutating_webhooks: List[WebhookConfigurationState]
    validating_webhooks: List[WebhookConfigurationState]
    storageclasses: List[StorageClassState]
    vertical_pod_autoscalers: List[VerticalPodAutoscalerState]
    volume_attachments: List[VolumeAttachmentState]
    certificate_signing_requests: List[CertificateSigningRequestState]
    kube_state_target: KubeStateScrapeTarget

    def iter_pods(self) -> Iterable[PodState]:
        for node in self.nodes:
            yield from node.pods


__all__ = [
    "CertificateSigningRequestState",
    "ClusterState",
    "ConfigMapState",
    "ContainerState",
    "CronJobState",
    "DaemonSetState",
    "DeploymentState",
    "EndpointState",
    "HorizontalPodAutoscalerState",
    "IngressState",
    "JobState",
    "LeaseState",
    "LimitRangeState",
    "NetworkPolicyState",
    "NODE_CONDITIONS",
    "NodeState",
    "POD_PHASES",
    "PodDisruptionBudgetState",
    "PodState",
    "KubeStateScrapeTarget",
    "PersistentVolumeClaimState",
    "PersistentVolumeState",
    "ReplicaSetState",
    "ReplicationControllerState",
    "ResourceQuotaState",
    "SecretState",
    "ServiceState",
    "StatefulSetState",
    "StorageClassState",
    "VerticalPodAutoscalerState",
    "VolumeAttachmentState",
    "WebhookConfigurationState",
]
