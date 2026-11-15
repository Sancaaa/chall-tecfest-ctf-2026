import time
import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Request size and timeout limits for safe SSRF operations
MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MB
REQUEST_TIMEOUT = 5.0

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/tools/connection", methods=["GET"])
def connection_tester():
    return render_template("tester.html")

@app.route("/status", methods=["GET"])
def service_status():
    services = [
        {
            "name": "archive-api",
            "type": "Internal Document Archive",
            "subnet": "VPC-Private (Cluster Only)",
            "status": "Operational",
            "health": 100,
            "latency": "1.2 ms"
        },
        {
            "name": "auth-gateway",
            "type": "Identity & Access Control",
            "subnet": "VPC-Private (Cluster Only)",
            "status": "Operational",
            "health": 100,
            "latency": "0.8 ms"
        },
        {
            "name": "relaydesk-web",
            "type": "Operator Web Interface",
            "subnet": "Public Ingress Edge",
            "status": "Operational",
            "health": 100,
            "latency": "0.3 ms"
        },
        {
            "name": "event-relay",
            "type": "Asynchronous Message Bus",
            "subnet": "VPC-Private (Cluster Only)",
            "status": "Operational",
            "health": 99,
            "latency": "2.4 ms"
        }
    ]
    return render_template("status.html", services=services)

@app.route("/help/networking", methods=["GET"])
def help_networking():
    return render_template("help_networking.html")

@app.route("/api/check", methods=["POST"])
def check_connection():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({
            "success": False,
            "status": 0,
            "error": "Request body must be valid JSON."
        }), 400

    target_url = str(payload.get("url", "")).strip()
    method = str(payload.get("method", "GET")).strip().upper()
    user_headers = payload.get("headers", {})
    body = payload.get("body", "")

    if not target_url:
        return jsonify({
            "success": False,
            "status": 0,
            "error": "The target 'url' parameter is required."
        }), 400

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        return jsonify({
            "success": False,
            "status": 0,
            "error": "Unsupported scheme. Only http:// and https:// URLs are allowed."
        }), 400

    if method not in ["GET", "POST"]:
        return jsonify({
            "success": False,
            "status": 0,
            "error": "Method not allowed. Connection tester supports GET and POST only."
        }), 400

    # Sanitize and forward headers
    forward_headers = {}
    if isinstance(user_headers, dict):
        for key, value in user_headers.items():
            if isinstance(key, str) and isinstance(value, str):
                forward_headers[key.strip()] = value.strip()

    # Prepare body payload
    request_data = None
    if method == "POST":
        if isinstance(body, str):
            request_data = body.encode("utf-8")
        elif isinstance(body, (bytes, bytearray)):
            request_data = body

    start_time = time.perf_counter()
    try:
        response = requests.request(
            method=method,
            url=target_url,
            headers=forward_headers,
            data=request_data,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True
        )

        # Read limited chunk to protect buffer
        raw_content = response.raw.read(MAX_RESPONSE_BYTES, decode_content=True)
        try:
            text_body = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            text_body = raw_content.decode("latin-1", errors="replace")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Filter safe response headers for client display
        resp_headers = {}
        for k, v in response.headers.items():
            resp_headers[k.lower()] = v

        return jsonify({
            "success": True,
            "status": response.status_code,
            "headers": resp_headers,
            "body": text_body,
            "elapsed_ms": elapsed_ms
        }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "status": 0,
            "error": f"Connection timed out after {REQUEST_TIMEOUT} seconds."
        }), 200
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "status": 0,
            "error": f"Network transport error: {str(e)}"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "status": 0,
            "error": f"Internal execution failure: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

