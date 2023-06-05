import mosaik_api
import threading
import json
from confluent_kafka import Producer

META = {
    "type": "event-based",
    "models": {
        "KafkaAdapterModel": {
            "public": True,
            "params": ["kafka_address"],
            "attrs": ["power"],
        },
    },
}

class KafkaAdapterModel():
    """Defines a model for Kafka adapter which initializes a Kafka producer and
    produces messages.

    Args:
        kafka_address (str): Address of the Kafka server. Defaults to "localhost:9092".
    """

    def __init__(self, kafka_address: str = "localhost:9092") -> None:
        self.lock = threading.Lock()
        self.p = None

        def initialize_producer():
            self.p = Producer({'bootstrap.servers': kafka_address})

        thread = threading.Thread(target=initialize_producer)
        thread.start()

    def step(self, household, power) -> None:
        """Produce a message to a Kafka topic.

        Args:
            household (str): Name of the household.
            power (float): Power data of the household.
        """
        def produce_message():
            """Produce a message to a Kafka topic."""
            # Extract the id from the household
            household_id = household.split(".")[1]
            data = {"node_id": household_id, "power_value": float(power)}

            self.lock.acquire()
            self.p.produce("power_topic", json.dumps(data))
            self.p.flush()
            self.lock.release()

        thread = threading.Thread(target=produce_message)
        thread.start()


class KafkaAdapter(mosaik_api.Simulator):
    """Mosaik Simulator class for Kafka Adapter which manages the creation and
    stepping of KafkaAdapterModel instances.

    It also manages getting data from the models and stepping the simulation.
    """
    def __init__(self) -> None:
        super().__init__(META)
        self.eid_prefix = "KafkaAdapter_"
        self.entities = {}

    def init(self, sid: int, time_resolution: int):
        """Mosaik: Initialize the Kafka Adapter with the given time resolution.

        Args:
            sid (int): Simulation ID.
            time_resolution (int): Time resolution of the simulation.

        Returns:
            dict: Metadata about the Kafka Adapter.
        """
        if float(time_resolution) != 1.0:
            raise ValueError(
                f"{self.__class__.__name__} only supports time_resolution=1., "
                f"but {time_resolution} was set."
            )
        return self.meta

    def create(self, num: int, model: str, kafka_address: str = "localhost:9092"):
        """Mosaik: Create entities of the given model.

        Args:
            num (int): Number of entities to be created.
            model (str): The model name.
            kafka_address (str, optional): Address of the Kafka server. Defaults to "localhost:9092".

        Returns:
            list: A list of dictionaries representing the created entities.
        """
        next_eid = len(self.entities)
        entities = []
        for i in range(next_eid, next_eid + num):
            model_instance = KafkaAdapterModel(kafka_address)
            eid = self.eid_prefix + str(i)
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time: int, inputs: dict, max_advance: int):
        """Mosaik: Step the simulation for all the entities in this adapter.

        Args:
            time (int): Current time of the simulation.
            inputs (dict): Input data for this step.
            max_advance (int): Maximum time that the simulator can advance in one step.

        Returns:
            None
        """
        self.time = time
        for eid, attrs in inputs.items():
            entity = self.entities[eid]
            for val_dict in attrs.values():
                for household, power in val_dict.items():
                    entity.step(household, power)
                    # There should be only one household per adapter
                    break
                # and also only the attr "power".
                break
        return None

    def get_data(self, outputs: dict):
        """Mosaik: Get output data for the given entity and attributes.

        Args:
            outputs (dict): A dictionary of entity ids and their requested attributes.

        Returns:
            dict: The data for the requested entities and attributes.
        """
        data = {}
        for eid, attrs in outputs.items():
            model = self.entities[eid]
            data["time"] = self.time
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta["models"]["KafkaAdapterModel"]["attrs"]:
                    raise ValueError(f"Unknown output attribute: {attr}")
                data[eid][attr] = getattr(model, attr)
        return data

