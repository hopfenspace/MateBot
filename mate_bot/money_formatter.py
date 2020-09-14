from mate_bot.config import config


def format_money(amount: int) -> str:
    """
    Convert an amount in cent into a str in euro or any similar currency.

    :param amount: amount in cent
    :type amount: int
    :return: formatted amount
    :rtype: str
    """
    return config["general"]["currency_format"].format(amount / config["general"]["currency_conversion"])
