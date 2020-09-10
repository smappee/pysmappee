import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysmappee",
    version="0.2.12",
    author="Smappee",
    author_email="support@smappee.com",
    description="Offical Smappee dev API and MQTT python wrapper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/smappee/pysmappee",
    packages=setuptools.find_packages(),
    license='MIT',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        "cachetools>=4.0.0",
        "certifi>=2019.11.28",
        "chardet>=3.0.4",
        "idna>=2.9",
        "paho-mqtt>=1.5.0",
        "pytz>=2019.3",
        "requests>=2.23.0",
        "tornado>=6.0.3",
        "urllib3>=1.25.8",
    ],
)
