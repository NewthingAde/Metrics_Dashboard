import logging, time
from flask import Flask, render_template, request
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_flask_exporter import PrometheusMetrics
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from prometheus_client import Counter, Summary, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask_opentracing import FlaskTracing
from jaeger_client import Config

# Create a metric to track time spent and requests made.
s = Summary('request_processing_seconds', 'Time spent processing request')
c = Counter('my_failures', 'Description of counter')

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

<<<<<<< HEAD
=======

>>>>>>> 087756ba06775fe4a54aa576edbf84f63503dc40
def init_tracer(service):

    config = Config(
        config={
            "sampler": {"type": "const", "param": 1},
            "logging": True,
            "reporter_batch_size": 1,
        },
        service_name=service,
        validate=True,
        metrics_factory=PrometheusMetricsFactory(service_name_label=service),
    )

    # this call also sets opentracing.tracer
    return config.initialize_tracer()

tracer = init_tracer("frontend")
flask_tracer = FlaskTracing(tracer, True, app)
metrics = PrometheusMetrics(app, group_by='endpoint')

# static information as metric
metrics.info("app_info", "Application info", version="1.0.3")

logging.getLogger("").handlers = []
logging.basicConfig(format="%(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# register additional default metrics
metrics.register_default(
    metrics.counter(
        'request_by_path_counter', 'Request count by request path',
        labels={'path': lambda: request.path}
    )
)

# Adding additional items to metric.
@s.time()
@app.route("/")
def homepage():
    with tracer.start_span('homepage') as span:
        span.set_tag('message', "Homepage")
    
    return render_template("main.html")

# Endpoint that returns 4xx error
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

if __name__ == "__main__":
    app.run()
