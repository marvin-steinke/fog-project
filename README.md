# fog-project

This project simulates a distributed power system where power data from
different households is streamed in real-time. The data is processed and
averaged over a 30-second window. The simulation is coordinated by Mosaik, a
co-simulation framework, and uses Apache Kafka for handling real-time data.

## Project Structure

```
.
├── cloud
│   ├── tf_gcp_node
│   ├── local_testsetup
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   ├── requirements.txt
│   │   └── cloud_server.py
│   └── Client
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── backend
        
│       └── frontend
│           ├── static
│           │   ├── css
│           │   │   └── main.css
│           │   └── js
│           │       └── main.js
│           ├── templates
│           │   └── index.html
│           └── requirements.txt
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
- `edge_server.py`: Contains the `EdgeServer` class for reading from and writing to Kafka topics.

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
- ZeroMQ (ZMQ)
- Docker and Docker Compose (for Kafka and Zookeeper)

Cloud Component

### Usage

The cloud server uses the `cloud_server.py` file to interact with the edge component. It consumes data from the Kafka server set up on the edge component and processes it. The cloud server can be run either directly or using Docker Compose with the provided `docker-compose.yml` file in the `cloud/local_testsetup` directory.

To run the cloud server with Docker Compose:

### Dependencies

Dependencies for the cloud server can be installed from the `requirements.txt` file in the `cloud/local_testsetup` directory.

- Docker and Docker Compose