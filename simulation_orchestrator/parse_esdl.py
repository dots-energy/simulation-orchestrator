#  This work is based on original code developed and copyrighted by TNO 2023.
#  Subsequent contributions are licensed to you by the developers of such code and are
#  made available to the Project under one or several contributor license agreements.
#
#  This work is licensed to you under the Apache License, Version 2.0.
#  You may obtain a copy of the license at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Contributors:
#      TNO         - Initial implementation
#  Manager:
#      TNO

import math
from typing import List

from esdl import esdl, EnergySystem
from esdl.esdl_handler import EnergySystemHandler
from base64 import b64decode

from rest.schemas.simulation_schemas import CalculationService
from simulation_orchestrator.dataclasses.dataclasses import CalculationServiceInfo, ConnectedCalculationServcie
from simulation_orchestrator.models.model_inventory import Model
from simulation_orchestrator.types import EsdlId, ProgressState


def get_energy_system(esdl_base64string: str) -> EnergySystem:
    esdl_string = b64decode(esdl_base64string + b"==".decode("utf-8")).decode("utf-8")

    esh = EnergySystemHandler()
    esh.load_from_string(esdl_string)
    return esh.get_energy_system()

def get_model_esdl_object(esdl_id: EsdlId, energy_system: EnergySystem) -> esdl:
    if energy_system.id == esdl_id:
        return energy_system
    # Iterate over all contents of the EnergySystem
    for obj in energy_system.eAllContents():
        if hasattr(obj, "id") and obj.id == esdl_id:
            return obj
    raise IOError(f"ESDL_ID '{esdl_id}' not found in provided ESDL file")

def add_calc_services_from_ports(
    calculation_services: List[CalculationService],
    connected_input_esdl_objects: List[ConnectedCalculationServcie],
    model_esdl_asset: esdl.EnergyAsset,
):
    for port in model_esdl_asset.port:
        if isinstance(port, esdl.InPort):
            for connected_port in port.connectedTo:
                connected_asset = connected_port.eContainer()
                add_connected_esdl_object(
                    connected_input_esdl_objects, calculation_services, connected_asset
                )

def add_calc_services_from_non_connected_objects(
    calculation_services: List[CalculationService],
    connected_input_esdl_objects: List[ConnectedCalculationServcie],
    energy_system: esdl,
):
    for esdl_obj in energy_system.eAllContents():
        if not isinstance(esdl_obj, esdl.EnergyAsset) and hasattr(esdl_obj, "id"):
            add_connected_esdl_object(
                connected_input_esdl_objects, calculation_services, esdl_obj
            )
    add_connected_esdl_object(connected_input_esdl_objects, calculation_services, energy_system)

def add_calc_services_from_all_objects(
    calculation_services: List[CalculationService],
    connected_input_esdl_objects: List[ConnectedCalculationServcie],
    energy_system: esdl.EnergySystem,
):
    for esdl_obj in energy_system.eAllContents():
        if hasattr(esdl_obj, "id"):
            add_connected_esdl_object(
                connected_input_esdl_objects, calculation_services, esdl_obj
            )

def get_connected_input_esdl_objects(
    esdl_id: EsdlId,
    calculation_services: List[CalculationService],
    energy_system: EnergySystem,
) -> List[ConnectedCalculationServcie]:
    model_esdl_obj = get_model_esdl_object(esdl_id, energy_system)

    connected_input_esdl_objects: List[ConnectedCalculationServcie] = []
    if isinstance(model_esdl_obj, esdl.EnergyAsset):
        add_calc_services_from_ports(
            calculation_services, connected_input_esdl_objects, model_esdl_obj
        )
        add_calc_services_from_non_connected_objects(
            calculation_services, connected_input_esdl_objects, energy_system
        )
    else:
        add_calc_services_from_all_objects(
            calculation_services, connected_input_esdl_objects, energy_system
        )
    return connected_input_esdl_objects

def extract_calculation_service(calculation_services: List[CalculationService], esdl_obj) -> CalculationService:
    esdl_obj_type_name = type(esdl_obj).__name__
    calc_service = next(
        (
            calc_service
            for calc_service in calculation_services
            if calc_service.esdl_type == esdl_obj_type_name
        ),
        None,
    )
    
    return calc_service

def add_esdl_object(service_info_dict: dict[str, CalculationServiceInfo], calculation_services: List[CalculationService], esdl_obj: esdl):
    calc_service = extract_calculation_service(calculation_services, esdl_obj)

    if calc_service:
        if calc_service.calc_service_name in service_info_dict:
            service_info_dict[calc_service.calc_service_name].esdl_ids.append(esdl_obj.id)
        else:
            service_info_dict[calc_service.calc_service_name] = CalculationServiceInfo(calc_service.calc_service_name, calc_service.service_image_url, calc_service.nr_of_models, [esdl_obj.id])

def get_model_list(calculation_services: List[CalculationService], esdl_base64string: str) -> List[Model]:
    try:
        energy_system = get_energy_system(esdl_base64string)

        # gather all esdl objects per calculation service
        service_info_dict: dict[str, CalculationServiceInfo] = {}
        # Iterate over all contents of an EnergySystem
        for esdl_obj in energy_system.eAllContents():
            add_esdl_object(service_info_dict, calculation_services, esdl_obj)

        if next((True for calc_service in calculation_services if
                 calc_service.esdl_type == esdl.EnergySystem.__name__), False):
            add_esdl_object(service_info_dict, calculation_services, energy_system)

        # create model(s) per calculation service
        model_list: List[Model] = []
        for service_info in service_info_dict.values():
            add_service_models(service_info, model_list, calculation_services, energy_system)
    except Exception as ex:
        raise IOError(f"Error getting Model list from ESDL: {ex},")

    return model_list


def add_connected_esdl_object(service_info_dict: List[ConnectedCalculationServcie], calculation_services: List[CalculationService], esdl_obj: esdl):
    calc_service = extract_calculation_service(calculation_services, esdl_obj)

    if calc_service:
        connected_calculation_service = next((connected_calc_service for connected_calc_service in service_info_dict if connected_calc_service.esdl_type == calc_service.esdl_type), None)
        if connected_calculation_service:
            connected_calculation_service.connected_services.append(esdl_obj.id)
        else:
            service_info_dict.append(ConnectedCalculationServcie(calc_service.esdl_type, [esdl_obj.id]))

def add_service_models(service_info : CalculationServiceInfo, model_list, calculation_services : List[CalculationService], energy_system : EnergySystem):
    nr_of_esdl_objects = len(service_info.esdl_ids)
    if service_info.nr_of_models == 0:
        nr_of_objects_in_model = 1
    else:
        nr_of_objects_in_model = math.ceil(nr_of_esdl_objects / service_info.nr_of_models)

    i_model = 0
    while i_model * nr_of_objects_in_model < nr_of_esdl_objects:
        i_model += 1
        model_id = f"{service_info.calc_service_name.replace('_', '-')}-{i_model}"

        esdl_ids = []
        for i_esdl_id in range((i_model - 1) * nr_of_objects_in_model, i_model * nr_of_objects_in_model):
            if i_esdl_id < len(service_info.esdl_ids):
                esdl_ids.append(service_info.esdl_ids[i_esdl_id])

        calculation_services_dict : dict[EsdlId, List[ConnectedCalculationServcie]] = {}
        for esdl_id in esdl_ids:
            calculation_services_dict[esdl_id] = get_connected_input_esdl_objects(esdl_id, calculation_services, energy_system)
        model_list.append(
            Model(
                model_id=model_id,
                esdl_ids=esdl_ids,
                connected_services=calculation_services_dict,
                calc_service_name=service_info.calc_service_name,
                service_image_url=service_info.service_image_url,
                current_state=ProgressState.REGISTERED,
            )
        )
