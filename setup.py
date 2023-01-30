from setuptools import setup, find_packages

setup(
    name = 'libLGTV_serial',
    packages=find_packages(),
    scripts=['lgtv-mqtt.py'],
    install_requires=[
        'pyserial',
        'paho-mqtt',
    ],
)
