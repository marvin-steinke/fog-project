# fog-project

This project simulates a distributed power system where power data from
different households is streamed in real-time. The data is processed and
averaged over a 5-second window. The simulation is coordinated by Mosaik, a
co-simulation framework, and uses Apache Kafka for handling real-time data.
The averaged data gets queued into a SQLite database and arranged into a schema
that allows for tracking of each inserted tuple. The edge-server manages the 
messaging of the queued data by continously checking connectivity to the 
cloud-server and buffering the generated tuples into the sockets. 
The cloud-server caches each received tuple and generates the according
postal code for the household and sents this back to the edge-server that 
eventually stores this in it's database and marks the tuple as acknolwedged. 
The initial start of the cloud-server triggers a backend running on the same
hosts that fetches key-value-pairs out of the cache and visualizes them on a 
charts, accessible on the web.

## Project Structure

```
.
├── cloud
│   ├── tf_gcp_node
        ├── terraform file to create  the gcp instance
    ├── gcloud_deployment
        ├── cloud_server.py
        ├── Dockerfile
        ├── requirements.txt
        ├── copy_to_cloud.sh
        ├── client
            ├── frontend
            ├── static
                ├── css
                    ├── main.css
                ├── js
                    ├── main.js
                ├── visuals
                    ├── .png files
            ├── templates
                ├── index.html
            ├── backend
                ├── data_fetcher.py
├── documents
└── edge
    ├── config.ini
    ├── data
    ├── docker-compose.yml
    ├── Dockerfile
    ├── edge_server.py
    ├── main.py
    ├── requirements.txt
    ├── local_db
    │   └── db_operations.py
    └── simulator
        ├── collector.py
        ├── household.py
        └── kafka_adapter.py

```

Edge Component:

- `data`: Based on the original data from ["Gem House Opendata: German Electricity Consumption in Many Households Over Three Years 2018-2020 (Fresh Energy)"](https://ieee-dataport.org/node/4576/). The data is reduced to a one hour window and made compatible with the simulation environment by adding a title and converting the timestamp from `YYYY-MM-DD HH:mm:ss.SSS` to `YYYY-MM-DD HH:mm:ss`.

- `household.py`: Contains the `Household` simulator that generates power data based on the provided CSV file.
- `kafka_adapter.py`: Contains the `KafkaAdapter` and `KafkaAdapterModel` classes, responsible for connecting the Mosaik simulation with the Kafka data stream.
- `collector.py`: Contains the `Collector` simulator that collects all power data.
- `main.py`: Contains the main function for starting the simulation.
- `edge_server.py`: Contains the `EdgeServer` class for reading, writing and inserting the produced data from the Kafka topics into sqlite. Furthermore 3 concurrent threads are used to continously check connectivity, publish the data read from the kafka topics and the sqlite database and subscribing to messages from the cloud-server.
- `db_operations`: Contains the database operations used by the `ÈdgeServer` create a schema, insert tuples coming from the kafka producer thread, fetch newly inserted & lost data by tracking and checking the sent flag, as well as inserting the received messages by the cloud-server.

### Usage

1. Set up your Kafka and Zookeeper services. You can use Docker Compose with the provided `docker-compose.yml` file:

    ```
    docker-compose up -d
    ```

2. Configure the simulation parameters in the `config.ini` file, including the start and end time of the simulation, and the address of the Kafka server.

3. Run the main Python script:

    ```
    python main.py
    ```

## Dependencies

If prefered use a virtualenv to install the necessary dependencies to run the edge node.

- Python 3.8 or later
- Mosaik
- Apache Kafka
- SQLite
- pynng 
- Docker and Docker Compose (for Kafka and Zookeeper)

Cloud Component

The cloud node runs the `cloud_server.py` file to asynchronously interact with the edge component through 3 pynng sockets making use of both Pub/Sub and Req/Rep message patterns. While the cloud node subscribes to the data from the Kafka server and cashes received data into a redis-cache it also publishes the generated postal codes to the edge-server and triggers the `data_fetcher.py`script in the backend to fetch data out of the cache to provide a RESTful API for an ajax-engine running `main.js` in the frontend. The cloud-server reacts to continous heartbeat messages to provide the necessary reliability and disconnection handling in the case of network failures or application crashes. The cloud server can be run either directly or using Docker with the provided `Dockerfile`.

- `cloud_server.py`: Contains asynchronous (implemented with asyncio & pynng) functions that reply to heartbeat messages by the edge-server, subscribing to the power data and publishing the generated postal codes back to the edge-server. The received data gets cached to redis-server instance on the same host.

- `data_fetcher.py`: Contains the flask backend script to fetch data out of the redis-cache, associate one of sixteen german states with the id of the received data tuple and providing a REST API for the frontend to present the data values on a webpage. 
- `main.js`+ `index.html`+ `main.css`: Contains a simple frontend logic to access the key-value-pairs using ajax and implements a bar-chart of the Chart.js library to visualize the average power-consumption per german state in annual kw/h + the associated price based on an assumption.

### Usage

1. Create a GCP instance by running the following commands out of the `tf_gcp_node`folder:

    ```
    terraform init
    terraform apply
    ```
2. Pull or copy the `Dockerfile` to the GCP instance and run:

    ```
    docker build -t myapp:latest
    docker run -P myapp:latest
    ```

    OR

3. Copy the files out of `gcloud_deployment`to the GCP instance and then run:

    ```
    python cloud_server.py
    ```

4. Access the frontend by:

    ```
    http://IP-of-the-cloud-server:5006
    ```

### Dependencies

Dependencies for the cloud server can be installed from the `requirements.txt` file in the `cloud/gcloud_deployment` directory.

- Docker (if preferred, but not necessary)
- redis-server
- redis
- flask 
- pynng