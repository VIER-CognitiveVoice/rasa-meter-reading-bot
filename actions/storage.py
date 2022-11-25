import abc
from dataclasses import dataclass
from typing import List

import requests

from . import create_logger

logger = create_logger("storage")


@dataclass
class Meter:

    meterID: str
    meterReading: str
    maxDiff: str
    lastYear_meterReading: str

    @staticmethod
    def from_dict(dict):
        return Meter(
            meterID=dict.get("meterID"),
            meterReading=dict.get("meterReading"),
            maxDiff=dict.get("maxDiff"),
            lastYear_meterReading=dict.get("lastYear_meterReading"),
        )


@dataclass
class Customer:
    customerNumber: str
    meters: List[Meter]

    # Ignore the first character (the letter)
    def findMeterFuzzy(self, meterID: str) -> Meter:
        if self is not None and meterID is not None:
            for meter in self.meters:
                if meter.meterID[1:] == meterID[1:]:
                    return meter
        return None


class HttpException(Exception):
    def __init__(self, response: requests.Response) -> None:
        super().__init__(
            f"HTTP {response.request.method} request to {response.request.url} failed with status code {response.status_code} and message: {response.text}"  # noqa: E501, F401
        )


class MeterReadingStorage(abc.ABC):
    @abc.abstractmethod
    def getCustomer(self, customerNumber: str) -> Customer:
        pass

    @abc.abstractmethod
    def submitMeterReading(self, meterID: str, newReading: str):
        pass

    @abc.abstractmethod
    def findMeter(self, meterID: str) -> Meter:
        pass


class InMemoryStorageImpl(MeterReadingStorage):
    storage: List[Customer] = []

    def getCustomer(self, customerNumber) -> Customer:
        if (
            customerNumber == None or           # The customerNumber MUST
            not customerNumber.isnumeric() or   # only contain digits
            len(customerNumber) != 6 or         # be 6 digits long
            not customerNumber.startswith("4")  # start with a 4
        ):
            return None

        for customer in self.storage:
            if customer.customerNumber == customerNumber:
              return customer
        meters = [
            Meter("A39" + customerNumber, None, "1000", "2000"), # You should not be able to set a meter reading higher than 3000
            Meter("B42" + customerNumber, "38000", None, None),  # You will be ask, if you want to overwrite the meter reading 
        ]
        customer = Customer(customerNumber, meters)
        self.storage.append(customer)
        return customer

    def submitMeterReading(self, meterID: str, newReading):
        meter = self.findMeter(meterID)
        if meter is None:
          raise KeyError("meter not found: " + str(meterID))
        meter.meterReading = newReading

    def findMeter(self, meterID: str) -> Meter:
        for customer in self.storage:
            for allMeters in customer.meters:
                if allMeters.meterID == meterID.upper():
                  return allMeters
        return None
