"""Pytest config — force the fully-local backends, seed the demo once."""
import os

os.environ.setdefault("STORE_BACKEND", "memory")
os.environ.setdefault("EMBED_PROVIDER", "hash")  # offline + deterministic for CI
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("VECTOR_PROVIDER", "memory")
os.environ.setdefault("CHANNEL_PROVIDER", "local")
os.environ.setdefault("PSP_PROVIDER", "mock")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.config import settings  # noqa: E402
from app.deps import get_repos  # noqa: E402
from app.schemas.enums import MessageType  # noqa: E402
from app.schemas.messaging import InboundMessage  # noqa: E402
from app.seed.seed_demo import seed_if_empty  # noqa: E402
from app.services.pipeline import process_inbound  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _seed():
    await seed_if_empty()


@pytest.fixture
def say():
    async def _say(text=None, iid=None, frm="+20100000123"):
        repos = get_repos()
        tenant = await repos.tenants.get_by_slug(settings.default_tenant_slug)
        msg = InboundMessage(
            tenant_id=tenant.id,
            channel="local",
            from_phone=frm,
            type=MessageType.INTERACTIVE if iid else MessageType.TEXT,
            text=text or "",
            interactive_id=iid,
        )
        return await process_inbound(msg)

    return _say
