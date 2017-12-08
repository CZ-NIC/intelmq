from __future__ import unicode_literals
import sys
from glob import glob
from intelmq.lib.bot import Bot
import json
from netaddr import IPNetwork, IPAddress

class CustomFilterExpertBot(Bot):    
    filters = {}

    def meet_condition(self, message):                           
        includable = None
        for filterO in self.filters.values():
            conforming = False
            for key, values in filterO["conditions"].items():                
                try:                    
                    if not isinstance(values, list):
                        values = [values] # the values can be list or string
                    if key in ["source.ip"]: # expand network masks
                        for val in values:
                            if ("/" in val and IPAddress(message[key]) in IPNetwork(val)) or message[key] == val:
                                conforming = True
                                break
                    elif message[key] in values:
                        conforming = True                                            
                                          
                    #if (isinstance(values, list) and message[key] in values) or values == message[key]: # filter passed                                                
                    #    conforming = True
                    else:                        
                        conforming = False
                        break
                except KeyError:                    
                    conforming = False
                    break
            
            if conforming:
                if filterO["type"] == "include":
                    includable = True
                elif filterO["type"] == "exclude":                      
                    return False
            elif filterO["type"] == "include" and includable is None:
                includable = False                
                    
        if includable is None:
            return True # none of the filters matched
        return includable 

    def init(self):        
        """ Loads rules from .json """        
        for i, rule_file in enumerate(glob(self.parameters.rules_dir + "*.json")):
            with open(rule_file, 'r') as f:
                rule = json.load(f)                
                CustomFilterExpertBot.filters[i] = rule            

    def process(self):
        message = self.receive_message()        
        if message and self.meet_condition(message):
            self.send_message(message)
            self.logger.info("PASSING message: " + repr(message) + ".") # .debug not displayed until an .error is called
        else:
            self.logger.info("Dropping message: " + repr(message) + ".")
        self.acknowledge_message()
     

BOT = CustomFilterExpertBot
