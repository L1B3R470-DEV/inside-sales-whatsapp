import json
import os
import urllib.error
import urllib.request

from flask import Flask, jsonify, request


app = Flask(__name__)

TOPOLOGY = {
    "operationalHostRole": os.getenv("ATTENDANT_OPERATIONAL_HOST_ROLE", "PC_CLS").strip() or "PC_CLS",
    "operationalHostIp": os.getenv("ATTENDANT_OPERATIONAL_HOST_IP", "100.113.13.27").strip() or "100.113.13.27",
    "operationalDockerHostRole": os.getenv("ATTENDANT_OPERATIONAL_DOCKER_HOST_ROLE", "PC_CLS").strip() or "PC_CLS",
    "operationalDockerHostIp": os.getenv("ATTENDANT_OPERATIONAL_DOCKER_HOST_IP", "100.113.13.27").strip() or "100.113.13.27",
    "interactiveHostRole": os.getenv("ATTENDANT_INTERACTIVE_HOST_ROLE", "PC_LBN").strip() or "PC_LBN",
    "interactiveHostIp": os.getenv("ATTENDANT_INTERACTIVE_HOST_IP", "100.101.106.95").strip() or "100.101.106.95",
    "interactiveModeOnly": os.getenv("ATTENDANT_INTERACTIVE_MODE_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"},
    "rejectLbnAsRuntime": os.getenv("ATTENDANT_REJECT_LBN_AS_RUNTIME", "true").strip().lower() in {"1", "true", "yes", "on"},
    "rejectLbnDocker": os.getenv("ATTENDANT_REJECT_LBN_DOCKER", "true").strip().lower() in {"1", "true", "yes", "on"},
}

UPSTREAM = "http://127.0.0.1:8091"


def _log(event: str, **payload) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def _request_json(method: str, path: str, payload=None):
    url = f"{UPSTREAM}{path}"
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
            return resp.status, data
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(raw or "{}")
        except Exception:
            data = {"ok": False, "error": raw or str(exc)}
        return exc.code, data
    except Exception as exc:
        return 502, {"ok": False, "error": str(exc)}


@app.get("/health")
def health():
    status, data = _request_json("GET", "/health")
    return jsonify({**data, "topology": TOPOLOGY}), status


@app.get("/llm-status")
def llm_status():
    status, data = _request_json("GET", "/llm-status")
    return jsonify({**data, "topology": TOPOLOGY}), status


@app.post("/route")
def route():
    payload = request.get_json(force=True, silent=True) or {}
    payload["topology"] = TOPOLOGY
    status, data = _request_json("POST", "/route", payload)
    return jsonify({**data, "topology": TOPOLOGY}), status


@app.post("/learn-response")
def learn_response():
    payload = request.get_json(force=True, silent=True) or {}
    payload["topology"] = TOPOLOGY
    status, data = _request_json("POST", "/learn-response", payload)
    return jsonify({**data, "topology": TOPOLOGY}), status


if __name__ == "__main__":
    _log("attendant_topology_registered", **TOPOLOGY)
    _log("attendant_llm_topology_registered", **TOPOLOGY)
    app.run(host="0.0.0.0", port=8092, threaded=True)
