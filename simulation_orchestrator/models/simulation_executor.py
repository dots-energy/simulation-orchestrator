
from simulation_orchestrator.model_services_orchestrator.k8s_api import K8sApi, HELICS_BROKER_PORT
from rest.schemas.simulation_schemas import Simulation
from simulation_orchestrator.io.log import LOGGER

import helics as h

class SimulationExecutor:

    def __init__(self, k8s_api : K8sApi) -> None:
        self.k8s_api = k8s_api

    def deploy_simulation(self, simulation : Simulation):
        amount_of_helics_federates = sum([calculation_service.nr_of_models for calculation_service in simulation.calculation_services])
        models = simulation.model_inventory.get_models()
        broker_ip = self.k8s_api.deploy_helics_broker(amount_of_helics_federates, simulation.simulation_id, simulation.simulator_id)
        for model in models:
            self.k8s_api.deploy_model(simulation.simulator_id, simulation.simulation_id, model, simulation.keep_logs_hours, broker_ip)
            self.k8s_api.await_pod_to_running_state(self.k8s_api.model_to_pod_name(simulation.simulator_id, simulation.simulation_id, model.model_id))

        federate_info = h.helicsCreateFederateInfo()
        h.helicsFederateInfoSetBroker(federate_info, broker_ip)
        h.helicsFederateInfoSetBrokerPort(federate_info, HELICS_BROKER_PORT)
        h.helicsFederateInfoSetTimeProperty(federate_info, h.HelicsProperty.TIME_PERIOD, 60)
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFederateFlag.UNINTERRUPTIBLE, True)
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFederateFlag.WAIT_FOR_CURRENT_TIME_UPDATE, True)
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFlag.TERMINATE_ON_ERROR, False)
        h.helicsFederateInfoSetCoreType(federate_info, h.HelicsCoreType.ZMQ)
        h.helicsFederateInfoSetIntegerProperty(federate_info, h.HelicsProperty.INT_LOG_LEVEL, h.HelicsLogLevel.DEBUG)
        LOGGER.info("Creating federate to send esdl file: ")
        message_federate = h.helicsCreateMessageFederate("esdl_broker", federate_info)
        message_enpoint = h.helicsFederateRegisterEndpoint(message_federate, "simulation-orchestrator")
        message = message_enpoint.create_message()
        message.data = simulation.esdl_base64string
        message_federate.enter_executing_mode(message_federate)
        h.helicsFederateRequestTime(message_federate, 1)
        for model in models:
            endpoint = f'{model.model_id}/esdl'
            LOGGER.info(f"Sending esdl file to: {endpoint}")
            message_enpoint.send_data(message, endpoint)
        
        h.helicsFederateRequestTime(message_federate, h.HELICS_TIME_MAXTIME)
        h.helicsFederateDisconnect(message_federate)
        h.helicsFederateDestroy(message_federate)


