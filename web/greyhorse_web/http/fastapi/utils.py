from starlette.requests import Request
from starlette.websockets import WebSocket

from greyhorse_web.schemas import ClientInfo


def get_client_info(request: Request | WebSocket) -> ClientInfo:
    client_ip = request.client.host.strip()
    client_port = request.client.port
    user_agent = request.headers.get('user-agent')
    referrer = request.headers.get('referer')

    x_real_ip = request.headers.get('x-real-ip', '').strip()
    x_fwd_ip = request.headers.get('x-forwarded-for', '').split(',')
    if isinstance(x_fwd_ip, tuple | list) and len(x_fwd_ip) > 0:
        x_fwd_ip = x_fwd_ip[0].strip()
    ip_current = x_fwd_ip or x_real_ip or client_ip

    return ClientInfo(
        ip=ip_current,
        port=client_port,
        host=request.base_url.netloc,
        agent=user_agent,
        referrer=referrer,
        scheme=request.base_url.scheme,
    )
