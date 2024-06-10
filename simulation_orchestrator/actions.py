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

import typing

from rest.schemas.simulation_schemas import SimulationPost
from simulation_orchestrator import parse_esdl
from simulation_orchestrator.io.mqtt_client import MqttClient
from simulation_orchestrator.models.simulation_inventory import SimulationInventory, Simulation
from simulation_orchestrator.models.simulation_executor import SimulationExecutor

from simulation_orchestrator.types import SimulationId, ProgressState

simulation_inventory: SimulationInventory
simulation_executor: SimulationExecutor
mqtt_client : MqttClient

def create_new_simulation(simulation_post : SimulationPost) -> Simulation:
    
    # check if esdl is readable
    parse_esdl.get_energy_system(simulation_post.esdl_base64string)

    simulator_id = 'SO'

    new_simulation = Simulation(
        simulator_id=simulator_id,
        simulation_name=simulation_post.name,
        simulation_start_date=simulation_post.start_date,
        simulation_duration_in_seconds=simulation_post.simulation_duration_in_seconds,
        keep_logs_hours=simulation_post.keep_logs_hours,
        log_level=simulation_post.log_level,
        calculation_services=simulation_post.calculation_services,
        esdl_base64string=simulation_post.esdl_base64string
    )

    return new_simulation

def start_new_simulation(simulation_post: SimulationPost) -> SimulationId:

    new_simulation = create_new_simulation(simulation_post)

    model_list = parse_esdl.get_model_list(new_simulation.calculation_services, new_simulation.esdl_base64string)

    simulation_id = simulation_inventory.add_simulation(new_simulation)
    simulation_inventory.add_models_to_simulation(new_simulation.simulation_id, model_list)
    simulation_executor.deploy_simulation(simulation_inventory.get_simulation(simulation_id))

    return simulation_id

def queue_new_simulation(simulation_post: SimulationPost) -> SimulationId:
    new_simulation = create_new_simulation(simulation_post)
    model_list = parse_esdl.get_model_list(new_simulation.calculation_services, new_simulation.esdl_base64string)
    simulation_id = simulation_inventory.queue_simulation(new_simulation)
    simulation_inventory.add_models_to_simulation(new_simulation.simulation_id, model_list)
    if simulation_inventory.nr_of_queued_simulations() == 1:
        mqtt_client.send_deploy_models(new_simulation.simulator_id, new_simulation.simulation_id,
                                   new_simulation.keep_logs_hours, new_simulation.log_level)
    return simulation_id

def get_simulation_and_status(simulation_id: SimulationId) -> typing.Tuple[typing.Union[Simulation, None], str]:
    return (
        simulation_inventory.get_simulation(simulation_id),
        simulation_inventory.get_status_description(simulation_id)
    )

def get_simulation_and_status_list() -> typing.List[typing.Tuple[typing.Union[Simulation, None], str]]:
    simulation_ids = simulation_inventory.get_simulation_ids()
    return [
        get_simulation_and_status(simulation_id)
        for simulation_id in simulation_ids
    ]

def terminate_simulation(simulation_id: SimulationId) -> typing.Tuple[typing.Union[Simulation, None], str]:
    return_val = mqtt_client.terminate_simulation(simulation_id)
    simulation_inventory.remove_simulation(simulation_id)
    return return_val
