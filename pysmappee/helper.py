"""Helper methods."""


def urljoin(*parts):
    """Join all url parts."""
    # first strip extra forward slashes (except http:// and the likes) and create list
    part_list = []
    for part in parts:
        str_part = str(part)
        if str_part.endswith('//'):
            str_part = str_part[0:-1]
        else:
            str_part = str_part.strip('/')
        part_list.append(str_part)
    # join everything together
    url = '/'.join(part_list)
    return url


def is_smappee_energy(serialnumber: str):
    return serialnumber.startswith('10')


def is_smappee_solar(serialnumber: str):
    return serialnumber.startswith('11')


def is_smappee_plus(serialnumber: str):
    return serialnumber.startswith('2')


def is_smappee_genius(serialnumber: str):
    return serialnumber.startswith('50')


def is_smappee_connect(serialnumber: str):
    return serialnumber.startswith('51')
