import mosaik
import mosaik.util
from loguru import logger
from edge_server import EdgeServer
import time
import configparser
import os


config = configparser.ConfigParser()
config.read('config.ini')
sim_args = {
    "start": config.get("Sim", "start"),
    "end": config.getint("Sim", "end"),
    "household_data_dir": config.get("Sim", "household_data_dir"),
    "kafka_address": config.get("Server", "kafka_address")
}

sim_config = {
    "Household": {
        "python": "simulator.household:Household",
    },
    "KafkaAdapter": {
        "python": "simulator.kafka_adapter:KafkaAdapter",
    },
    "Collector": {
        "python": "simulator.collector:Collector",
    }
}


def main() -> None:
    """Main function to run the simulation with EdgeServer and Mosaik.

    This function initializes the EdgeServer, creates the Mosaik world, runs
    the simulation and finally stops the EdgeServer.
    """
    edge_server = EdgeServer(
            bootstrap_servers=sim_args["kafka_address"],
            input_topic="power_topic",
            output_topic="avg_power_topic"
    )
    edge_server.run()
    while not edge_server.ready:
        time.sleep(.1)

    # suppress mosaik warnings
    logger.remove()
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=sim_args["end"], rt_factor=1)

    edge_server.stop()


def create_scenario(world: mosaik.World) -> None:
    """Creates the simulation scenario in the given mosaik world.

    Args:
        world (mosaik.World): The mosaik world in which the scenario is to be created.
    """
    # Read household csvs
    household_data_dir = sim_args["household_data_dir"]
    if household_data_dir[-1] != "/":
        household_data_dir += "/"
    csv_files = [file for file in os.listdir(household_data_dir) if file.endswith('.csv')]

    # Start simulators
    households = []
    for csv_file in csv_files:
        csv_path = household_data_dir + csv_file
        household_name = csv_file[:-4]
        households.append(world.start(
            "Household",
            datafile=csv_path,
            household_name=household_name
        ).household())

    # Create one kafka adapter for each household
    kafka_adapters = world.start("KafkaAdapter").KafkaAdapterModel.create(
                                                    num=len(csv_files),
                                                    kafka_address=sim_args["kafka_address"]
                                                )
    # and connect them respectively.
    mosaik.util.connect_randomly(world, households, kafka_adapters, "power")

    # Print all collected data at the end for debugging
    monitor = world.start("Collector").Monitor()
    mosaik.util.connect_many_to_one(world, households, monitor, "power")


if __name__ == '__main__':
    """Entry point of the script, calls the main function."""
    main()

