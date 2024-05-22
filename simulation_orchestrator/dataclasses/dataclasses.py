from dataclasses import dataclass
from typing import List

from simulation_orchestrator.types import EsdlId


@dataclass
class ConnectedCalculationServcie:
    service_name : str
    connected_services : List[EsdlId]

@dataclass
class CalculationServiceInfo:
    calc_service_name : str
    service_image_url : str
    nr_of_models : int
    esdl_ids : List[EsdlId]