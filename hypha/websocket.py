"""Provide an s3 interface."""
import asyncio
import logging
import sys

from fastapi import Query, WebSocket, status
from starlette.websockets import WebSocketDisconnect

from hypha.core import ClientInfo, UserInfo
from hypha.core.store import RedisRPCConnection
from hypha.core.auth import parse_reconnection_token, parse_token
import shortuuid

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger("websocket-server")
logger.setLevel(logging.INFO)

DISCONNECT_DELAY = 180


class WebsocketServer:
    """Represent an Websocket server."""

    # pylint: disable=too-many-statements

    def __init__(self, store, path="/ws", allow_origins="*") -> None:
        """Set up the websocket server."""
        if allow_origins == ["*"]:
            allow_origins = "*"

        self.store = store

        disconnected_clients = {}

        self.store = store
        app = store._app

        @app.websocket(path)
        async def websocket_endpoint(
            websocket: WebSocket,
            workspace: str = Query(None),
            client_id: str = Query(None),
            token: str = Query(None),
            reconnection_token: str = Query(None),
        ):
            async def disconnect(code):
                logger.info(f"Disconnecting {code}")
                await websocket.close(code)

            if client_id is None:
                logger.error("Missing query parameters: workspace, client_id")
                await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                return

            parent_client = None
            if reconnection_token:
                logger.info(
                    f"Reconnecting client via token: {reconnection_token[:5]}..."
                )
                user_info, ws, cid = parse_reconnection_token(reconnection_token)
                if await store.get_workspace(ws) is None:
                    logger.error(
                        "Failed to recover the connection (client: %s),"
                        " workspace has been removed: %s",
                        cid,
                        ws,
                    )
                    await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                    return
                if client_id != cid:
                    logger.error(
                        "Client ID mismatch in the reconnection token %s", client_id
                    )
                    await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                    return
                logger.info("Client successfully reconnected: %s", cid)
                disconnected_clients[client_id].cancel()
                del disconnected_clients[client_id]
            else:
                if token:
                    try:
                        user_info = parse_token(token)
                        parent_client = user_info.get_metadata("parent_client")
                        if parent_client:
                            logger.info(
                                "Registering user %s (parent_client: %s)",
                                user_info.id,
                                parent_client,
                            )
                        await store.register_user(user_info)
                    except Exception:
                        logger.error("Invalid token: %s", token)
                        await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                        return
                else:
                    user_info = UserInfo(
                        id=shortuuid.uuid(),
                        is_anonymous=True,
                        email=None,
                        parent=None,
                        roles=[],
                        scopes=[],
                        expires_at=None,
                    )
                    await store.register_user(user_info)
                    logger.info("Anonymized User connected: %s", user_info.id)

            if workspace is None:
                workspace = user_info.id
                persistent = not user_info.is_anonymous
                # If the user disconnected unexpectedly, the workspace will be preserved
                if not await store.get_user_workspace(user_info.id):
                    try:
                        await store.register_workspace(
                            dict(
                                name=user_info.id,
                                owners=[user_info.id],
                                visibility="protected",
                                persistent=persistent,
                                read_only=False,
                            ),
                            overwrite=False,
                        )
                    except Exception as exp:
                        logger.error("Failed to create user workspace: %s", exp)
                        await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                        return
            try:
                workspace_manager = await store.get_workspace_manager(
                    workspace, setup=True
                )
            except Exception as exp:
                logger.error(
                    "Failed to get workspace manager %s, error: %s", workspace, exp
                )
                await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                return
            if not await workspace_manager.check_permission(user_info):
                logger.error(
                    "Permission denied (workspace: %s,"
                    " user: %s, client: %s, scopes: %s)",
                    workspace,
                    user_info.id,
                    client_id,
                    user_info.scopes,
                )
                await disconnect(code=status.WS_1003_UNSUPPORTED_DATA)
                return

            if await workspace_manager.check_client_exists(client_id):
                logger.error(
                    "Another client with the same id %s"
                    " already connected to workspace: %s",
                    client_id,
                    workspace,
                )
                await disconnect(code=status.WS_1013_TRY_AGAIN_LATER)
                # await workspace_manager.delete_client(client_id)
                return

            await websocket.accept()

            conn = RedisRPCConnection(
                workspace_manager._redis,
                workspace_manager._workspace,
                client_id,
                user_info,
            )
            conn.on_message(websocket.send_bytes)

            await workspace_manager.register_client(
                ClientInfo(
                    id=client_id,
                    parent=parent_client,
                    workspace=workspace_manager._workspace,
                    user_info=user_info,
                )
            )

            try:
                while True:
                    data = await websocket.receive_bytes()
                    await conn.emit_message(data)
            except WebSocketDisconnect as exp:
                logger.info("Client disconnected: %s", client_id)
                try:
                    await workspace_manager.delete_client(client_id)
                except KeyError:
                    logger.info("Client already deleted: %s", client_id)
                if exp.code in [
                    status.WS_1000_NORMAL_CLOSURE,
                    status.WS_1001_GOING_AWAY,
                ]:
                    try:
                        # Clean up if the client is disconnected normally
                        await workspace_manager.delete()
                    except KeyError:
                        logger.info("Workspace already deleted: %s", workspace)
                else:
                    logger.error(
                        "Websocket (client=%s) disconnected"
                        " unexpectedly: %s (will be removed in %s seconds)",
                        client_id,
                        exp,
                        DISCONNECT_DELAY,
                    )

                    async def delayed_remove(client_id, workspace_manager):
                        try:
                            await asyncio.sleep(DISCONNECT_DELAY)
                            del disconnected_clients[client_id]
                            await workspace_manager.delete()
                        except asyncio.CancelledError:
                            pass

                    disconnected_clients[client_id] = asyncio.ensure_future(
                        delayed_remove(client_id, workspace_manager)
                    )

    async def is_alive(self):
        """Check if the server is alive."""
        return True
