import pymongo, logging, opentracing
from flask_pymongo import PyMongo
from jaeger_client import Config
from flask import Flask, render_template, request, jsonify
from opentracing_instrumentation.request_context import get_current_span, span_in_context
from flask_opentracing import FlaskTracer
from jaeger_client.metrics.prometheus import PrometheusMetricsFactory
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'example-mongodb'
app.config['MONGO_URI'] = 'mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb'
#app.config['MONGO_URI'] = 'localhost:27017'

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

mongo = PyMongo(app)
metrics = PrometheusMetrics(app,group_by='endpoint')

# Endpoint for home 
@app.route('/')
def homepage():
    with init_tracer('backend-trace').start_span('hello world') as span:
         val = "Hello World"
         span.set_tag('message', val)
         return(val)

# Endpoint for Api
@app.route('/api')
def my_api():
    with init_tracer('backend-trace').start_span('api') as span:
        answer = "something"
        span.set_tag('message', answer)
    return jsonify(repsonse=answer)

# Endpoint for star
@app.route('/star', methods=['POST'])
def add_star():
        with init_tracer('backend-trace').start_span('star') as span:
            star = mongo.db.stars
            name = request.json['name']
            distance = request.json['distance']
            star_id = star.insert({'name': name, 'distance': distance})
            new_star = star.find_one({'_id': star_id })
            output = {'name' : new_star['name'], 'distance' : new_star['distance']}
            span.set_tag('status', 'OK')
        return jsonify({'result' : output})

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