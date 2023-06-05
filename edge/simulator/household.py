import csv
from typing import Optional
import mosaik_csv

class Household(mosaik_csv.CSV):
    """Represents a household as a subclass of mosaik_csv.CSV.

    This class allows the creation of a unique household entity and enables
    interaction with data stored in a CSV file. The format of the CSV file can
    be derived from `data/reduced_csvs` which is based on the original data
    from "Gem House Opendata: German Electricity Consumption in Many Households
    Over Three Years 2018-2020 (Fresh Energy)" (https://ieee-dataport.org/node/4576/).
    """

    def __init__(self):
        super().__init__()
        self.eid = None

    def init(self,
             sid: int,
             time_resolution: int,
             datafile: str,
             household_name: str,
             sim_start: Optional[str] = None,
             date_format = "YYYY-MM-DD HH:mm:ss",
             delimiter=","):
        """Mosaik: Initialize the Household instance with specified data.

        Args:
            sid (int): Simulation ID.
            time_resolution (int): Time resolution for simulation.
            datafile (str): Path to the data file (CSV).
            household_name (str): Name of the household.
            sim_start (Optional[str], optional): Simulation start date. Defaults to None.
            date_format (str, optional): Date format in the CSV. Defaults to "YYYY-MM-DD HH:mm:ss".
            delimiter (str, optional): Delimiter for CSV. Defaults to ",".

        Returns:
            dict: The initialized instance.
        """
        self.household_name = household_name
        if not sim_start:
            sim_start = self._first_date(datafile)
        return super().init(sid, time_resolution, sim_start, datafile, date_format, delimiter)

    def create(self, num, model):
        """Mosaik: Create a unique entity for the Household instance.

        Args:
            num (int): The number of entities to create. Should only be 1 for this model.
            model (str): The model name.

        Raises:
            ValueError: If the model name is incorrect.
            RuntimeError: If trying to create more than one instance or the entity id already exists.

        Returns:
            list: The entity id and type in a dictionary.
        """
        if model != self.modelname:
            raise ValueError(f"Invalid model '{model}'")

        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of a unique household.')

        self.eid = f"{self.modelname}_{self.household_name}"
        return [{'eid': self.eid, 'type': model}]

    def get_data(self, outputs):
        """Mosaik: Get output data for the given entity and attributes.

        Args:
            outputs (dict): A dictionary of entity ids and their requested attributes.

        Returns:
            dict: The data for the requested entities and attributes.
        """
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                data[eid][attr] = self.cache[attr]

        return data

    def _first_date(self, csv_file: str) -> Optional[str]:
        """Get the first date from a given CSV file.

        Args:
            csv_file (str): Path to the CSV file.

        Returns:
            Optional[str]: The first date string in the CSV file, or None if no date found.
        """
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            # Skip the header
            next(reader)
            next(reader)
            for row in reader:
                # Extract the date string
                date_str = row[0]
                return date_str
        return

