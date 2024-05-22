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

from threading import Lock
import typing

from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Sequence

from simulation_orchestrator.models.model_inventory import ModelInventory
from simulation_orchestrator.types import SimulationId, SimulatorId

class CalculationService(BaseModel):
    esdl_type: str = Field(default='PVInstallation', description="The exactname of the ESDL type")
    calc_service_name: str = Field(default='pvinstallation_service',
                                   description="Name of the calculation service,"
                                               " as described in the code generator yaml config file")
    service_image_url: str = Field(default='<pvinstallation_service_docker_image_url>',
                                   description="The URL of the docker image file")
    nr_of_models: int = Field(default=1, description="'0' will create a model (container) per ESDL object")


class SimulationPost(BaseModel):
    name: str = 'simulation name'
    start_date: datetime = '2023-01-25 00:00:00'
    time_step_seconds: int = '3600'
    nr_of_time_steps: int = '24'
    max_step_calc_time_minutes: float = Field(default=10,
                                              description="If a time step takes longer than this amount of minutes,"
                                                          " the simulation will be aborted")
    keep_logs_hours: float = '24.0'
    log_level: str = Field(default='info', description="Options: 'debug', 'info', 'warning', 'error'")
    calculation_services: list[CalculationService]
    esdl_base64string: str = '<esdl_file_base64encoded_string>'

class Simulation:
    simulator_id: SimulatorId
    simulation_id: SimulationId
    simulation_name: str

    simulation_start_datetime: datetime
    time_step_seconds: int
    nr_of_time_steps: int

    max_step_calc_time_minutes: float
    keep_logs_hours: float
    log_level: str

    calculation_services: typing.List[CalculationService]
    esdl_base64string: str

    current_time_step_nr: int
    calculation_start_datetime: datetime
    calculation_end_datetime: typing.Optional[datetime]
    current_step_calculation_start_datetime: typing.Optional[datetime]
    modelparameters_start_datetime: typing.Optional[datetime]
    model_inventory: ModelInventory
    error_message: str

    terminated: bool

    lock: Lock

    def __init__(
            self,
            simulator_id: SimulatorId,
            simulation_name: str,
            simulation_start_date: datetime,
            time_step_seconds: int,
            sim_nr_of_steps: int,
            max_step_calc_time_minutes: float,
            keep_logs_hours: float,
            log_level: str,
            calculation_services: typing.List[CalculationService],
            esdl_base64string: str,
    ):
        self.simulator_id = simulator_id
        self.simulation_name = simulation_name
        self.simulation_start_datetime = simulation_start_date
        self.time_step_seconds = time_step_seconds
        self.nr_of_time_steps = sim_nr_of_steps

        self.max_step_calc_time_minutes = max_step_calc_time_minutes
        self.keep_logs_hours = keep_logs_hours
        self.log_level = log_level

        self.calculation_services = calculation_services
        self.esdl_base64string = esdl_base64string

        self.current_time_step_nr = 0
        self.calculation_start_datetime = datetime.now()
        self.calculation_end_datetime = None
        self.current_step_calculation_start_datetime = None
        self.modelparameters_start_datetime = None
        self.model_inventory = ModelInventory()
        self.error_message = ""
        self.terminated = False

        self.lock = Lock()


class SimulationStatus(SimulationPost):
    simulation_id: str = 'sim-0'
    simulation_status: str = 'Running time step 2 of 24'
    calculation_start_datetime: datetime = datetime.now()
    calculation_end_datetime: typing.Optional[datetime] = None
    calculation_duration: timedelta = timedelta(seconds=3000)

    @classmethod
    def from_simulation_and_status(cls, simulation: Simulation, status: str):
        if simulation.calculation_end_datetime:
            calculation_duration = simulation.calculation_end_datetime - simulation.calculation_start_datetime
        else:
            calculation_duration = datetime.now() - simulation.calculation_start_datetime

        return cls(
            name=simulation.simulation_name,
            start_date=simulation.simulation_start_datetime,
            time_step_seconds=simulation.time_step_seconds,
            nr_of_time_steps=simulation.nr_of_time_steps,
            calculation_services=simulation.calculation_services,
            esdl_base64string=simulation.esdl_base64string,
            log_level=simulation.log_level,
            simulation_id=simulation.simulation_id,
            simulation_status=status,
            calculation_start_datetime=simulation.calculation_start_datetime,
            calculation_end_datetime=simulation.calculation_end_datetime,
            calculation_duration=calculation_duration
        )


class SimulationList(BaseModel):
    simulations: Sequence[SimulationStatus]
