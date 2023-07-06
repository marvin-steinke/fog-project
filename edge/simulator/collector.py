"""
Adopted from https://mosaik.readthedocs.io/en/latest/tutorials/demo1.html.
Alteration by us: added docstrings
"""

import collections
import mosaik_api


META = {
    'type': 'event-based',
    'models': {
        'Monitor': {
            'public': True,
            'any_inputs': True,
            'params': [],
            'attrs': [],
        },
    },
}


class Collector(mosaik_api.Simulator):
    """Mosaik Simulator class for a Monitor that collects data.

    This class allows the creation of a unique Monitor entity and enables
    interaction with incoming data.
    """

    def __init__(self):
        super().__init__(META)
        self.eid = None
        self.data = collections.defaultdict(lambda: collections.defaultdict(dict))

    def init(self, sid, time_resolution):
        """Mosaik: Initialize the Collector instance with the given simulation id and
        time resolution.

        Args:
            sid (int): Simulation ID.
            time_resolution (int): Time resolution for simulation.

        Returns:
            dict: The initialized instance's metadata.
        """
        return self.meta

    def create(self, num, model):
        """Mosaik: Create a unique entity for the Monitor instance.

        Args:
            num (int): The number of entities to create. Should only be 1 for
                this model.
            model (str): The model name.

        Raises:
            RuntimeError: If trying to create more than one instance or the
                entity id already exists.

        Returns:
            list: The entity id and type in a dictionary.
        """
        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of Monitor.')

        self.eid = 'Monitor'
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs, max_advance):
        """Mosaik: Step the simulation for all the entities in this monitor.

        Args:
            time (int): Current time of the simulation.
            inputs (dict): Input data for this step.
            max_advance (int): Maximum time that the simulator can advance in
                one step.

        Returns:
            None
        """
        data = inputs.get(self.eid, {})
        for attr, values in data.items():
            for src, value in values.items():
                self.data[src][attr][time] = value

        return None

    def finalize(self):
        """Mosaik: Prints the collected data upon simulation finalization."""
        print('Collected data:')
        for sim, sim_data in sorted(self.data.items()):
            print('- %s:' % sim)
            for attr, values in sorted(sim_data.items()):
                print('  - %s: %s' % (attr, values))


if __name__ == '__main__':
    mosaik_api.start_simulation(Collector())

