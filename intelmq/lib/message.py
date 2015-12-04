# -*- coding: utf-8 -*-
"""
Messages are the information packages in pipelines.

Use MessageFactory to get a Message object (types Report and Event).
"""
from __future__ import unicode_literals
import hashlib
import json
import re
import six

import intelmq.lib.exceptions as exceptions
import intelmq.lib.harmonization
from intelmq import HARMONIZATION_CONF_FILE
from intelmq.lib import utils


harm_config = utils.load_configuration(HARMONIZATION_CONF_FILE)


class MessageFactory(object):
    """
    unserialize: JSON encoded message to object
    serialize: object to JSON encoded object
    """    

    @staticmethod
    def from_dict(message):
        """
        Takes dictionary Message object, returns instance of correct class.

        The class is determined by __type attribute.
        """
        try:
            class_reference = getattr(intelmq.lib.message, message["__type"])
        except AttributeError:
            raise exceptions.InvalidArgument('__type',
                                             got=message["__type"],
                                             expected=list(harm_config.keys()),
                                             docs=HARMONIZATION_CONF_FILE)
        del message["__type"]
        return class_reference(message)

    @staticmethod
    def unserialize(raw_message):
        """
        Takes JSON-encoded Message object, returns instance of correct class.

        The class is determined by __type attribute.
        """
        message = Message.unserialize(raw_message)
        try:
            #logger = utils.log("message log nee",log_level='DEBUG')
            #logger.info(message)
            #if "__type" in message:
                #logger.info("OK EDVARD INFO")
            class_reference = getattr(intelmq.lib.message, message["__type"])
            #elif type in message:
#                logger.info("NOT OK EDVARD INFO")
#                class_reference = getattr(intelmq.lib.message, message["type"])
#            else:
#                logger.info("KLURVAAAAAAAAAA TADY BUDE CHYBA PITOMY INTELMQ")
#                raise "Edvarde, sem to nesmi dospet"
        except AttributeError:
            logger.info("TOHLE JE TA SPATNA MESSAGE")
            logger.info(message)
            raise exceptions.InvalidArgument('__type',
                                             got=message["__type"],
                                             expected=list(harm_config.keys()),
                                             docs=HARMONIZATION_CONF_FILE)
        del message["__type"]
        return class_reference(message)

    @staticmethod
    def serialize(message):
        """
        Takes instance of message-derived class and makes JSON-encoded Message.

        The class is saved in __type attribute.
        """
        raw_message = Message.serialize(message)
        return raw_message


class Message(dict):

    def __init__(self, message=()):
        super(Message, self).__init__(message)
        try:
            classname = message['__type'].lower()
            del message['__type']
        except (KeyError, TypeError):
            classname = self.__class__.__name__.lower()

        try:
            self.harmonization_config = harm_config[classname]
        except KeyError:
            raise exceptions.InvalidArgument('__type',
                                             got=classname,
                                             expected=list(harm_config.keys()),
                                             docs=HARMONIZATION_CONF_FILE)

    def __setitem__(self, key, value):
        self.add(key, value)

    def add(self, key, value, sanitize=False, force=False, ignore=()):
        if not force and key in self:
            raise exceptions.KeyExists(key)

        if value is None or value == "":
            return

        for invalid_value in ["-", "N/A"]:
            if value == invalid_value:
                return

        if not self.__is_valid_key(key):
            raise exceptions.InvalidKey(key)

        try:
            if value in ignore:
                return
        except TypeError:
            raise exceptions.InvalidArgument('ignore',
                                             got=type(ignore),
                                             expected='list or tuple')

        if sanitize:
            old_value = value
            value = self.__sanitize_value(key, value)
            if value is None:
                raise exceptions.InvalidValue(key, old_value)

        valid_value = self.__is_valid_value(key, value)
        if not valid_value[0]:
            raise exceptions.InvalidValue(key, value, reason=valid_value[1])

        super(Message, self).__setitem__(key, value)

    def value(self, key):  # TODO: Remove? Use get instead
        return self.__getitem__(key)

    def update(self, key, value, sanitize=False):
        if key not in self:
            raise exceptions.KeyNotExists(key)
        self.add(key, value, force=True, sanitize=sanitize)

    def clear(self, key):  # TODO: Remove? Use del instead
        self.__delitem__(key)

    def contains(self, key):
        return key in self

    def finditems(self, keyword):
        for key, value in super(Message, self).items():
            if key.startswith(keyword):
                yield key, value

    def copy(self):
        class_ref = self.__class__.__name__
        #logger = utils.log("message log",log_level='DEBUG')
        #logger.info("set type copy" + str(class_ref))
        self['__type'] = class_ref
        retval = getattr(intelmq.lib.message,
                         class_ref)(super(Message, self).copy())
        del self['__type']
        del retval['__type']
        return retval

    def deep_copy(self):
        return MessageFactory.unserialize(MessageFactory.serialize(self))

    def __unicode__(self):
        return self.serialize()

    def __str__(self):
        return self.serialize()

    def serialize(self):
        #logger = utils.log("message log",log_level='DEBUG')
        #logger.info("set type serialize" + str(self.__class__.__name__))
        self['__type'] = self.__class__.__name__
        json_dump = utils.decode(json.dumps(self))
        del self['__type']
        return json_dump

    @staticmethod
    def unserialize(message_string):
        message = json.loads(message_string)
        return message

    def __is_valid_key(self, key):
        if key in self.harmonization_config or key == '__type':
            return True
        return False

    def __is_valid_value(self, key, value):
        if key == '__type':
            return (True, )
        config = self.__get_type_config(key)
        class_reference = getattr(intelmq.lib.harmonization, config['type'])
        if not class_reference().is_valid(value):
            logger = utils.log("edvard",log_level='DEBUG')
            logger.info(config['type'])
            logger.info(intelmq.lib.harmonization)
            logger.info(config)
            logger.info(class_reference())
            logger.info(value)
            return (False, 'is_valid returned False.')
        if 'length' in config:
            length = len(six.text_type(value))
            if not length <= config['length']:
                return (False, 'too long: {} > {}.'.format(length,
                                                           config['length']))
        if 'regex' in config:
            if not re.search(config['regex'], six.text_type(value)):
                return (False, 'regex did not match.')
        return (True, )

    def __sanitize_value(self, key, value):
        class_name = self.__get_type_config(key)['type']
        class_reference = getattr(intelmq.lib.harmonization, class_name)
        return class_reference().sanitize(value)

    def __get_type_config(self, key):
        class_name = self.harmonization_config[key]
        return class_name


class Event(Message):

    def __init__(self, message=()):
        """
        Parameters
        ----------
        message : dict
            Give a report and feed.name, feed.url and
            time.observation will be used to construct the Event if given.
        """
        if isinstance(message, Report):
            template = {}
            if 'feed.name' in message:
                template['feed.name'] = message['feed.name']
            if 'feed.url' in message:
                template['feed.url'] = message['feed.url']
            if 'feed.accuracy' in message:
                template['feed.accuracy'] = message['feed.accuracy']
            if 'time.observation' in message:
                template['time.observation'] = message['time.observation']
        else:
            template = message
        super(Event, self).__init__(template)

    def __hash__(self):
        event_hash = hashlib.sha256()

        for key, value in sorted(self.items()):
            if "time.observation" == key:
                continue

            event_hash.update(utils.encode(key))
            event_hash.update(b"\xc0")
            event_hash.update(utils.encode(repr(value)))
            event_hash.update(b"\xc0")

        return int(event_hash.hexdigest(), 16)

    def to_dict(self):
        json_dict = dict()

        for key, value in self.items():
            subkeys = key.split('.')
            json_dict_fp = json_dict

            for subkey in subkeys:
                if subkey == subkeys[-1]:
                    json_dict_fp[subkey] = value
                    break

                if subkey not in json_dict_fp:
                    json_dict_fp[subkey] = dict()

                json_dict_fp = json_dict_fp[subkey]
        return json_dict

    def to_json(self):
        json_dict = self.to_dict()
        return utils.decode(json.dumps(json_dict, ensure_ascii=False))


class Report(Message):
    pass
