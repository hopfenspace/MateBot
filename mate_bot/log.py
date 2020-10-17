import logging as _logging
import logging.handlers


class NoTelegramDebugFilter(_logging.Filter):

    def filter(self, record: _logging.LogRecord) -> int:
        if super().filter(record):
            return record.levelno > _logging.DEBUG
        return True


def setup():
    formatter = logging.Formatter(fmt='matebot %(process)d: %(levelname)s: %(name)s: %(message)s')

    handler = _logging.FileHandler("/var/log/matebot.log")
    handler.addFilter(NoTelegramDebugFilter("telegram"))
    handler.setFormatter(formatter)

    logger = _logging.getLogger()
    logger.setLevel(_logging.DEBUG)
    logger.addHandler(handler)
