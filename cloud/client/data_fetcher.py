from flask import Flask, jsonify, render_template
import redis
import random
import time

app = Flask(__name__)
cache_host = '127.0.0.1'
redis_port = 6379
redis_db = 0
cache = None

german_cities = [
  'Baden-Württemberg',
  'Bayern',
  'Berlin',
  'Brandenburg',
  'Bremen',
  'Hamburg',
  'Hessen',
  'Niedersachsen',
  'Mecklemburg-Vorpommern',
  'Nordrhein-Westphalen',
  'Rheinland-Pfalz',
  'Saarland',
  'Sachsen',
  'Sachsen-Anhalt',
  'Schleswig-Holstein',
  'Thüringen'
]

def connect_to_redis():
    """Establishes a connection to the Redis cache server.

    In case of failure, retries every 5 seconds until successful.
    """
    global cache
    while True:
        try:
            cache = redis.Redis(host=cache_host, port=redis_port, db=redis_db)
            break
        except redis.ConnectionError:
            print("Failed to connect to Redis. Retrying in 5 seconds...")
            time.sleep(5)

connect_to_redis()

@app.route('/')
def index():
    """Renders the index page.

    Returns:
        Rendered template for the index page.
    """
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """Fetches data from the Redis cache, calculates cost based on power average and 
    sends it as a json object.

    Returns:
        json: JSON object containing the key, city name, power average, and calculated cost.
    """
    data = []
    keys = cache.keys()
    for key in keys:
        value = cache.get(key)
        city = random.choice(german_cities)
        power_average = float(value.decode())
        cost = power_average * 0.30
        data.append({"key": key.decode(), "cityName": city, "powerAverage": power_average, "cost": cost})
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)
