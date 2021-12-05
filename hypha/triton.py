"""Provide the triton proxy."""
import random

import httpx
from fastapi import APIRouter, Depends, Request, Response

from hypha.core.auth import login_optional
from hypha.core.interface import CoreInterface


class TritonProxy:
    """A proxy for accessing triton inference servers."""

    def __init__(self, core_interface: CoreInterface, triton_servers: str) -> None:
        """Initialize the triton proxy."""
        # pylint: disable=broad-except
        router = APIRouter()
        self.core_interface = core_interface
        self.servers = list(filter(lambda x: x.strip(), triton_servers))
        self.servers = list(map(lambda x: x.rstrip("/"), self.servers))

        @router.get("/models/{path:path}")
        @router.post("/models/{path:path}")
        async def triton_proxy(
            path: str,
            request: Request,
            response: Response,
            user_info: login_optional = Depends(login_optional),
        ):
            """Route for listing all the models."""
            headers = dict(request.headers.items())
            # with the host header, the server will return 404
            del headers["host"]
            params = request.query_params.multi_items()
            server = random.choice(self.servers)
            url = f"{server}/{path}"
            async with httpx.AsyncClient() as client:
                if request.method == "GET":
                    proxy = await client.get(url, params=params, headers=headers)
                    response.headers.update(proxy.headers)
                    response.body = proxy.content
                    response.status_code = proxy.status_code
                    return response

                if request.method == "POST":

                    async def request_streamer():
                        async for chunk in request.stream():
                            yield chunk

                    # Use a stream to access raw request body (with compression)
                    async with client.stream(
                        "POST",
                        url,
                        data=request_streamer(),
                        params=params,
                        headers=headers,
                    ) as proxy:
                        response.headers.update(proxy.headers)
                        body = b""
                        async for chunk in proxy.aiter_raw():
                            body += chunk
                        response.body = body
                        response.status_code = proxy.status_code
                        return response

        core_interface.register_router(router)
