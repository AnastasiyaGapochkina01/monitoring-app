from flask import Flask, request, abort
import requests
from prometheus_client import Counter, Histogram, generate_latest, Gauge
import time
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)

SHARED_KEY = os.getenv('PROMETHEUS_HEX')

endpoint_clicks = Counter('endpoint_clicks', 'Total clicks per endpoint', ['endpoint'])
endpoint_latency = Histogram('endpoint_latency_seconds', 'Endpoint response time', ['endpoint'])
user_locations = Counter('unique_user_locations', 'Unique user locations', ['latitude', 'longitude'])
error_counter = Counter('endpoint_errors', 'Total errors per endpoint and status code', ['endpoint', 'status_code'])

def get_location(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}')
        data = response.json()
        if data['status'] == 'success':
            return [data['lat'], data['lon']]
        else:
            return [0.0, 0.0]
    except Exception as e:
        return [0.0, 0.0]

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def track_metrics(response):
    if request.path != '/favicon.ico' and request.path != '/metrics':
        # Track endpoint clicks
        endpoint_clicks.labels(endpoint=request.path).inc()

        # Track load time
        latency = time.time() - request.start_time
        endpoint_latency.labels(endpoint=request.path).observe(latency)

        # Track user locations
        location = get_location(request.remote_addr)
        user_locations.labels(latitude=location[0], longitude=location[1]).inc()
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    error_counter.labels(endpoint=request.path, status_code="500").inc()
    return "An error occurred", 500

@app.errorhandler(404)
def page_not_found(e):
    error_counter.labels(endpoint=request.path, status_code="404").inc()
    return "404 Not Found"

@app.errorhandler(403)
def page_not_found(e):
    error_counter.labels(endpoint=request.path, status_code="403").inc()
    return "403 Forbidden"

@app.route('/metrics')
def metrics():
    auth_header = request.headers.get("Authorization")
    if auth_header is None or not auth_header.startswith("Bearer "):
        abort(401)  # Unauthorized if no bearer token is provided

    token = auth_header.split(" ")[1]
    if token != SHARED_KEY:
        abort(403)  # Forbidden
    return generate_latest(), 200, {'Content-Type': 'text/plain'}


@app.route('/')
def home():
    return "Welcome to the Home Page!"

@app.route('/about')
def about():
    return "This is the about page!"

@app.route('/contact')
def contact():
    return "This is the contact page!"

@app.route('/error1')
def error1():
    raise Exception("This is a test error 1")

@app.route('/error2')
def error2():
    raise Exception("This is a test error 2")
  
