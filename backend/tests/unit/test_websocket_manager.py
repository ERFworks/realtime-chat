from app.websocket.manager import ConnectionManager
from tests.unit.fakes import FakeRedis, FakeWebSocket


def make_manager() -> ConnectionManager:
    return ConnectionManager(redis=FakeRedis())


async def test_disconnect_removes_socket_without_leak():
    manager = make_manager()

    ws_1 = FakeWebSocket()
    ws_2 = FakeWebSocket()

    await manager.connect(user_id=1, websocket=ws_1)
    await manager.connect(user_id=1, websocket=ws_2)

    manager.disconnect(user_id=1, websocket=ws_1)

    user_1_sockets = manager.active_connections.get(1, set())

    assert len(user_1_sockets) == 1
    assert ws_2 in user_1_sockets
    assert ws_1 not in user_1_sockets


async def test_disconnect_last_socket_removes_user_key():
    manager = make_manager()

    ws = FakeWebSocket()
    await manager.connect(user_id=1, websocket=ws)

    manager.disconnect(user_id=1, websocket=ws)

    assert 1 not in manager.active_connections


async def test_disconnect_unknown_user_is_noop():
    manager = make_manager()

    manager.disconnect(user_id=999, websocket=FakeWebSocket())
    assert manager.active_connections == {}


async def test_deliver_locally_sends_to_all_healthy_sockets():
    manager = make_manager()

    ws_1 = FakeWebSocket()
    ws_2 = FakeWebSocket()
    await manager.connect(user_id=1, websocket=ws_1)
    await manager.connect(user_id=1, websocket=ws_2)

    await manager._deliver_locally(1, {"type": "ping"})

    assert ws_1.sent_messages == [{"type": "ping"}]
    assert ws_2.sent_messages == [{"type": "ping"}]


async def test_deliver_locally_removes_broken_socket():
    manager = make_manager()

    good_ws = FakeWebSocket()
    broken_ws = FakeWebSocket(should_fail_on_send=True)
    await manager.connect(user_id=1, websocket=good_ws)
    await manager.connect(user_id=1, websocket=broken_ws)

    await manager._deliver_locally(1, {"type": "ping"})

    remaining = manager.active_connections.get(1, set())
    assert good_ws in remaining
    assert broken_ws not in remaining
    assert good_ws.sent_messages == [{"type": "ping"}]


async def test_deliver_locally_no_connections_is_noop():
    manager = make_manager()

    await manager._deliver_locally(1, {"type": "ping"})

    assert manager.active_connections == {}


async def test_send_to_user_never_raises_on_broken_socket():
    manager = make_manager()

    broken_ws = FakeWebSocket(should_fail_on_send=True)
    await manager.connect(user_id=1, websocket=broken_ws)

    await manager.send_to_user(1, {"type": "ping"})

    remaining = manager.active_connections.get(1, set())
    assert broken_ws not in remaining


async def test_send_to_user_publishes_to_redis_and_records_delivery():
    redis = FakeRedis()
    manager = ConnectionManager(redis=redis)

    ws = FakeWebSocket()
    await manager.connect(user_id=1, websocket=ws)

    await manager.send_to_user(1, {"type": "ping"})

    assert ws.sent_messages == [{"type": "ping"}]
    assert len(redis.published) == 1
    channel, payload = redis.published[0]
    assert channel == manager.broadcast_channel
    assert payload == f'{{"node_id": "{manager.node_id}", "user_id": 1, "message": {{"type": "ping"}}}}'


async def test_send_to_user_no_connections_still_publishes():
    redis = FakeRedis()
    manager = ConnectionManager(redis=redis)

    await manager.send_to_user(999, {"type": "ping"})

    assert len(redis.published) == 1


async def test_send_to_user_tolerates_redis_publish_failure():
    from redis.exceptions import RedisError

    class ExplodingRedis(FakeRedis):
        async def publish(self, channel: str, payload: str) -> int:
            raise RedisError("redis down")

    manager = ConnectionManager(redis=ExplodingRedis())

    ws = FakeWebSocket()
    await manager.connect(user_id=1, websocket=ws)

    await manager.send_to_user(1, {"type": "ping"})
    assert ws.sent_messages == [{"type": "ping"}]
