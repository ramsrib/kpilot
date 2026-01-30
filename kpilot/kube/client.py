from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kubernetes import client as k8s_client, config as k8s_config


@dataclass
class KubeInfo:
    cluster_name: str = ""
    context_name: str = ""
    namespace: str = "default"


class KubeClient:
    """Wraps the kubernetes Python client for resource listing."""

    def __init__(self, kubeconfig: str, namespace: str = "default") -> None:
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.info = KubeInfo(namespace=namespace)
        self._core: k8s_client.CoreV1Api | None = None
        self._apps: k8s_client.AppsV1Api | None = None

    def connect(self) -> None:
        """Load kubeconfig and create API clients."""
        try:
            contexts, active = k8s_config.list_kube_config_contexts(
                config_file=self.kubeconfig
            )
            if active:
                self.info.context_name = active.get("name", "")
                ctx = active.get("context", {})
                self.info.cluster_name = ctx.get("cluster", "")
                ns = ctx.get("namespace", "")
                if ns and self.namespace == "default":
                    self.namespace = ns
                    self.info.namespace = ns

            k8s_config.load_kube_config(config_file=self.kubeconfig)
            self._core = k8s_client.CoreV1Api()
            self._apps = k8s_client.AppsV1Api()
        except Exception:
            # Allow running without a cluster (UI still works)
            self._core = None
            self._apps = None

    @property
    def connected(self) -> bool:
        return self._core is not None

    def set_namespace(self, ns: str) -> None:
        self.namespace = ns
        self.info.namespace = ns

    # ── Resource listing ──────────────────────────────────────────

    def list_pods(
        self, namespace: str = "", label_selector: str = ""
    ) -> tuple[list[str], list[list[str]]]:
        ns = namespace or self.namespace
        if not self._core:
            return ["ERROR"], [["Not connected to cluster"]]
        kwargs: dict[str, Any] = {}
        if label_selector:
            kwargs["label_selector"] = label_selector
        pods = self._core.list_namespaced_pod(ns, **kwargs)
        headers = ["NAME", "READY", "STATUS", "RESTARTS", "AGE"]
        rows = []
        for pod in pods.items:
            ready = sum(
                1
                for cs in (pod.status.container_statuses or [])
                if cs.ready
            )
            total = len(pod.spec.containers)
            restarts = sum(
                cs.restart_count
                for cs in (pod.status.container_statuses or [])
            )
            rows.append([
                pod.metadata.name,
                f"{ready}/{total}",
                pod.status.phase or "Unknown",
                str(restarts),
                _age(pod.metadata.creation_timestamp),
            ])
        return headers, rows

    def list_services(self, namespace: str = "") -> tuple[list[str], list[list[str]]]:
        ns = namespace or self.namespace
        if not self._core:
            return ["ERROR"], [["Not connected to cluster"]]
        svcs = self._core.list_namespaced_service(ns)
        headers = ["NAME", "TYPE", "CLUSTER-IP", "PORTS", "AGE"]
        rows = []
        for svc in svcs.items:
            ports = ",".join(
                f"{p.port}/{p.protocol}" for p in (svc.spec.ports or [])
            )
            rows.append([
                svc.metadata.name,
                svc.spec.type or "",
                svc.spec.cluster_ip or "",
                ports,
                _age(svc.metadata.creation_timestamp),
            ])
        return headers, rows

    def list_deployments(
        self, namespace: str = ""
    ) -> tuple[list[str], list[list[str]]]:
        ns = namespace or self.namespace
        if not self._apps:
            return ["ERROR"], [["Not connected to cluster"]]
        deps = self._apps.list_namespaced_deployment(ns)
        headers = ["NAME", "READY", "UP-TO-DATE", "AVAILABLE", "AGE"]
        rows = []
        for d in deps.items:
            s = d.status
            rows.append([
                d.metadata.name,
                f"{s.ready_replicas or 0}/{s.replicas or 0}",
                str(s.updated_replicas or 0),
                str(s.available_replicas or 0),
                _age(d.metadata.creation_timestamp),
            ])
        return headers, rows

    def list_namespaces(self) -> tuple[list[str], list[list[str]]]:
        if not self._core:
            return ["ERROR"], [["Not connected to cluster"]]
        nss = self._core.list_namespace()
        headers = ["NAME", "STATUS", "AGE"]
        rows = []
        for ns in nss.items:
            rows.append([
                ns.metadata.name,
                ns.status.phase or "",
                _age(ns.metadata.creation_timestamp),
            ])
        return headers, rows

    def list_nodes(self) -> tuple[list[str], list[list[str]]]:
        if not self._core:
            return ["ERROR"], [["Not connected to cluster"]]
        nodes = self._core.list_node()
        headers = ["NAME", "STATUS", "ROLES", "AGE", "VERSION"]
        rows = []
        for node in nodes.items:
            status = "NotReady"
            for cond in node.status.conditions or []:
                if cond.type == "Ready" and cond.status == "True":
                    status = "Ready"
            roles = [
                lbl.removeprefix("node-role.kubernetes.io/")
                for lbl in (node.metadata.labels or {})
                if lbl.startswith("node-role.kubernetes.io/")
                and lbl != "node-role.kubernetes.io/"
            ] or ["<none>"]
            rows.append([
                node.metadata.name,
                status,
                ",".join(roles),
                _age(node.metadata.creation_timestamp),
                node.status.node_info.kubelet_version,
            ])
        return headers, rows


def _age(ts) -> str:
    if ts is None:
        return "<unknown>"
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    delta = now - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else now - ts
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"
