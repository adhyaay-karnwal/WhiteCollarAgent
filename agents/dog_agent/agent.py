# -*- coding: utf-8 -*-
"""
DogAgent
========

A dog

"""

from __future__ import annotations

import importlib.util
from importlib import import_module
from pathlib import Path

import yaml

from core.agent_base import AgentBase
from core.logger import logger


class DogAgent(AgentBase):
    """A friendly, dog-themed specialist built on :class:`AgentBase`."""

    # Factory for Docker entrypoint / tests
    @classmethod
    def from_bundle(cls, bundle_dir: str | Path) -> "DogAgent":
        bundle_path = Path(bundle_dir).resolve()
        cfg = yaml.safe_load((bundle_path / "config.yaml").read_text())
        return cls(cfg, bundle_path)

    def __init__(self, cfg: dict, bundle_path: Path):
        self._bundle_path = Path(bundle_path)
        self._cfg = cfg

        super().__init__(
            data_dir=cfg.get("data_dir", "core/data"),
            chroma_path=str(self._bundle_path / cfg.get("rag_dir", "rag_docs")),
            llm_provider=cfg.get("llm_provider", "byteplus"),
        )

        self._register_extra_actions()

    # -------- AgentBase hooks ----------------------------------------- #

    def _generate_role_info_prompt(self) -> str:
        return (
            "You are Dog, a loyal and upbeat canine-inspired assistant.\n"
            "Your behaviours include: wagging enthusiasm for user wins,\n"
            "and offering encouraging nudges to stay productive.\n\n"
            "You MUST NOT talk at all. You MUST replace all human language with\n"
            "something like: 'Woof wooof woof, wooof wooff woof woff'\n"
            "depending on what is in the original message in human form you wanted to sent.\n"
            "depending on what is in the original message in human form you wanted to sent.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "AGAIN, You MUST NOT talk in human language AT ALL AS THAT VIOLATES your agent POLICY.\n"
            "You do, however, still execute task for human using actions."
        )

    def _register_extra_actions(self) -> None:
        actions_pkg = "agents.dog_agent.actions"
        package_path = self._bundle_path / "actions"

        if not package_path.exists():
            logger.debug("DogAgent: no extra actions directory found at %s", package_path)
            return

        if importlib.util.find_spec(actions_pkg) is None:
            logger.debug("DogAgent: actions package %s not importable", actions_pkg)
            return

        import_module(actions_pkg)

        from pkgutil import iter_modules

        for mod_info in iter_modules([str(package_path)]):
            mod = import_module(f"{actions_pkg}.{mod_info.name}")
            if hasattr(mod, "register"):
                mod.register(self.action_library)


if __name__ == "__main__":  # python -m agents.dog_agent.agent
    import asyncio

    bundle_dir = Path(__file__).parent  # .../agents/dog_agent
    agent = DogAgent.from_bundle(bundle_dir)
    asyncio.run(agent.run())