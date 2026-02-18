"""ag_ui_strands の SessionManager 未対応を補う一時パッチ。

PR #798 が取り込まれるまで利用する。
"""

from __future__ import annotations

from functools import wraps
from typing import Any

from ag_ui_strands import StrandsAgent, StrandsAgentConfig
from strands import Agent as StrandsAgentCore

_ORIGINAL_INIT = StrandsAgent.__init__
_ORIGINAL_RUN = StrandsAgent.run
_PATCH_APPLIED_ATTR = "_copilotkit_session_manager_patch_applied"


def _resolve_session_manager(
    session_manager: Any,
    thread_id: str,
    input_data: Any,
) -> Any:
    """session_manager が callable の場合は thread ごとに解決する。"""
    resolved = session_manager
    if callable(session_manager):
        try:
            resolved = session_manager(thread_id=thread_id, input_data=input_data)
        except TypeError:
            resolved = session_manager(thread_id)
    return resolved


def apply_session_manager_patch() -> None:
    """StrandsAgent に session_manager の受け渡しを追加する。"""
    if getattr(StrandsAgent, _PATCH_APPLIED_ATTR, False):
        return

    @wraps(_ORIGINAL_INIT)
    def patched_init(
        self: StrandsAgent,
        agent: StrandsAgentCore,
        name: str,
        description: str = "",
        config: StrandsAgentConfig | None = None,
        session_manager: Any = None,
    ) -> None:
        self._session_manager = (
            session_manager
            if session_manager is not None
            else getattr(agent, "session_manager", None)
        )
        _ORIGINAL_INIT(self, agent, name, description, config)

    @wraps(_ORIGINAL_RUN)
    async def patched_run(
        self: StrandsAgent,
        input_data: Any,
        session_manager: Any = None,
    ):
        thread_id = getattr(input_data, "thread_id", None) or "default"
        effective_session_manager = (
            session_manager
            if session_manager is not None
            else getattr(self, "_session_manager", None)
        )

        if thread_id not in self._agents_by_thread:
            agent_kwargs = dict(getattr(self, "_agent_kwargs", {}))
            resolved_session_manager = _resolve_session_manager(
                effective_session_manager,
                thread_id,
                input_data,
            )
            if resolved_session_manager is not None:
                agent_kwargs["session_manager"] = resolved_session_manager

            self._agents_by_thread[thread_id] = StrandsAgentCore(
                model=self._model,
                system_prompt=self._system_prompt,
                tools=self._tools,
                **agent_kwargs,
            )

        async for event in _ORIGINAL_RUN(self, input_data):
            yield event

    StrandsAgent.__init__ = patched_init
    StrandsAgent.run = patched_run
    setattr(StrandsAgent, _PATCH_APPLIED_ATTR, True)


__all__ = ["apply_session_manager_patch"]
