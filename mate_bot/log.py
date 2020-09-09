import logging as _logging
import logging.handlers


class NotFilter(_logging.Filter):

    def filter(self, record: _logging.LogRecord) -> int:
        return not super().filter(record)


def setup():
    formatter = logging.Formatter(fmt='matebot %(process)d: %(levelname)s: %(name)s: %(message)s')

    handler = _logging.FileHandler("/var/log/matebot.log")
    handler.addFilter(NotFilter("telegram"))
    handler.setFormatter(formatter)

    logger = _logging.getLogger()
    logger.setLevel(_logging.DEBUG)
    logger.addHandler(handler)
