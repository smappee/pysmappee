config = dict()

# api base urls
config['API_URL'] = {
    1: {
        'authorize_url': 'https://app1pub.smappee.net/dev/v1/oauth2/authorize',
        'token_url': 'https://app1pub.smappee.net/dev/v3/oauth2/token',
        'servicelocation_url': 'https://app1pub.smappee.net/dev/v3/servicelocation',
    },
    2: {
        'token_url': 'https://farm2pub.smappee.net/dev/v3/oauth2/token',
        'servicelocation_url': 'https://farm2pub.smappee.net/dev/v3/servicelocation',
    },
    3: {
        'token_url': 'https://farm3pub.smappee.net/dev/v3/oauth2/token',
        'servicelocation_url': 'https://farm3pub.smappee.net/dev/v3/servicelocation',
    },
}

config['MQTT'] = {
    1: {
        'host': 'mqtt.smappee.net',
        'port': 443,
    },
    2: {
        'host': 'mqtttest.smappee.net',
        'port': 443,
    },
    3: {
        'host': 'mqttdev.smappee.net',
        'port': 443,
    },
    'local': {  # only accessible from same network
        'port': 1883,
    },
    'discovery': False,
}
