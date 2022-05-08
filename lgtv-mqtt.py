#!/usr/bin/env python3

from argparse import ArgumentParser
import time

import paho.mqtt.client as mqtt

from libLGTV_serial import LGTV


class TvWrapper:
    def __init__(self, model, serial):
        self.tv = LGTV(model, serial)

    def command(self, name, data=None):
        print('Command:', name)
        status = self.tv.send(name, data)
        print('Command status:', repr(status))
        return status

    def get_power(self):
        return self.command('powerstatus') == b'01'

    def set_power(self, set_to_on):
        self.command('poweron' if set_to_on else 'poweroff')

    def get_input(self):
        return self.command('inputstatus')

    def set_input(self, input_name):
        self.command('input' + input_name)

    def get_volume(self):
        return self.command('volumelevel')

    def set_volume(self, volume):
        self.command('volumelevel', volume)


parser = ArgumentParser()
parser.add_argument('model', metavar='MODEL')
parser.add_argument('broker', metavar='MQTT_BROKER')
parser.add_argument('--serial', '-s', metavar='SERIAL_DEVICE', default=LGTV.default_serial)
parser.add_argument('--topic-prefix', metavar='MQTT_TOPIC_PREFIX', default='lgtv/')
args = parser.parse_args()

tv = TvWrapper(args.model, args.serial)
get_power_topic = args.topic_prefix + 'power'
set_power_topic = get_power_topic + '/set'
get_input_topic = args.topic_prefix + 'input'
set_input_topic = get_input_topic + '/set'
get_volume_topic = args.topic_prefix + 'volume'
set_volume_topic = get_volume_topic + '/set'
direct_command_topic = args.topic_prefix + 'command'


def publish(client, topic, message):
    print(f'Publish: {topic}: {message}')
    client.publish(topic, message, qos=2)


def update_power_to(client, set_to_on):
    publish(client, get_power_topic, 'ON' if set_to_on else 'OFF')


def update_power(client, tv):
    update_power_to(client, tv.get_power())


def update_input(client, tv):
    publish(client, get_input_topic, tv.get_input())


def update_volume(client, tv):
    publish(client, get_volume_topic, str(tv.get_volume()))


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(args.topic_prefix + "+/set")
    client.subscribe(direct_command_topic)
    update_power(client, tv)
    update_input(client, tv)
    update_volume(client, tv)


def on_message(client, userdata, msg):
    m = msg.payload.decode()
    print(f'Received: {msg.topic}: {m}')
    if msg.topic == set_power_topic:
        set_to_on = {'ON': True, 'OFF': False}[m]
        tv.set_power(set_to_on)
        if set_to_on:
            # If off, it will take a while for it to report that it's on and
            # this is a pain to deal with. Just pretend it turned on
            # successfully.
            update_power_to(client, True)
        else:
            update_power(client, tv)
    elif msg.topic == set_input_topic:
        tv.set_input(m)
        update_input(client, tv)
    elif msg.topic == set_volume_topic:
        if m in ('UP', 'DOWN'):
            tv.command('volume' + m.lower())
        else:
            tv.set_volume(int(m))
        update_volume(client, tv)
    elif msg.topic == direct_command_topic:
        tv.command(m)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(args.broker, 1883, 60)
client.loop_forever()
