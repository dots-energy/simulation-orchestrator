
import json
from simulation_orchestrator.model_services_orchestrator.k8s_api import K8sApi, HELICS_BROKER_PORT
from rest.schemas.simulation_schemas import CalculationService, Simulation
from simulation_orchestrator.io.log import LOGGER

import helics as h

class CalculationServiceJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, CalculationService):
                return [
                     {"calc_service_name" : o.calc_service_name},
                     {"esdl_type" : o.esdl_type}
                ]
            return super().default(o)

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
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFederateFlag.UNINTERRUPTIBLE, False)
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFederateFlag.WAIT_FOR_CURRENT_TIME_UPDATE, False)
        h.helicsFederateInfoSetFlagOption(federate_info, h.HelicsFlag.TERMINATE_ON_ERROR, False)
        h.helicsFederateInfoSetCoreType(federate_info, h.HelicsCoreType.ZMQ)
        h.helicsFederateInfoSetIntegerProperty(federate_info, h.HelicsProperty.INT_LOG_LEVEL, h.HelicsLogLevel.DEBUG)
        LOGGER.info("Creating federate to send esdl file: ")
        message_federate = h.helicsCreateMessageFederate("esdl_broker", federate_info)
        message_enpoint = h.helicsFederateRegisterEndpoint(message_federate, "simulation-orchestrator")        
        h.helicsFederateEnterExecutingMode(message_federate)
        esdl_message = h.helicsEndpointCreateMessage(message_enpoint)
        h.helicsMessageSetString(esdl_message, simulation.esdl_base64string)
        calculation_services_message = h.helicsEndpointCreateMessage(message_enpoint)
        h.helicsMessageSetString(calculation_services_message, json.dumps(simulation.calculation_services, cls=CalculationServiceJSONEncoder))

        request_time = int(h.helicsFederateGetTimeProperty(message_federate, h.HelicsProperty.TIME_PERIOD))
        h.helicsFederateRequestTime(message_federate, request_time)
        for model in models:
            endpoint = f'{model.model_id}/esdl'
            h.helicsMessageSetDestination(esdl_message, endpoint)
            LOGGER.info(f"Sending esdl file to: {endpoint}")
            h.helicsEndpointSendMessage(message_enpoint, esdl_message)

        h.helicsFederateRequestTime(message_federate, h.HELICS_TIME_MAXTIME)
        h.helicsFederateDisconnect(message_federate)
        h.helicsFederateDestroy(message_federate)


