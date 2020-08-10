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
