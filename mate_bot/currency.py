from mate_bot.config import config


def cent_to_euro(amount: int) -> float:
    """
    Convert an integer in cent to a flot in euro or their equivalents.

    :param amount: amount in cent
    :type amount: int
    :return: amount in euro
    :rtype: float
    """

    return amount / config["currency"]["conversion"]


def format_money(amount: int) -> str:
    """
    Convert an amount in cent into a str in euro or any similar currency.

    :param amount: amount in cent
    :type amount: int
    :return: formatted amount
    :rtype: str
    """

    return config["currency"]["format"].format(cent_to_euro(amount))
