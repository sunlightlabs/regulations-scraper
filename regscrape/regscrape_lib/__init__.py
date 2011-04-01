# lifted some logging code from the examples in the Python docs

import logging

# create logger
logger = logging.getLogger("regscrape")
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# also log pykka stuff if DEBUG is true
import settings

if settings.DEBUG:
    for ext_logger_name in ['pykka', 'remote_connection']:
        ext_logger = logging.getLogger(ext_logger_name)
        ext_logger.setLevel(logging.DEBUG)
        ext_logger.addHandler(ch)
