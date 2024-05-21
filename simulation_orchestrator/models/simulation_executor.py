
from simulation_orchestrator.model_services_orchestrator.k8s_api import K8sApi
from simulation_orchestrator.models.simulation_inventory import Simulation

class SimulationExecutor:

    def __init__(self, k8s_api : K8sApi) -> None:
        self.k8s_api = k8s_api

    def deploy_simulation(self, simulation : Simulation):
        amount_of_helics_federates = sum([calculation_service.nr_of_models for calculation_service in simulation.calculation_services])
        models = simulation.model_inventory.get_models()
        self.k8s_api.deploy_helics_broker(amount_of_helics_federates, simulation.simulation_id, simulation.simulator_id)
        for model in models:
            self.k8s_api.deploy_model(simulation.simulator_id, simulation.simulation_id, model, 2.0)
