"""All suite tests are offline; provider integration runs are explicit commands."""
import pytest

@pytest.fixture(autouse=True)
def no_unmocked_http(monkeypatch):
    import httpx
    async def blocked_async(*args, **kwargs):
        raise AssertionError('Unmocked async HTTP in offline test; patch the shared adapter')
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', blocked_async)
