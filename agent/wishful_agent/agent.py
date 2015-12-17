import logging
import sys
import zmq
import uuid
import msgpack
import time
import datetime
import os
import subprocess
import re
import socket
from apscheduler.schedulers.background import BackgroundScheduler
import yaml

__author__ = "Piotr Gawlowicz"
__copyright__ = "Copyright (c) 2015, Technische Universitat Berlin"
__version__ = "0.1.0"
__email__ = "gawlowicz@tkn.tu-berlin.de"

class Agent(object):
    def __init__(self, controllerDL=None, controllerUL=None, bnInterface=None, hostname=None, sutMac=None, config=None):
        self.log = logging.getLogger("{module}.{name}".format(
            module=self.__class__.__module__, name=self.__class__.__name__))

        self.myUuid = uuid.uuid4()
        self.myUuidStr = str(self.myUuid)

        if config:
            with open(config, 'r') as f:
                config = yaml.load(f)
                hostname = config['hostname']
                bnInterface = config['bnInterface']
                sutMac = config['sutMac']
                controllerDL = config['controllerDL']
                controllerUL = config['controllerUL']

        self.log.debug("Hostname : {}, BN interface : {}, Connected DUT : {}".format(hostname, bnInterface, sutMac))
        self.log.debug("Controller DL: {0}, UL: {1}".format(controllerDL, controllerUL))

        if hostname:
            self.myName = hostname
        else:
            self.myName = socket.gethostname()

        self.connectedSutNodeMac = sutMac

        self.bnInterface = bnInterface
        self.qDiscConifg = None

        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)
        self.jobScheduler = BackgroundScheduler()
        self.jobScheduler.start()

        self.connectedToController = False
        self.controllerDL = controllerDL
        self.controllerUL = controllerUL
        self.reconnectionJob = None
        self.connectionRequestSent = False

        self.echoMsgInterval = 3
        self.echoTimeOut = 10
        self.echoSendJob = None
        self.connectionLostJob = None 

        self.poller = zmq.Poller()
        self.context = zmq.Context()
        self.dl_socket = self.context.socket(zmq.SUB) # for downlink communication with controller
        self.dl_socket.setsockopt(zmq.SUBSCRIBE,  "ALL")
        self.dl_socket.setsockopt(zmq.SUBSCRIBE,  self.myUuidStr)
        self.ul_socket = self.context.socket(zmq.PUB) # for uplink communication with controller

        #register downlink socket in poller
        self.poller.register(self.dl_socket, zmq.POLLIN)


    def connectToController(self):
        self.log.debug("Agent connects controller: DL:{0}, UL:{1}".format(self.controllerDL, self.controllerUL))

        if self.connectionRequestSent:
            try:
                self.dl_socket.disconnect(self.controllerDL)
                self.ul_socket.disconnect(self.controllerUL)
            except:
                pass

        self.dl_socket.connect(self.controllerDL)
        self.ul_socket.connect(self.controllerUL)

        topic = "NEW_NODE"
        cmd = 'add_new_node'
        msg = msgpack.packb({'uuid':self.myUuidStr, 'name':self.myName, 'sut_node_mac' : self.connectedSutNodeMac})

        self.log.debug("Agent sends context-setup request to controller")
        time.sleep(1) # wait until zmq agree on topics
        self.ul_socket.send("%s %s %s" % (topic, cmd, msg))

        self.connectionRequestSent = True

        #schedule reconnection job that will be canceled if NewNodeAck is received
        execTime =  str(datetime.datetime.now() + datetime.timedelta(seconds=5))
        self.log.debug("Schedule reconnection function".format())
        self.reconnectionJob = self.jobScheduler.add_job(self.connectToController, 'date', run_date=execTime)

    def serve_new_node_ack(self, msg):
        self.log.debug("Agend received NewNodeAck from Controller".format())
        self.reconnectionJob.remove()

        #start sending hello msgs
        execTime =  str(datetime.datetime.now() + datetime.timedelta(seconds=self.echoMsgInterval))
        self.log.debug("Agent schedule sending of Hello message".format())
        self.echoSendJob = self.jobScheduler.add_job(self.send_hello_msg, 'date', run_date=execTime)

        execTime = datetime.datetime.now() + datetime.timedelta(seconds=self.echoTimeOut)
        self.connectionLostJob = self.jobScheduler.add_job(self.connection_to_controller_lost, 'date', run_date=execTime)

    def connection_to_controller_lost(self):
        self.log.debug("Lost connection with controller".format())

        if self.connectionRequestSent:
            try:
                self.dl_socket.disconnect(self.controllerDL)
                self.ul_socket.disconnect(self.controllerUL)
            except:
                pass

        self.connectionRequestSent = False

        self.echoSendJob.remove()

        #schedule reconnection job that will be canceled if NewNodeAck is received
        execTime =  str(datetime.datetime.now() + datetime.timedelta(seconds=1))
        self.log.debug("Schedule reconnection function".format())
        self.reconnectionJob = self.jobScheduler.add_job(self.connectToController, 'date', run_date=execTime)

    def terminate_connection_to_controller(self):
        self.log.debug("Agend sends NodeExitMsg to Controller".format())
        topic = "NODE_EXIT"
        cmd = 'remove_node'
        msg = msgpack.packb({'uuid':self.myUuidStr, 'reason':'Agent_Process_Exit'})
        self.ul_socket.send("%s %s %s" % (topic, cmd, msg))

    def send_hello_msg(self):
        self.log.debug("Sending Hello message to controller".format())
        topic = "Controller"
        cmd = "HelloMsg"
        msg = msgpack.packb({"source": self.myUuidStr})
        self.ul_socket.send("%s %s %s" % (topic, cmd, msg))

        #reschedule hello msg
        self.log.debug("Re-schedule sending of Hello message function".format())
        execTime =  datetime.datetime.now() + datetime.timedelta(seconds=self.echoMsgInterval)
        self.echoSendJob = self.jobScheduler.add_job(self.send_hello_msg, 'date', run_date=execTime)

    def serve_hello_msg(self, msg):
        self.log.debug("Agend received Hello Message from {}".format(msg["source"]))

        #reschedule connection lost function
        if self.connectionLostJob:
            self.connectionLostJob.remove()
            execTime = datetime.datetime.now() + datetime.timedelta(seconds=self.echoTimeOut)
            self.connectionLostJob = self.jobScheduler.add_job(self.connection_to_controller_lost, 'date', run_date=execTime)


    def install_egress_scheduler(self, qdisc_config):
        self.log.debug("Configure Qdisc".format())

        self.qDiscConifg = qdisc_config
        interface = self.bnInterface

        rootQdisc = qdisc_config["root"]
        rootQdiscParams = rootQdisc["params"]

        queues = qdisc_config["queues"]
        filters = qdisc_config["filters"]

        self.log.debug("Clear root qdisc in interface : {}".format(interface))
        cmd = "tc qdisc del dev {} root".format(interface)
        os.system(cmd)

        self.log.debug("Install root qdisc in interface : {}, type : {}".format(interface, rootQdisc["type"]))
        cmd = "tc qdisc add dev {0} root handle {1} {2} ".format(interface, rootQdisc["handle"], rootQdisc["type"])
        for param in rootQdiscParams:
            cmd = cmd + "{} {} ".format(param["key"],param["value"])

        os.system(cmd)

        self.log.debug("Install queues in interface : {}".format(interface))
        for q in queues:
            qparams = q["params"]
            cmd = "tc qdisc add dev {} parent {} handle {} {} ".format(interface, q["parent"], q["handle"], q["type"])

            for param in qparams:
                cmd = cmd + "{} {} ".format(param["key"],param["value"])

            os.system(cmd)

        self.log.debug("Install filters in interface : {}".format(interface))
        for f in filters:
            self.log.debug("Installing filter : {}".format(f["name"]))
            config = f["config"]
            flow_desc = config["flow_desc"]
            srcAddress = flow_desc["srcAddress"]
            dstAddress = flow_desc["dstAddress"]
            proto = flow_desc["proto"]
            srcPort = flow_desc["srcPort"]
            dstPort = flow_desc["dstPort"]

            cmd = "tc filter add dev {} parent {} protocol ip prio {} ".format(interface, config["parent"], config["priority"] )

            if not srcAddress and not dstAddress and not proto and not srcPort and not dstPort:
                self.log.debug("Installing default filter : {}".format(f["name"]))
                #sudo tc filter add dev eth0 parent 1:0 protocol ip prio 2 u32 match u32 0 0 flowid 1:6
                cmd = cmd + "u32 match u32 0 0 ".format()
                cmd = cmd + "flowid {}".format(config["target"])
                os.system(cmd)
                continue

            if srcAddress or dstAddress or proto or srcPort or dstPort:
                cmd = cmd + "u32 ".format()

            if srcAddress is not None:
                cmd = cmd + "match ip src {}/32 ".format(srcAddress)

            if dstAddress is not None:
                cmd = cmd + "match ip dst {}/32 ".format(dstAddress)

            if proto is not None:
                if proto == 'tcp':
                    cmd = cmd + "match ip protocol 6 0xff "
                elif proto == 'udp':
                    cmd = cmd + "match ip protocol 17 0xff "

            if srcPort is not None:
                cmd = cmd + "match ip sport {} 0xffff ".format(srcPort)

            if dstPort is not None:
                cmd = cmd + "match ip dport {} 0xffff ".format(dstPort)

            cmd = cmd + "flowid {}".format(config["target"])

            os.system(cmd)

        self.log.debug("Qdisc setup completed".format())

    def set_channel(self, msg):
        channel = msg
        self.log.debug("Set channel {}".format(channel))

        interface = self.bnInterface

        #TODO: set channel for BN interface
        self.log.debug("Configure new channel {} for interface: {}".format(channel, interface))

    def monitor_transmission_parameters(self, msg):
        self.log.debug("Monitoring interface {}, parameters: {}".format(self.bnInterface, msg))
        parameters = msg["parameters"]

        result = {}
        if "droppedPackets" in parameters:
            qdiscId = 1
            droppedPackets = []
            cmd = ['/sbin/tc','-s','-d', 'qdisc', 'show', 'dev', self.bnInterface]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            lines_iterator = iter(process.stdout.readline, b"")
            for line in lines_iterator:
                if "dropped" in line:
                    numbers = re.findall(r'\d+', line)
                    droppedPackets.append({"qdiscId": qdiscId, "droppedPkts" : numbers[2]})
                    qdiscId += 1
            result["droppedPackets"] = droppedPackets

        #send response to controller
        self.log.debug("Send monitoring result to controller".format())

        topic = self.myUuidStr
        cmd = 'monitor_transmission_parameters_response'
        msg = msgpack.packb(result)
        self.ul_socket.send("%s %s %s" % (topic, cmd, msg))

    def process_msgs(self):
        # Work on requests from controller
        while True:
            socks = dict(self.poller.poll())

            if self.dl_socket in socks and socks[self.dl_socket] == zmq.POLLIN:
                msg = self.dl_socket.recv()
                topic, cmd, msg = msg.split(" ")
                msg = msgpack.unpackb(msg)
                self.log.debug("Agent received cmd : {} on topic {}".format(cmd, topic))

                if cmd == "NewNodeAck":
                    self.serve_new_node_ack(msg)
                elif cmd == "HelloMsg":
                    self.serve_hello_msg(msg)
                elif cmd == "install_egress_scheduler":
                    self.install_egress_scheduler(msg)
                elif cmd == "set_channel":
                    self.set_channel(msg)
                elif cmd == "monitor_transmission_parameters":
                    self.monitor_transmission_parameters(msg)
                else:
                    self.log.debug("Operation not supported")


    def run(self):
        self.log.debug("Agent starting".format())
        self.connectToController()

        try:
            self.process_msgs()

        except KeyboardInterrupt:
            self.log.debug("Agent exits")

        except:
            self.log.debug("Unexpected error:".format(sys.exc_info()[0]))

        finally:
            self.terminate_connection_to_controller()
            self.log.debug("Exit")
            self.dl_socket.close()
            self.ul_socket.close()
            self.context.term()