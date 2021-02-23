INTERVALS = (
    ('years', 3154e+7),
    ('months', 2628e+6),
    ('weeks', 604800),
    ('days', 86400),
    ('hours', 3600),
    ('minutes', 60),
    ('seconds', 1)
)


def display_time(seconds: int, granularity: int = 2) -> dict:
    result = {}
    i = 0

    for name, count in INTERVALS:
        if i >= granularity:
            break

        value = seconds // count

        if value:
            seconds -= value * count

            result[name] = value
            i += 1

    return result


def string(seconds: int, localizator, granularity: int = 2) -> str:
    data = display_time(seconds, granularity)
    result = []

    for k, v in data.items():
        result.append(localizator.get_message(k, count=v))

    return ', '.join(result)
