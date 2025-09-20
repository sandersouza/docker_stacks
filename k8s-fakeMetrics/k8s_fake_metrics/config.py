"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        """Fallback stub when python-dotenv is not installed."""

        return False


@dataclass(slots=True)
class Config:
    """Runtime configuration parsed from environment variables."""

    cluster_count: int = 1
    nodes_per_cluster: int = 3
    pods_per_node: int = 8
    update_interval_seconds: float = 5.0
    metrics_port: int = 8000
    metrics_host: str = "0.0.0.0"
    namespaces_per_cluster: int = 4
    containers_per_pod_min: int = 1
    containers_per_pod_max: int = 3
    random_seed: Optional[int] = None
    deployments_per_namespace: int = 2
    enable_ingress_controllers: bool = True
    enable_traefik_metrics: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables and defaults."""

        load_dotenv()

        def _get_int(name: str, default: int) -> int:
            value = os.getenv(name)
            if value is None:
                return default
            try:
                return int(value)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise ValueError(f"Invalid integer for {name}: {value}") from exc

        def _get_float(name: str, default: float) -> float:
            value = os.getenv(name)
            if value is None:
                return default
            try:
                return float(value)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise ValueError(f"Invalid float for {name}: {value}") from exc

        def _get_bool(name: str, default: bool) -> bool:
            value = os.getenv(name)
            if value is None:
                return default
            return value.strip().lower() in {"1", "true", "yes", "on"}

        random_seed: Optional[int]
        random_seed_value = os.getenv("RANDOM_SEED")
        if random_seed_value is not None:
            try:
                random_seed = int(random_seed_value)
            except ValueError as exc:  # pragma: no cover - defensive programming
                raise ValueError(
                    f"Invalid integer for RANDOM_SEED: {random_seed_value}"
                ) from exc
        else:
            random_seed = None

        return cls(
            cluster_count=_get_int("CLUSTER_COUNT", 1),
            nodes_per_cluster=_get_int("NODES_PER_CLUSTER", 3),
            pods_per_node=_get_int("PODS_PER_NODE", 8),
            update_interval_seconds=_get_float("UPDATE_INTERVAL_SECONDS", 5.0),
            metrics_port=_get_int("METRICS_PORT", 8000),
            metrics_host=os.getenv("METRICS_HOST", "0.0.0.0"),
            namespaces_per_cluster=_get_int("NAMESPACES_PER_CLUSTER", 4),
            containers_per_pod_min=_get_int("CONTAINERS_PER_POD_MIN", 1),
            containers_per_pod_max=_get_int("CONTAINERS_PER_POD_MAX", 3),
            random_seed=random_seed,
            deployments_per_namespace=_get_int("DEPLOYMENTS_PER_NAMESPACE", 2),
            enable_ingress_controllers=_get_bool("ENABLE_INGRESS_CONTROLLERS", True),
            enable_traefik_metrics=_get_bool("ENABLE_TRAEFIK_METRICS", False),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


__all__ = ["Config"]
