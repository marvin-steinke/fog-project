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
    'Berlin', 'Hamburg', 'München', 'Cologne', 'Frankfurt', 'Stuttgart', 'Düsseldorf', 'Dortmund', 'Essen', 'Leipzig',
    'Bremen', 'Dresden', 'Hanover', 'Nürnberg', 'Duisburg', 'Bochum', 'Wuppertal', 'Bielefeld', 'Bonn', 'Munster',
    'Karlsruhe', 'Mannheim', 'Augsburg', 'Wiesbaden', 'Gelsenkirchen', 'Mönchengladbach', 'Braunschweig', 'Chemnitz',
    'Kiel', 'Aachen', 'Halle', 'Magdeburg', 'Freiburg', 'Krefeld', 'Lubeck', 'Oberhausen', 'Erfurt', 'Mainz',
    'Rostock', 'Kassel', 'Hagen', 'Hamm', 'Saarbrucken', 'Potsdam', 'Leverkusen', 'Oldenburg', 'Solingen', 'Herne'
]

def connect_to_redis():
    while True:
        try:
            global cache
            cache = redis.Redis(host=cache_host, port=redis_port, db=redis_db)
            break  # Connection successful, break out of the loop
        except redis.ConnectionError:
            print("Failed to connect to Redis. Retrying in 5 seconds...")
            time.sleep(5)

connect_to_redis()  # Connect to Redis initially

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    data = []
    keys = cache.keys()
    for key in keys:
        value = cache.get(key)
        city = random.choice(german_cities)
        power_average = float(value.decode())
        # Calculate price based on power average
        # Assuming price is 0.30 Euros per kWh
        cost = power_average * 0.30
        data.append({"key": key.decode(), "cityName": city, "powerAverage": power_average, "cost": cost})
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)
