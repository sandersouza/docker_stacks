"""Dynamic Prometheus metrics generated from a JSON catalog.

This module loads the list of metric names from ``metric-label.json`` and
creates lightweight Prometheus metrics for each one. The metrics are grouped
by heuristics (counter/gauge, unit, category) so that every update produces
values that resemble the semantics of the original metric.  A ``ChaosEngine``
can optionally amplify deltas to create sporadic anomalies for resource usage
metrics such as CPU, memory and network throughput.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Iterable, List, Protocol, Sequence, Tuple

from prometheus_client import CollectorRegistry, Counter, Gauge

from .ksm_labels import MetricLabelMetadata

logger = logging.getLogger(__name__)


METRIC_NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")


class UpdateMode(Enum):
    """How a metric should be updated on every iteration."""

    SET = auto()
    INCREMENT = auto()
    ACCUMULATE = auto()


class ValueMode(Enum):
    """High level behaviour that influences the generated values."""

    RANDOM = auto()
    BOOLEAN = auto()
    STATIC_ONE = auto()


class MetricCategory(Enum):
    """Categories used to decide where chaos anomalies can be injected."""

    CPU = auto()
    MEMORY = auto()
    NETWORK = auto()
    DISK = auto()
    CONNECTIONS = auto()
    OTHER = auto()


class MetricUnit(Enum):
    """Physical unit (or best-effort guess) for a metric."""

    BYTES = auto()
    BYTES_PER_SECOND = auto()
    SECONDS = auto()
    PERCENT = auto()
    COUNT = auto()
    CELSIUS = auto()
    WATTS = auto()
    GENERAL = auto()


DEFAULT_BUCKET_BOUNDS: Tuple[str, ...] = (
    "0.005",
    "0.01",
    "0.025",
    "0.05",
    "0.1",
    "0.25",
    "0.5",
    "1.0",
    "2.5",
    "5.0",
    "10.0",
    "+Inf",
)


def _guess_unit(name: str) -> MetricUnit:
    lowered = name.lower()
    if "bytes_per_second" in lowered or "bandwidth" in lowered:
        return MetricUnit.BYTES_PER_SECOND
    if "bytes" in lowered or "memory" in lowered or "mem" in lowered:
        return MetricUnit.BYTES
    if "seconds" in lowered or "latency" in lowered or "duration" in lowered:
        return MetricUnit.SECONDS
    if "percent" in lowered or "ratio" in lowered or "util" in lowered or "usage" in lowered:
        return MetricUnit.PERCENT
    if "temp" in lowered or "celsius" in lowered:
        return MetricUnit.CELSIUS
    if "watt" in lowered or "power" in lowered:
        return MetricUnit.WATTS
    return MetricUnit.COUNT


def _guess_category(name: str) -> MetricCategory:
    lowered = name.lower()
    if "cpu" in lowered:
        return MetricCategory.CPU
    if "memory" in lowered or "mem" in lowered:
        return MetricCategory.MEMORY
    if any(key in lowered for key in ("network", "net", "traffic", "bandwidth", "rx", "tx")):
        return MetricCategory.NETWORK
    if any(key in lowered for key in ("disk", "filesystem", "fs_", "io")):
        return MetricCategory.DISK
    if any(key in lowered for key in ("request", "connection", "session", "http")):
        return MetricCategory.CONNECTIONS
    return MetricCategory.OTHER


def _guess_value_mode(name: str) -> ValueMode:
    lowered = name.lower()
    if lowered.endswith("_info") or "version_info" in lowered:
        return ValueMode.STATIC_ONE
    if lowered.endswith("_labels"):
        return ValueMode.STATIC_ONE
    if any(keyword in lowered for keyword in ("allocatable", "capacity", "_bytes", "_cores")):
        return ValueMode.RANDOM
    if any(keyword in lowered for keyword in ("enabled", "ready", "healthy", "alive", "status")):
        return ValueMode.BOOLEAN
    return ValueMode.RANDOM


def _guess_update_mode(name: str) -> UpdateMode:
    if name.endswith("_bucket") or name.endswith("_count") or name.endswith("_sum"):
        return UpdateMode.ACCUMULATE
    if name.endswith("_total"):
        return UpdateMode.ACCUMULATE
    return UpdateMode.SET


def _clamp(value: float, minimum: float = 0.0, maximum: float | None = None) -> float:
    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


@dataclass(slots=True)
class MetricDefinition:
    """Configuration for a dynamically generated metric."""

    name: str
    update_mode: UpdateMode
    value_mode: ValueMode
    unit: MetricUnit
    category: MetricCategory
    labelnames: Tuple[str, ...] = ()
    labelsets: Tuple[Tuple[str, ...], ...] = ((),)

    @classmethod
    def from_name(cls, name: str) -> MetricDefinition | None:
        if not name or not METRIC_NAME_RE.match(name):
            return None
        update_mode = _guess_update_mode(name)
        value_mode = _guess_value_mode(name)
        unit = _guess_unit(name)
        category = _guess_category(name)
        if name.endswith("_bucket"):
            labelsets = tuple((bound,) for bound in DEFAULT_BUCKET_BOUNDS)
            labelnames = ("le",)
        else:
            labelnames = ()
            labelsets = ((),)
        return cls(
            name=name,
            update_mode=update_mode,
            value_mode=value_mode,
            unit=unit,
            category=category,
            labelnames=labelnames,
            labelsets=labelsets,
        )

    def create_metric(self, registry: CollectorRegistry) -> Gauge | Counter:
        help_text = f"Synthetic metric for {self.name}"
        if self.update_mode == UpdateMode.INCREMENT:
            return Counter(self.name, help_text, labelnames=self.labelnames, registry=registry)
        return Gauge(self.name, help_text, labelnames=self.labelnames, registry=registry)

    def initial_baseline(self, rng) -> float:
        if self.value_mode == ValueMode.STATIC_ONE:
            return 1.0
        if self.value_mode == ValueMode.BOOLEAN:
            return 1.0
        if self.unit == MetricUnit.BYTES:
            if self.category == MetricCategory.MEMORY:
                return rng.uniform(2e9, 32e9)
            if self.category == MetricCategory.DISK:
                return rng.uniform(50e9, 600e9)
            return rng.uniform(5e6, 5e11)
        if self.unit == MetricUnit.BYTES_PER_SECOND:
            return rng.uniform(5e5, 5e8)
        if self.unit == MetricUnit.SECONDS:
            return rng.uniform(0.01, 5.0)
        if self.unit == MetricUnit.PERCENT:
            return rng.uniform(15.0, 85.0)
        if self.unit == MetricUnit.CELSIUS:
            return rng.uniform(35.0, 85.0)
        if self.unit == MetricUnit.WATTS:
            return rng.uniform(50.0, 400.0)
        if self.category == MetricCategory.CONNECTIONS:
            return rng.uniform(50.0, 2000.0)
        return rng.uniform(5.0, 500.0)

    def initial_value(self, rng, baseline: float) -> float:
        if self.value_mode == ValueMode.STATIC_ONE:
            return 1.0
        if self.value_mode == ValueMode.BOOLEAN:
            return 1.0 if rng.random() > 0.1 else 0.0
        return baseline

    def sample_gauge(self, rng, baseline: float, previous: float) -> float:
        if self.value_mode == ValueMode.STATIC_ONE:
            return 1.0
        if self.value_mode == ValueMode.BOOLEAN:
            return 1.0 if rng.random() > 0.05 else 0.0
        spread_ratio = 0.1
        maximum = None
        minimum = 0.0
        if self.unit == MetricUnit.PERCENT:
            maximum = 100.0
            spread_ratio = 0.15
        elif self.unit == MetricUnit.CELSIUS:
            maximum = 110.0
            spread_ratio = 0.05
        elif self.unit == MetricUnit.SECONDS:
            spread_ratio = 0.4
        elif self.unit == MetricUnit.BYTES_PER_SECOND:
            spread_ratio = 0.3
        elif self.unit == MetricUnit.BYTES:
            spread_ratio = 0.2
        spread = max(baseline * spread_ratio, 0.1)
        candidate = rng.gauss(baseline, spread)
        if math.isnan(candidate):
            candidate = baseline
        return _clamp(candidate, minimum=minimum, maximum=maximum)

    def initial_accumulator(self, rng, baseline: float) -> float:
        if self.update_mode == UpdateMode.ACCUMULATE:
            return max(baseline, 0.0)
        return 0.0

    def counter_start(self, rng) -> float:
        if self.update_mode != UpdateMode.INCREMENT:
            return 0.0
        # Seed counters with a bit of activity so that dashboards are populated.
        return self.sample_increment(rng) * rng.uniform(5.0, 20.0)

    def sample_increment(self, rng) -> float:
        if self.value_mode in (ValueMode.STATIC_ONE, ValueMode.BOOLEAN):
            return 0.0
        if self.unit == MetricUnit.BYTES:
            if self.category == MetricCategory.MEMORY:
                return rng.uniform(5e6, 5e7)
            if self.category == MetricCategory.DISK:
                return rng.uniform(1e7, 1e8)
            return rng.uniform(1e5, 5e7)
        if self.unit == MetricUnit.BYTES_PER_SECOND:
            return rng.uniform(1e4, 5e6)
        if self.unit == MetricUnit.SECONDS:
            return rng.uniform(0.01, 0.5)
        if self.unit == MetricUnit.PERCENT:
            return rng.uniform(0.5, 5.0)
        if self.unit == MetricUnit.CELSIUS:
            return rng.uniform(0.1, 1.5)
        if self.unit == MetricUnit.WATTS:
            return rng.uniform(1.0, 15.0)
        if self.category == MetricCategory.CONNECTIONS:
            return rng.uniform(5.0, 150.0)
        if self.category == MetricCategory.CPU:
            return rng.uniform(0.5, 10.0)
        return rng.uniform(1.0, 25.0)

    def metric_key(self, labels: Tuple[str, ...]) -> str:
        if not labels:
            return self.name
        return f"{self.name}|{'|'.join(labels)}"


class DynamicMetric:
    """Runtime state for a generated metric."""

    def __init__(
        self,
        definition: MetricDefinition,
        metric_obj: Gauge | Counter,
        labels: Tuple[str, ...],
        rng,
    ) -> None:
        self.definition = definition
        self.metric = metric_obj.labels(*labels) if labels else metric_obj
        self.random = rng
        self.labels = labels
        self.baseline = definition.initial_baseline(rng)
        self.value = definition.initial_value(rng, self.baseline)
        if definition.update_mode == UpdateMode.SET:
            self.metric.set(self.value)
        elif definition.update_mode == UpdateMode.ACCUMULATE:
            self.value = definition.initial_accumulator(rng, self.baseline)
            self.metric.set(self.value)
        else:  # Counter
            start = definition.counter_start(rng)
            if start > 0:
                self.metric.inc(start)
                self.value = start
            else:
                self.value = 0.0
        self.metric_key = definition.metric_key(labels)

    def update(self, chaos: "ChaosEngine") -> None:
        mode = self.definition.update_mode
        if mode == UpdateMode.SET:
            new_value = self.definition.sample_gauge(self.random, self.baseline, self.value)
            new_value = chaos.apply_value(self.metric_key, self.definition.category, new_value)
            self.value = new_value
            self.metric.set(self.value)
            return
        delta = self.definition.sample_increment(self.random)
        delta = chaos.apply_delta(self.metric_key, self.definition.category, delta)
        if delta <= 0:
            return
        if mode == UpdateMode.INCREMENT:
            self.value += delta
            self.metric.inc(delta)
        else:
            self.value += delta
            self.metric.set(self.value)


class ChaosEngine:
    """Introduce sporadic anomalies on selected metric categories."""

    def __init__(
        self,
        rng,
        enabled_categories: Iterable[MetricCategory] | None = None,
        probability: float = 0.02,
        duration_range: Tuple[int, int] = (2, 5),
        multiplier_range: Tuple[float, float] = (2.0, 6.0),
    ) -> None:
        self.random = rng
        self.enabled_categories = set(enabled_categories or {
            MetricCategory.CPU,
            MetricCategory.MEMORY,
            MetricCategory.NETWORK,
            MetricCategory.DISK,
            MetricCategory.CONNECTIONS,
        })
        self.probability = probability
        self.duration_range = duration_range
        self.multiplier_range = multiplier_range
        self._active: dict[str, Tuple[int, float]] = {}

    def _multiplier(self, key: str, category: MetricCategory) -> float:
        entry = self._active.get(key)
        if entry:
            remaining, multiplier = entry
            if remaining <= 1:
                del self._active[key]
            else:
                self._active[key] = (remaining - 1, multiplier)
            return multiplier
        if category not in self.enabled_categories:
            return 1.0
        if self.random.random() < self.probability:
            duration = self.random.randint(*self.duration_range)
            multiplier = self.random.uniform(*self.multiplier_range)
            self._active[key] = (duration, multiplier)
            return multiplier
        return 1.0

    def apply_value(self, key: str, category: MetricCategory, value: float) -> float:
        multiplier = self._multiplier(key, category)
        if multiplier == 1.0:
            return value
        return _clamp(value * multiplier)

    def apply_delta(self, key: str, category: MetricCategory, delta: float) -> float:
        multiplier = self._multiplier(key, category)
        if multiplier == 1.0:
            return delta
        return delta * multiplier


class LabelMetadataProvider(Protocol):
    def metadata_for(self, metric_name: str) -> MetricLabelMetadata | None:
        ...


class DynamicMetricRegistry:
    """Manage dynamic metrics backed by Prometheus primitives."""

    def __init__(
        self,
        registry: CollectorRegistry,
        rng,
        metrics_file: Path,
        excluded_names: Sequence[str] | None = None,
        label_provider: "LabelMetadataProvider" | None = None,
    ) -> None:
        self.registry = registry
        self.random = rng
        self.metrics: List[DynamicMetric] = []
        self.label_provider = label_provider
        self._load_metrics(metrics_file, set(excluded_names or ()))

    def _load_metrics(self, metrics_file: Path, excluded: set[str]) -> None:
        names = _load_metric_names(metrics_file)
        seen: set[Tuple[str, Tuple[str, ...]]] = set()
        loaded = 0
        for name in names:
            if name in excluded:
                continue
            definition = MetricDefinition.from_name(name)
            if definition is None:
                continue
            if self.label_provider:
                metadata = self.label_provider.metadata_for(name)
                if metadata:
                    definition.labelnames = metadata.labelnames
                    definition.labelsets = metadata.labelsets
            key = (definition.name, definition.labelnames)
            if key in seen:
                continue
            seen.add(key)
            metric_obj = definition.create_metric(self.registry)
            for labelset in definition.labelsets:
                dynamic_metric = DynamicMetric(definition, metric_obj, labelset, self.random)
                self.metrics.append(dynamic_metric)
                loaded += 1
        logger.info("Registered %s dynamic metrics from %s", loaded, metrics_file)

    def update_all(self, chaos: ChaosEngine) -> None:
        for metric in self.metrics:
            metric.update(chaos)


def _load_metric_names(metrics_file: Path) -> List[str]:
    try:
        data = json.loads(metrics_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Metric label file %s not found; no dynamic metrics loaded", metrics_file)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in %s: %s", metrics_file, exc)
        return []
    if isinstance(data, dict):
        items = data.get("data")
        if isinstance(items, list):
            return [str(item) for item in items]
    if isinstance(data, list):
        return [str(item) for item in data]
    logger.warning("Unexpected structure in %s; expected list or dict with 'data'", metrics_file)
    return []


__all__ = [
    "ChaosEngine",
    "DynamicMetricRegistry",
]

