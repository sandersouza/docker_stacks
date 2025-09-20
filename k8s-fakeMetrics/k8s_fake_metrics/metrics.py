"""Prometheus metric registrations for the fake Kubernetes environment."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


KSM_BASE_NODE_LABELS = (
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


class MetricSet:
    """Wrapper object holding Prometheus metric instances."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        reg = registry
        self.node_cpu_seconds_total = Counter(
            "node_cpu_seconds_total",
            "Cumulative node CPU time broken down by mode.",
            labelnames=("cluster", "node", "mode"),
            registry=reg,
        )
        self.node_memory_available_bytes = Gauge(
            "node_memory_MemAvailable_bytes",
            "Amount of available memory on the node.",
            labelnames=("cluster", "node"),
            registry=reg,
        )
        self.node_memory_total_bytes = Gauge(
            "node_memory_MemTotal_bytes",
            "Total amount of memory available on the node.",
            labelnames=("cluster", "node"),
            registry=reg,
        )
        self.node_filesystem_size_bytes = Gauge(
            "node_filesystem_size_bytes",
            "Filesystem capacity for the node root filesystem.",
            labelnames=("cluster", "node", "mountpoint", "device"),
            registry=reg,
        )
        self.node_filesystem_free_bytes = Gauge(
            "node_filesystem_free_bytes",
            "Free filesystem capacity for the node root filesystem.",
            labelnames=("cluster", "node", "mountpoint", "device"),
            registry=reg,
        )
        self.node_filesystem_avail_bytes = Gauge(
            "node_filesystem_avail_bytes",
            "Filesystem capacity available to non-root users.",
            labelnames=("cluster", "node", "mountpoint", "device"),
            registry=reg,
        )
        self.node_network_receive_bytes_total = Counter(
            "node_network_receive_bytes_total",
            "Total number of bytes received over all node interfaces.",
            labelnames=("cluster", "node", "interface"),
            registry=reg,
        )
        self.node_network_transmit_bytes_total = Counter(
            "node_network_transmit_bytes_total",
            "Total number of bytes transmitted over all node interfaces.",
            labelnames=("cluster", "node", "interface"),
            registry=reg,
        )
        self.node_disk_read_bytes_total = Counter(
            "node_disk_read_bytes_total",
            "Total bytes read from disk devices on the node.",
            labelnames=("cluster", "node", "device"),
            registry=reg,
        )
        self.node_disk_written_bytes_total = Counter(
            "node_disk_written_bytes_total",
            "Total bytes written to disk devices on the node.",
            labelnames=("cluster", "node", "device"),
            registry=reg,
        )
        self.node_temperature_celsius = Gauge(
            "node_hwmon_temp_celsius",
            "Simulated node temperature per sensor.",
            labelnames=("cluster", "node", "sensor"),
            registry=reg,
        )
        self.container_cpu_usage_seconds_total = Counter(
            "container_cpu_usage_seconds_total",
            "Cumulative CPU time consumed by the container.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.container_memory_usage_bytes = Gauge(
            "container_memory_usage_bytes",
            "Current memory usage of the container.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.container_fs_usage_bytes = Gauge(
            "container_fs_usage_bytes",
            "Filesystem usage of the container root filesystem.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.container_network_receive_bytes_total = Counter(
            "container_network_receive_bytes_total",
            "Total network receive bytes per container.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.container_network_transmit_bytes_total = Counter(
            "container_network_transmit_bytes_total",
            "Total network transmit bytes per container.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.kube_pod_status_phase = Gauge(
            "kube_pod_status_phase",
            "The pods current phase (Pending, Running, Succeeded, Failed, Unknown).",
            labelnames=("cluster", "namespace", "pod", "phase"),
            registry=reg,
        )
        self.kube_pod_container_status_restarts_total = Counter(
            "kube_pod_container_status_restarts_total",
            "Cumulative container restarts per pod container.",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.kube_pod_container_status_ready = Gauge(
            "kube_pod_container_status_ready",
            "Whether the container is currently ready (0/1).",
            labelnames=("cluster", "namespace", "pod", "container"),
            registry=reg,
        )
        self.kube_deployment_status_replicas = Gauge(
            "kube_deployment_status_replicas",
            "Deployment replica counts broken down by condition.",
            labelnames=("cluster", "namespace", "deployment", "condition"),
            registry=reg,
        )
        self.kube_daemonset_status_number_available = Gauge(
            "kube_daemonset_status_number_available",
            "Number of available pods targeted by the daemonset.",
            labelnames=("cluster", "namespace", "daemonset"),
            registry=reg,
        )
        self.kube_node_status_condition = Gauge(
            "kube_node_status_condition",
            "The condition of a Kubernetes node as reported by the API server.",
            labelnames=KSM_BASE_NODE_LABELS + ("condition", "status"),
            registry=reg,
        )
        self.kube_node_status_capacity_cpu_cores = Gauge(
            "kube_node_status_capacity_cpu_cores",
            "Node CPU core capacity from the Kubernetes API.",
            labelnames=KSM_BASE_NODE_LABELS,
            registry=reg,
        )
        self.kube_node_status_capacity_memory_bytes = Gauge(
            "kube_node_status_capacity_memory_bytes",
            "Node memory capacity from the Kubernetes API.",
            labelnames=KSM_BASE_NODE_LABELS,
            registry=reg,
        )
        self.kube_node_status_allocatable_cpu_cores = Gauge(
            "kube_node_status_allocatable_cpu_cores",
            "Node CPU allocatable cores from the Kubernetes API.",
            labelnames=KSM_BASE_NODE_LABELS,
            registry=reg,
        )
        self.kube_node_status_allocatable_memory_bytes = Gauge(
            "kube_node_status_allocatable_memory_bytes",
            "Node allocatable memory from the Kubernetes API.",
            labelnames=KSM_BASE_NODE_LABELS,
            registry=reg,
        )
        self.kube_namespace_status_phase = Gauge(
            "kube_namespace_status_phase",
            "Phase of the namespace (Active/Terminating).",
            labelnames=("cluster", "namespace", "phase"),
            registry=reg,
        )
        self.apiserver_request_total = Counter(
            "apiserver_request_total",
            "Number of apiserver requests partitioned by verb/resource/response code.",
            labelnames=("cluster", "verb", "resource", "code"),
            registry=reg,
        )
        self.apiserver_request_duration_seconds = Histogram(
            "apiserver_request_duration_seconds",
            "Histogram of apiserver request latency in seconds.",
            labelnames=("cluster", "verb", "resource"),
            buckets=(
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
            ),
            registry=reg,
        )
        self.rest_client_requests_total = Counter(
            "rest_client_requests_total",
            "Total REST client requests performed by Kubernetes controllers.",
            labelnames=("cluster", "component", "code"),
            registry=reg,
        )
        self.scheduler_schedule_attempts_total = Counter(
            "scheduler_schedule_attempts_total",
            "Number of scheduling attempts by outcome.",
            labelnames=("cluster", "result"),
            registry=reg,
        )
        self.scheduler_e2e_scheduling_duration_seconds = Histogram(
            "scheduler_e2e_scheduling_duration_seconds",
            "Scheduling latency histogram.",
            labelnames=("cluster",),
            buckets=(
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
            ),
            registry=reg,
        )
        self.controller_manager_reconcile_total = Counter(
            "controller_runtime_reconcile_total",
            "Number of reconciliations handled by controller-runtime based controllers.",
            labelnames=("cluster", "controller", "result"),
            registry=reg,
        )
        self.nginx_ingress_controller_requests = Counter(
            "nginx_ingress_controller_requests",
            "Number of ingress controller HTTP requests by status code.",
            labelnames=("cluster", "namespace", "ingress", "status"),
            registry=reg,
        )
        self.nginx_ingress_controller_upstream_latency_seconds = Histogram(
            "nginx_ingress_controller_upstream_latency_seconds",
            "Ingress upstream latency distribution.",
            labelnames=("cluster", "namespace", "ingress"),
            buckets=(
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
            ),
            registry=reg,
        )
        self.traefik_backend_requests_total = Counter(
            "traefik_backend_requests_total",
            "Requests handled by Traefik backends by status code.",
            labelnames=("cluster", "service", "code"),
            registry=reg,
        )
        self.cluster_resource_quota_cpu = Gauge(
            "kube_resourcequota_usage_cpu_cores",
            "Resource quota CPU usage by namespace.",
            labelnames=("cluster", "namespace", "quota"),
            registry=reg,
        )
        self.cluster_resource_quota_memory = Gauge(
            "kube_resourcequota_usage_memory_bytes",
            "Resource quota memory usage by namespace.",
            labelnames=("cluster", "namespace", "quota"),
            registry=reg,
        )
        self.kubelet_volume_stats_used_bytes = Gauge(
            "kubelet_volume_stats_used_bytes",
            "Volume usage reported by kubelet.",
            labelnames=("cluster", "namespace", "pod", "volume"),
            registry=reg,
        )
        self.kubelet_volume_stats_capacity_bytes = Gauge(
            "kubelet_volume_stats_capacity_bytes",
            "Volume capacity reported by kubelet.",
            labelnames=("cluster", "namespace", "pod", "volume"),
            registry=reg,
        )


__all__ = ["MetricSet"]
