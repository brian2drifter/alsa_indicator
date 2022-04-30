#!/usr/bin/env python3

""" Provide a visual indication of ALSA sample_rate and bit _depth to an external USB or serial device.

Most Raspberry Pi streamer and DAC implementations do not give an indication of the quality (bit-depth and
sample_rate) of the music being played. This code interrogates ALSA to determine the currently active soundcard and the
sample_rate and bit_depth of any music being played. It then sends a coded version of this via a serial link to any
external indicator device.

The code was designed to work with and has been tested on an Adafruit Neo Trinkey but should work with any suitable
device that has back-end code to decode the serial information and display it appropriately.


This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Brian Jones"
__contact__ = "brian@ivarc.org.uk"
__copyright__ = "Copyright 2022 Brian Jones"
__date__ = "2022/01/15"
__deprecated__ = False
__license__ = "GPLv3"
__maintainer__ = "developer"
__status__ = "Production"
__version__ = "0.0.1"

import os
import glob
import re
import serial
import time
import logging
import configparser


class NoActiveSoundcard(Exception):
    """
    Raised when no soundcard is found
    """
    pass


class NoSerialDevice(Exception):
    """
    Raised when Serial setup or write fails
    """
    pass


def read_config_info(config_file):
    """
    Read the config variables into a dictionary

    Variables are
    LOGGING
        LOG_LEVEL (as per keys to log_level _info below and corresponding to Python standard library Logging
        IGNORE_SERIAL_ERROR - Boolean - set to True if testing alsa code without serial device attached
    SERIAL
        PORT - serial port for attached sample-rate indicator device
        BAUDRATE - baud rate for the above
        SAMPLE_SECONDS - rate at which to re-check alsa for sample_rate and bit_depth of any playing audio

    :param: config_file: standard configparser config file
    :return: _config_info: dictionary containing the parsed config variables
    """
    _config_info = {}
    log_level_info = {'logging.DEBUG': logging.DEBUG,
                      'logging.INFO': logging.INFO,
                      'logging.WARNING': logging.WARNING,
                      'logging.ERROR': logging.ERROR,
                      }

    config = configparser.ConfigParser()
    config.read(config_file)
    _config_info['log_level'] = log_level_info.get(config['LOGGING']['LOG_LEVEL'], logging.ERROR)
    _config_info['ignore_serial_error'] = config.getboolean('LOGGING', 'IGNORE_SERIAL_ERROR')
    _config_info['serial_port'] = config['SERIAL']['PORT']
    _config_info['baud_rate'] = config['SERIAL']['BAUDRATE']
    _config_info['sample_time_seconds'] = config.getint('SERIAL', 'SAMPLE_SECONDS')
    return _config_info


def find_active_soundcard():
    """
    Searches all cards defined to alsa and returns the first one with status=RUNNING

    :return: _soundcard: the fully qualified name of the active alsa soundcard subdevice '/proc/asound/card?/pcm?p/sub?'
    """
    for sub_device in glob.glob(f'/proc/asound/card**/pcm**p/sub*'):
        try:
            with open(os.path.join(sub_device, 'status'), 'r') as f:
                status = f.read()
            if "RUNNING" in status:
                log.info(sub_device)
                log.info(status)
                _soundcard = sub_device
                return _soundcard
        except (FileNotFoundError, IOError):
            pass
    raise NoActiveSoundcard


def find_sample_rate_bit_depth(_soundcard):
    """
    Returns the sample_rate and bit_depth currently being played on the input soundcard

    :param: _soundcard: the fully qualified name of the active alsa soundcard subdevice '/proc/asound/card?/pcm?p/sub?'
    :return: _sample_rate: the sample rate of currently playing sound, from the file 'hw_parms' of the input soundcard
    :return: _bit_depth: the bit depth of currently playing sound, from the file 'hw_parms' of the input soundcard
    """
    bit_depth_pattern = r"format: S([0-9]+)_LE"
    sample_rate_pattern = r"rate: ([0-9]+) \("
    try:
        with open(f"{_soundcard}/hw_params", 'r') as f:
            hw_params = f.read()
        try:
            _sample_rate = re.search(sample_rate_pattern, hw_params).group(1)
            _bit_depth = re.search(bit_depth_pattern, hw_params).group(1)
            log.info(hw_params)
            return _sample_rate, _bit_depth
        except AttributeError:
            raise NoActiveSoundcard
    except (FileNotFoundError, IOError):
        raise NoActiveSoundcard


def find_new_soundcard_and_sample_rate():
    """
    Combines find_active_soundcard and find_sample_rate_bit_depth into one helper function

    :return: _soundcard: the fully qualified name of the active alsa soundcard subdevice '/proc/asound/card?/pcm?p/sub?'
    :return: _sample_rate: the sample rate of currently playing sound, from the file 'hw_parms' of the input soundcard
    :return: _bit_depth: the bit depth of currently playing sound, from the file 'hw_parms' of the input soundcard
    """
    try:
        _soundcard = find_active_soundcard()
        _sample_rate, _bit_depth = find_sample_rate_bit_depth(_soundcard)
    except NoActiveSoundcard:
        _soundcard, _sample_rate, _bit_depth = None, 0, 0
    return _soundcard, _sample_rate, _bit_depth


def signal_sample_rate(_soundcard):
    """
    Sends the current sample_rate and bit_depth to the serial device

    :param: _soundcard: the fully qualified name of the active alsa soundcard subdevice '/proc/asound/card?/pcm?p/sub?'
    :return: _soundcard: the fully qualified name of the active alsa soundcard subdevice '/proc/asound/card?/pcm?p/sub?'
             This may be different to the input parameter if _soundcard had been stopped, started, or changed
    """
    try:  # Assume the last active soundcard is still Active
        _sample_rate, _bit_depth = find_sample_rate_bit_depth(_soundcard)
    except NoActiveSoundcard:  # Nope, it's changed - maybe turned on/off or maybe user chase a different soundcard
        _soundcard, _sample_rate, _bit_depth = find_new_soundcard_and_sample_rate()
    serial_dev_write(serial_dev, _sample_rate, _bit_depth)  # Write sample_rate/bit_depth to the serial device
    return _soundcard


def serial_dev_init(_serial_port, _baud_rate):
    """
    Simply initialise the serial port device - parameters are at the top of the code

    If we want just to test the alsa code, getting the soundcard and sample_rate etc. then ignore_serial_error can be
    set to True (via the config file)

    :param: _serial_port: the string value of the serial port to be initialised
    :param: _baud_rate: the integer baudrate of the serial port
    :return: _serial_dev: the initialised serial device object

    """
    try:
        _serial_dev = serial.Serial(port=_serial_port, baudrate=_baud_rate, timeout=.1)
        return _serial_dev
    except serial.SerialException:
        if not ignore_serial_error:
            raise NoSerialDevice
        pass


def serial_dev_write(_serial_dev, _sample_rate, _bit_depth):
    """
    Write the encoded sample_rate and bit_depth encoded to the serial port
    Encoding is sample_rate_index*8+bit_depth_index - the indexes are from sample_rate_dict and bit_depth_dict
    Should be able to send as an integer, but I can't make this work so encode as a single char
    Note, not sound card has sample_rate=0 and invalid/unknown sample_rate will be sent as sample_rate_dict[-1]
    Code in the serial device is responsible for decoding these values

    If we want just to test the alsa code, getting the soundcard and sample_rate etc. then ignore_serial_error can be
    set to True (via the config file)

    :param: _serial_port: the initialised serial port to send the data to
    :param: _sample_rate: the sample rate of currently playing sound, from the file 'hw_parms' of the input soundcard
    :param: _bit_depth: the bit depth of currently playing sound, from the file 'hw_parms' of the input soundcard
    """

    sample_rate_dict = {0: 0, 44100: 1 * 8, 48000: 2 * 8, 88200: 3 * 8, 96000: 4 * 8, 176400: 5 * 8, 192000: 6 * 8,
                        3528000: 7 * 8, 384000: 8 * 8, -1: 9 * 8}
    bit_depth_dict = {0: 0, 16: 1, 24: 2, 32: 3, -1: 4}

    log.info(f"Sample_rate = {_sample_rate}, bit_depth= {_bit_depth}")
    try:
        serial_val = str(sample_rate_dict[int(_sample_rate)] + bit_depth_dict[int(_bit_depth)])
    except KeyError:
        serial_val = str(sample_rate_dict[-1] + bit_depth_dict[-1])
    log.info(serial_val)
    try:
        _serial_dev.write(bytes(serial_val, 'utf-8'))
    except AttributeError:
        if not ignore_serial_error:
            raise NoSerialDevice
        pass


if __name__ == "__main__":
    """
    Main code 
    
    Get config info
    Set up logging
    Initialise Serial port
    
    loop forever finding the sample rate and bit depth of any active soundcard (first one found) every n seconds
    """
    config_info = read_config_info('config.ini')

    logging.basicConfig(level=config_info['log_level'], filename='alsa_indicator.log',filemode = 'w',
                        format = "%(levelname)s %(asctime)s - %(message)s")
    log = logging.getLogger()
    log.info("Alsa_indicator started")


    ignore_serial_error = config_info['ignore_serial_error']
    if ignore_serial_error:
        log.info("Alsa test mode, ignoring any Serial port errors")
    serial_dev = serial_dev_init(config_info['serial_port'], config_info['baud_rate'])
    sample_time_seconds = config_info['sample_time_seconds']

    soundcard = None

    log.info("Setup complete")

    while True:
        soundcard = signal_sample_rate(soundcard)
        time.sleep(sample_time_seconds)
