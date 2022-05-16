#!/usr/bin/env python3

from argparse import ArgumentParser
from datetime import datetime, timedelta
import time

import paho.mqtt.client as mqtt

from libLGTV_serial import LGTV


class TvWrapper:
    def __init__(self, model, serial, fake=False):
        self.tv = None if fake else LGTV(model, serial)
        self.fake = fake
        self.fake_on = False
        self.last_known_input = 'hdmi1' if fake else None
        self.last_known_volume = 0 if fake else None

    def command(self, name, data=None):
        if self.fake:
            raise ValueError('command can not be called if TV is fake')
        print('Command:', name)
        status = self.tv.send(name, data)
        print('Command status:', repr(status))
        return status

    def get_power(self):
        if self.fake:
            return self.fake_on
        return bool(self.command('powerstatus'))

    def set_power(self, set_to_on):
        if self.fake:
            self.fake_on = set_to_on
        else:
            self.command('poweron' if set_to_on else 'poweroff')

    def get_input(self):
        if self.fake:
            return self.last_known_input
        value = self.command('inputstatus')
        if value is None:
            return self.last_known_input
        self.last_known_input = value
        return value

    def set_input(self, input_name):
        if self.fake:
            self.last_known_input = input_name
        else:
            self.command('input' + input_name)

    def get_volume(self):
        if self.fake:
            return self.last_known_volume
        value = self.command('volumelevel')
        if value is None:
            return self.last_known_volume
        self.last_known_volume = value
        return value

    def set_volume(self, volume):
        if self.fake:
            self.last_known_volume = volume
        else:
            self.command('volumelevel', volume)

    def inc_or_dec_volume(self, inc):
        if self.fake:
            if inc and self.last_known_volume < 100:
                self.last_known_volume += 1
            elif self.last_known_volume:
                self.last_known_volume -= 1
        else:
            self.tv.command('volume' + ('up' if inc else 'down'))


class MqttWrapper:
    def __init__(self, tv, topic_prefix, update_interval):
        self.tv = tv

        self.topic_prefix = topic_prefix
        self.get_power_topic = topic_prefix + 'power'
        self.set_power_topic = self.get_power_topic + '/set'
        self.get_input_topic = topic_prefix + 'input'
        self.set_input_topic = self.get_input_topic + '/set'
        self.get_volume_topic = topic_prefix + 'volume'
        self.set_volume_topic = self.get_volume_topic + '/set'
        self.direct_command_topic = topic_prefix + 'command'

        self.update_interval = update_interval
        self.last_update = datetime.min

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.connected = False

    def publish(self, topic, message):
        print(f'Publish: {topic}: {message}')
        self.client.publish(topic, message, qos=2)

    def update_power_to(self, set_to_on):
        if set_to_on:
            # Reset the last update it doesn't undo the fake power on status in
            # below in on_message.
            self.last_update = datetime.now()
        self.publish(self.get_power_topic, 'ON' if set_to_on else 'OFF')

    def update_power(self):
        self.update_power_to(tv.get_power())

    def update_input(self):
        value = self.tv.get_input()
        if value is not None:
            self.publish(self.get_input_topic, value)

    def update_volume(self):
        value = self.tv.get_volume()
        if value is not None:
            self.publish(self.get_volume_topic, str(value))

    def update_all(self):
        now = datetime.now()
        if (now - self.last_update) >= self.update_interval:
            print('Updating...')
            self.update_power()
            self.update_input()
            self.update_volume()
            self.last_update = now

    def on_connect(self, client, userdata, flags, rc):
        print('Connected to broker with result code ' + str(rc))
        client.subscribe(self.topic_prefix + '+/set')
        client.subscribe(self.direct_command_topic)
        self.connected = True

    def on_disconnect(self, client, userdata, rc):
        print('Disconnected from broker')
        self.connected = False

    def on_message(self, client, userdata, msg):
        m = msg.payload.decode()
        print(f'Received: {msg.topic}: {m}')
        if msg.topic == self.set_power_topic:
            set_to_on = {'ON': True, 'OFF': False}[m]
            self.tv.set_power(set_to_on)
            if set_to_on:
                # If off, it will take a while for it to report that it's on
                # and this is a pain to deal with. Just pretend it turned on
                # successfully.
                self.update_power_to(True)
            else:
                self.update_power()
        elif msg.topic == self.set_input_topic:
            self.tv.set_input(m)
            self.update_input()
        elif msg.topic == self.set_volume_topic:
            inc = {'UP': True, 'DOWN': False}.get(m)
            if inc is None:
                self.tv.set_volume(int(m))
            else:
                self.tv.inc_or_dec_volume(inc)
            self.update_volume()
        elif msg.topic == self.direct_command_topic:
            if self.tv.fake:
                print('TV is fake, ignoring direct command')
            else:
                self.tv.command(m)

    def start(self, *args):
        print('Trying to connect...')
        try:
            self.client.connect(*args)
        except OSError:
            print('Failed, going to try again...')

        while True:
            self.client.loop()
            if self.connected:
                self.update_all()
            else:
                print('Trying to reconnect...')
                try:
                    self.client.reconnect()
                except OSError:
                    print('Failed, going to try again...')
                time.sleep(1)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('model', metavar='MODEL')
    parser.add_argument('broker', metavar='MQTT_BROKER')
    parser.add_argument('--serial', '-s', metavar='SERIAL_DEVICE', default=LGTV.default_serial)
    parser.add_argument('--topic-prefix', metavar='MQTT_TOPIC_PREFIX', default='lgtv/')
    parser.add_argument('--interval', metavar='SECONDS', type=int, default=15)
    parser.add_argument('--fake', action='store_true')
    args = parser.parse_args()

    tv = TvWrapper(args.model, args.serial, fake=args.fake)
    client = MqttWrapper(tv, args.topic_prefix, timedelta(seconds=args.interval), )
    client.start(args.broker, 1883, 60)
