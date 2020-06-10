import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pysmappee",
    version="0.1.0",
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
)
