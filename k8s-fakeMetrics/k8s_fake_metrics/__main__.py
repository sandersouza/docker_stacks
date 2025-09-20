"""Command line entrypoint for the fake metrics generator."""

from __future__ import annotations

import argparse
import logging
from typing import Optional

from .config import Config
from .generator import run_from_config


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="k8s-fake-metrics",
        description="Start a Prometheus endpoint that emits synthetic Kubernetes metrics.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of update iterations to run before exiting (default: run forever).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one metrics update cycle and exit.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override the metrics HTTP port (default from METRICS_PORT env).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Override the metrics HTTP host (default from METRICS_HOST env).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Override the metrics update interval in seconds.",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=None,
        help="Override the number of clusters to simulate.",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=None,
        help="Override the number of nodes per cluster.",
    )
    parser.add_argument(
        "--pods",
        type=int,
        default=None,
        help="Override the number of pods per node.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=None,
        help="Set an explicit log level (default from LOG_LEVEL env).",
    )
    return parser


def _configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = Config.from_env()

    if args.port is not None:
        config.metrics_port = args.port
    if args.host is not None:
        config.metrics_host = args.host
    if args.interval is not None:
        config.update_interval_seconds = args.interval
    if args.clusters is not None:
        config.cluster_count = args.clusters
    if args.nodes is not None:
        config.nodes_per_cluster = args.nodes
    if args.pods is not None:
        config.pods_per_node = args.pods

    log_level = args.log_level or config.log_level
    _configure_logging(log_level)

    iterations = args.iterations
    if args.once:
        iterations = 1 if iterations is None else max(1, iterations)

    try:
        run_from_config(config, iterations=iterations)
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Received interrupt, shutting down.")


if __name__ == "__main__":  # pragma: no cover - module entrypoint
    main()
