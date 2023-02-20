import logging, time
from flask import Flask, render_template, request
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentracing_instrumentation.request_context import get_current_span, span_in_context
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Summary, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from flask_opentracing import FlaskTracing
from jaeger_client import Config


app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

def init_tracer(svc):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        svc_name=svc,
    )
    # this call also sets opentracing.tracer
    return config.initialize_tracer()

metrics = PrometheusMetrics(app, group_by='endpoint')

# Decorate function with metric.
@s.time()
@app.route('/')
def homepage():
    with  init_tracer('frontend').start_span('main.html') as span:
        span.set_tag('message', 'Hello from main!')
        return render_template("main.html")

# Endpoint that returns 4xx error
@app.route("/client-error")
@metrics.summary('requests_by_status_4xx', 'Status Code', labels={
    'code': lambda r: '400'
})
def client_error():
    return "4xx Error", 400

# Endpoint that returns 5xx error
@app.route("/server-error")
@metrics.summary('requests_by_status_5xx', 'Status Code', labels={
    'code': lambda r: '500'
})
def server_error():
    return "5xx Error", 500

if __name__ == "__main__":
    app.run()