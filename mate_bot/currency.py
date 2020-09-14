from mate_bot.config import config


def format_money(amount: int) -> str:
    """
    Convert an amount in cent into a str in euro or any similar currency.

    :param amount: amount in cent
    :type amount: int
    :return: formatted amount
    :rtype: str
    """
    return config["currency"]["format"].format(amount / config["currency"]["conversion"])
