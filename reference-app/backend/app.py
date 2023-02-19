# Import packages 
import pymongo, logging, random, time
from flask_pymongo import PyMongo
from flask import Flask, request, jsonify
from flask_opentracing import FlaskTracing
from jaeger_client import Config
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Summary, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

logging.getLogger("").handlers = []
logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

metrics = PrometheusMetrics(app)

# Metrics Static information 
metrics.info("app_info", "Application info", version="1.0.3")

app = Flask(__name__)

app.config["MONGO_DBNAME"] = "example-mongodb"
app.config[
    "MONGO_URI"
] = "mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb"

mongo = PyMongo(app)

# Add prometheus middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Additional default metrics
metrics.register_default(
    metrics.counter(
        'request_by_path_counter', 'Request count by request path',
        labels={'path': lambda: request.path}
    )
)

# Function for tracer
def init_tracer(svc):

    config = Config(
        config={
            "sampler": {"type": "const", "param": 1},
            "logging": True,
            "reporter_batch_size": 1,
        },
        svc_name=svc,
        validate=True,
        metrics_factory=PrometheusMetricsFactory(service_name_label=svc),
    )
    return config.initialize_tracer()

svc_span =  FlaskTracing(init_tracer("backend"), True, app).get_span()

# This function is to decorate with metrics
@s.time()
@app.route("/")
def homepage():
    result = 'Hello World'

    with init_tracer("backend").start_span('homepage', child_of=svc_span) as span:
        span.set_tag('message', result)
        return result

# This function is to decorate with metrics
@s.time()
@app.route("/api")
def my_api():
    result = "something"

    with init_tracer("backend").start_span('api', child_of=svc_span) as span:
        # add some delay
        for i in range(3):
            process_request_with_random_delay(random.random())

        span.set_tag('message', result)
        return jsonify(response=result)

# This function is to decorate with metrics
@s.time()
@c.count_exceptions()
@app.route("/star", methods=["POST"])
def add_star():
    output = {}

    with init_tracer("backend").start_span('star') as span:
        try:
            star = mongo.db.stars

            name = request.json["name"]
            distance = request.json["distance"]
            star_id = star.insert({"name": name, "distance": distance})
            new_star = star.find_one({"_id": star_id})
            output = {"name": new_star["name"], "distance": new_star["distance"]}

            span.set_tag('output', output)
        except:
            span.set_tag('error', 'Error: Unable to process request')

    return jsonify({"result": output})

# This function is to decorate with metrics
@s.time()
def process_request_with_random_delay(t):
    time.sleep(t)

# Register endpoint that returns 4xx error
@app.route("/client-error")
@metrics.summary('requests_by_status_4xx', 'Status Code', labels={
    'code': lambda r: '400'
})
def client_error():
    return "4xx Error", 400

# Register endpoint that returns 5xx error
@app.route("/server-error")
@metrics.summary('requests_by_status_5xx', 'Status Code', labels={
    'code': lambda r: '500'
})
def server_error():
    return "5xx Error", 500

# Create a metric to track time spent and requests made.
s = Summary('request_processing_seconds', 'Time spent processing request')
c = Counter('my_failures', 'Description of counter')

if __name__ == "__main__":
    app.run()
