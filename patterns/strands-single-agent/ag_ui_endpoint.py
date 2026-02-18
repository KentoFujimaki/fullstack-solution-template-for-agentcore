import os
import sys
from pathlib import Path
from typing import AsyncIterator

from ag_ui.core import EventType, RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder
from ag_ui_strands import StrandsAgent, StrandsAgentConfig
from fastapi import FastAPI, Header, Request
from fastapi.responses import StreamingResponse

# repo root を import path に追加して patch module を参照可能にする
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from basic_agent import create_basic_agent
from copilotkit.patches.ag_ui_strands_patch import apply_session_manager_patch

app = FastAPI(title="FAST AG-UI Endpoint")
AGUI_ENDPOINT_URL = os.environ.get("AGUI_ENDPOINT_URL", "/invocations")


@app.on_event("startup")
async def startup_event() -> None:
    # ag_ui_strands PR #798 取り込みまでの暫定パッチ
    apply_session_manager_patch()


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invocations")
async def invoke(
    input_data: RunAgentInput,
    request: Request,
    user_sub: str | None = Header(default=None, alias="User-Sub"),
    session_id: str | None = Header(default=None, alias="Session-Id"),
):
    resolved_session_id = session_id or input_data.thread_id
    resolved_user_sub = user_sub or "anonymous"

    base_agent = create_basic_agent(resolved_user_sub, resolved_session_id)
    session_manager = getattr(base_agent, "session_manager", None)

    strands_agent = StrandsAgent(
        agent=base_agent,
        name="FastStrandsAgent",
        description="FAST Strands agent over AG-UI",
        config=StrandsAgentConfig(),
        session_manager=session_manager,
    )

    accept_header = request.headers.get("accept")
    encoder = EventEncoder(accept=accept_header)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in strands_agent.run(
                input_data,
                session_manager=session_manager,
            ):
                yield encoder.encode(event)
        except Exception as exc:
            error_event = RunErrorEvent(
                type=EventType.RUN_ERROR,
                message=f"Invocation error: {exc}",
                code="INVOCATION_ERROR",
            )
            yield encoder.encode(error_event)

    return StreamingResponse(
        event_generator(),
        media_type=encoder.get_content_type(),
        headers={"x-agui-endpoint-url": AGUI_ENDPOINT_URL},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
