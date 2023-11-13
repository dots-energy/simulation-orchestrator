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

import os
import logging

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOGGER = logging.getLogger('SO-logger')
LOGGER.setLevel(LOG_LEVEL)

logging.basicConfig(
    format='%(asctime)s [%(threadName)s][%(filename)s:%(lineno)d][%(name)s-%(levelname)s]: %(message)s',
    level=LOG_LEVEL,
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

logging.info(f"Using Debug Level '{LOG_LEVEL}'")
