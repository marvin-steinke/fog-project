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
    def __init__(self, kafka_address: str) -> None:
        self.lock = threading.Lock()
        self.p = None

        def initialize_producer():
            self.p = Producer({'bootstrap.servers': kafka_address})

        thread = threading.Thread(target=initialize_producer)
        thread.start()

    def step(self, household, power) -> None:
        def produce_message():
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
    def __init__(self) -> None:
        super().__init__(META)
        self.eid_prefix = "KafkaAdapter_"
        self.entities = {}

    def init(self, sid: int, time_resolution: int):
        """Initialize Simulator."""
        if float(time_resolution) != 1.0:
            raise ValueError(
                f"{self.__class__.__name__} only supports time_resolution=1., "
                f"but {time_resolution} was set."
            )
        return self.meta

    def create(self, num: int, model: str, kafka_address: str = "localhost:9092"):
        """Create `model_instance` and save it in `entities`."""
        next_eid = len(self.entities)
        entities = []
        for i in range(next_eid, next_eid + num):
            model_instance = KafkaAdapterModel(kafka_address)
            eid = self.eid_prefix + str(i)
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time: int, inputs: dict, max_advance: int):
        """Set all `inputs` attr values to the `entity` attrs, then step the `entity`."""
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
        """Return all requested data as attr from the `model_instance`."""
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
