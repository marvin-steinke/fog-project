import csv
from typing import Optional

import mosaik_csv

class Household(mosaik_csv.CSV):
    def __init__(self):
        super().__init__()
        self.eid = None

    def init(self, sid: int, time_resolution: int, datafile: str, household_name: str, sim_start: Optional[str] = None, date_format = "YYYY-MM-DD HH:mm:ss", delimiter=","):
        self.household_name = household_name
        if not sim_start:
            sim_start = self._first_date(datafile)
        return super().init(sid, time_resolution, sim_start, datafile, date_format, delimiter)

    def create(self, num, model):
        if model != self.modelname:
            raise ValueError(f"Invalid model '{model}'")

        if num > 1 or self.eid is not None:
            raise RuntimeError('Can only create one instance of a unique household.')

        self.eid = f"{self.modelname}_{self.household_name}"
        return [{'eid': self.eid, 'type': model}]

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                data[eid][attr] = self.cache[attr]

        return data

    def _first_date(self, csv_file: str) -> Optional[str]:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            # Skip the header
            next(reader)
            next(reader)
            for row in reader:
                # Extract the date string
                date_str = row[0]
                return date_str
        return None
