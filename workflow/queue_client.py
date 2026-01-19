# workflow/queue_client.py
import base64
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from django.conf import settings


def _http_get_json(url: str, username: str, password: str):
    """
    urllib ile Basic Auth GET (requests yok).
    """
    creds = f"{username}:{password}".encode("utf-8")
    token = base64.b64encode(creds).decode("ascii")
    req = Request(url, headers={"Authorization": f"Basic {token}"})
    try:
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": f"HTTPError {e.code}: {e.reason}"}
    except URLError as e:
        return {"error": f"URLError: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def _rbmq_cfg():
    cfg = getattr(settings, "RABBITMQ_MANAGEMENT", {})
    url = cfg.get("URL", "http://127.0.0.1:15672")
    user = cfg.get("USERNAME", "guest")
    pwd  = cfg.get("PASSWORD", "guest")
    vhost = cfg.get("VHOST", "/")
    qname = cfg.get("QUEUE_NAME", "celery")
    return url, user, pwd, vhost, qname


def _rbmq_queues():
    """
    /api/queues (veya /api/queues/{vhost})
    """
    url, user, pwd, vhost, _ = _rbmq_cfg()
    vhost_enc = "%2F" if vhost == "/" else vhost
    api = f"{url}/api/queues/{vhost_enc}"
    return _http_get_json(api, user, pwd)


def _rbmq_overview():
    """
    /api/overview: genel özet
    """
    url, user, pwd, _, _ = _rbmq_cfg()
    api = f"{url}/api/overview"
    return _http_get_json(api, user, pwd)


def _rbmq_queue_detail(queue_name: str):
    """
    /api/queues/{vhost}/{name} tek kuyruk detayı
    """
    url, user, pwd, vhost, _ = _rbmq_cfg()
    vhost_enc = "%2F" if vhost == "/" else vhost
    api = f"{url}/api/queues/{vhost_enc}/{queue_name}"
    return _http_get_json(api, user, pwd)
