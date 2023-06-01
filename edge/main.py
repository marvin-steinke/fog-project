import mosaik
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
sim_args = {
    "start": config.get("Sim", "start"),
    "end": config.getint("Sim", "end"),
    "solar_data": config.get("Sim", "solar_data"),
    "wind_data": config.get("Sim", "wind_data")
}

sim_config = {
    "CSV": {
        "python": "mosaik_csv:CSV",
    }
}


def main() -> None:
    world = mosaik.World(sim_config)
    create_scenario(world)
    world.run(until=sim_args["end"])  # As fast as possilbe
    # world.run(until=sim_args["end"], rt_factor=1/60)  # Real-time 1min -> 1sec


def create_scenario(world: mosaik.World) -> None:
    # Start simulators
    solar_sim = world.start(
        "CSV",
        sim_start=sim_args["start"],
        datafile=sim_args["solar_data"]
    )
    wind_sim = world.start(
        "CSV",
        sim_start=sim_args["start"],
        datafile=sim_args["wind_data"]
    )

    # Instantiate models
    solar_panel = solar_sim.PV.create(1)
    wind_turbine = solar_sim.Wind.create(1)


if __name__ == '__main__':
    main()
