"""Test ASGI services."""
from pathlib import Path
import asyncio

import pytest
import requests
from imjoy_rpc.hypha.websocket_client import connect_to_server

from . import WS_SERVER_URL, SERVER_URL

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_asgi(fastapi_server):
    """Test the ASGI gateway apps."""
    api = await connect_to_server({"name": "test client", "server_url": WS_SERVER_URL})
    workspace = api.config["workspace"]

    # Test plugin with custom template
    controller = await api.get_service("server-apps")

    source = (
        (Path(__file__).parent / "testASGIWebPythonPlugin.imjoy.html")
        .open(encoding="utf-8")
        .read()
    )
    config = await controller.launch(
        source=source,
        wait_for_service="hello-fastapi",
    )
    service = await api.get_service(
        {"workspace": config.workspace, "id": "hello-fastapi"}
    )
    assert "serve" in service

    response = requests.get(f"{SERVER_URL}/{workspace}/apps/hello-fastapi/")
    assert response.ok
    assert response.json()["message"] == "Hello World"

    await controller.stop(config.id)


async def test_functions(fastapi_server):
    """Test the functions service."""
    api = await connect_to_server({"name": "test client", "server_url": WS_SERVER_URL})
    workspace = api.config["workspace"]

    # Test plugin with custom template
    controller = await api.get_service("server-apps")

    source = (
        (Path(__file__).parent / "testFunctionsPlugin.imjoy.html")
        .open(encoding="utf-8")
        .read()
    )
    config = await controller.launch(
        source=source,
        wait_for_service="hello-functions",
    )

    service = await api.get_service(
        {"workspace": config.workspace, "id": "hello-functions"}
    )
    assert "hello-world" in service

    response = requests.get(
        f"{SERVER_URL}/{workspace}/apps/hello-functions/hello-world"
    )
    assert response.ok
    assert response.json()["message"] == "Hello World"

    response = requests.get(
        f"{SERVER_URL}/{workspace}/apps/hello-functions/hello-world/"
    )
    assert response.ok

    response = requests.get(
        f"{SERVER_URL}/{workspace}/apps/hello-functions/",
        headers={"origin": "http://localhost:3000"},
    )
    assert response.ok
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.content == b"Home page"

    response = requests.get(f"{SERVER_URL}/{workspace}/apps/hello-functions")
    assert response.ok
    assert response.content == b"Home page"

    await controller.stop(config.id)
