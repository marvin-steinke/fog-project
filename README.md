# fog-project

This project simulates a distributed power system where power data from
different households is streamed in real-time. The data is processed and
averaged over a 30-second window. The simulation is coordinated by Mosaik, a
co-simulation framework, and uses Apache Kafka for handling real-time data.

## Project Structure

```
.
├── cloud
│   └── tf_gcp_node
├── documents
└── edge
    ├── config.ini
    ├── data
    ├── docker-compose.yml
    ├── edge_server.py
    ├── main.py
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

## Usage

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

- Python 3.8 or later
- Mosaik
- Apache Kafka
- Docker and Docker Compose (for Kafka and Zookeeper)

