from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    kubeconfig: str = ""
    namespace: str = "default"
    anthropic_key: str = ""
    model: str = "claude-sonnet-4-20250514"

    @classmethod
    def load(cls) -> Config:
        cfg = cls()
        cfg.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        cfg.model = os.environ.get("KPILOT_MODEL", cfg.model)
        cfg.namespace = os.environ.get("KPILOT_NAMESPACE", cfg.namespace)
        cfg.kubeconfig = os.environ.get(
            "KUBECONFIG",
            str(Path.home() / ".kube" / "config"),
        )
        return cfg
