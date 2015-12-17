import logging
import time
import datetime
import sys
import zmq
import uuid
import msgpack
from apscheduler.schedulers.background import BackgroundScheduler
import yaml

import pytc

__author__ = "Piotr Gawlowicz"
__copyright__ = "Copyright (c) 2015, Technische Universität Berlin"
__version__ = "0.1.0"
__email__ = "gawlowicz@tkn.tu-berlin.de"

class Node(object):
    def __init__(self, uuid, name, sut_mac):
        self.uuid = uuid
        self.name = name
        self.connectedSut = sut_mac

class Controller(object):
    def __init__(self, dl=None, ul=None, nodeList=None, tms=None, config=None):
        self.log = logging.getLogger("{module}.{name}".format(
            module=self.__class__.__module__, name=self.__class__.__name__))

        self.myUuid = uuid.uuid4()
        self.myUuidStr = str(self.myUuid)
        self.qdisc_config_desc = None

        if config:
            with open(config, 'r') as f:
                config = yaml.load(f)
                tms = config['tms']
                dl = config['dl']
                ul = config['ul']
                nodeList = config['bnNodeList']
                self.qdisc_config_desc = config['qdisc']

        self.log.debug("TMS : {}".format(tms))
        self.log.debug("Controller DL: {0}, UL: {1}".format(dl, ul))
        self.log.info("Waiting for nodes: [" + ", ".join(nodeList) + "]")
        self.expectedNodeList = nodeList
        self.nodes = []

        self.qdisc_config = None
        self.bnChannel = 11
        self.availableChannels = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,40,44,48,52,56,60]

        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)
        self.jobScheduler = BackgroundScheduler()
        self.jobScheduler.start()

        self.echoMsgInterval = 3
        self.echoTimeOut = 10
        self.echoSendJob = None
        self.connectionLostJobs = {}

        #start sending hello msgs
        execTime =  str(datetime.datetime.now() + datetime.timedelta(seconds=self.echoMsgInterval))
        self.log.debug("Schedule sending of Hello message function".format())
        self.echoSendJob = self.jobScheduler.add_job(self.send_hello_msg, 'date', run_date=execTime)

        self.context = zmq.Context()
        self.poller = zmq.Poller()

        self.ul_socket = self.context.socket(zmq.SUB) # one SUB socket for uplink communication over topics
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  "ALL")
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  "NEW_NODE")
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  "NODE_EXIT")
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  "RESPONSE")
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  "Controller")
        self.ul_socket.bind(ul)

        self.dl_socket = self.context.socket(zmq.PUB) # one PUB socket for downlink communication over topics
        self.dl_socket.bind(dl)

        self.tms = tms
        self.tms_socket = self.context.socket(zmq.PAIR)
        self.tms_socket.bind(tms)

        #register UL socket in poller
        self.poller.register(self.ul_socket, zmq.POLLIN)
        self.poller.register(self.tms_socket, zmq.POLLIN)


    def add_new_node(self, msg):
        self.log.debug("Adding new node with UUID: {},  Name: {}, Connected SUT: {}".format(msg['uuid'], \
                                                        msg['name'], msg['sut_node_mac']))
        newNode = Node(msg['uuid'], msg['name'], msg['sut_node_mac'])
        self.nodes.append(newNode)

        self.log.info("Node: {} with SUT: {} connected".format(msg['name'], msg['sut_node_mac']))
        connectedList = map(lambda n: n.name, self.nodes)
        waitingList = set(self.expectedNodeList) - set(connectedList)
        self.log.info("Waiting for nodes: [" + ", ".join(waitingList) + "]")

        #subscribe to node UUID
        self.ul_socket.setsockopt(zmq.SUBSCRIBE,  newNode.uuid)
        time.sleep(1)

        #schedule connection lost job
        execTime = datetime.datetime.now() + datetime.timedelta(seconds=self.echoTimeOut)
        self.connectionLostJobs[msg['uuid']] = self.jobScheduler.add_job(self.connection_to_agent_lost, 'date', run_date=execTime, kwargs={'lostNodeUuid' : msg['uuid']})
        
        #send ack
        self.log.debug("Sending NewNodeAck".format())
        #send QDisc configuration to agent
        topic = newNode.uuid
        cmd = "NewNodeAck"
        msg = msgpack.packb({"source":"controller"})
        self.dl_socket.send("%s %s %s" % (topic, cmd, msg))

        return newNode

    def connection_to_agent_lost(self, lostNodeUuid):
        self.log.debug("Lost connection with node with UUID: {}".format(lostNodeUuid))
        lostNode = None
        for node in self.nodes:
            if node.uuid == lostNodeUuid:
                lostNode = node
                self.nodes.remove(node)
      
        if lostNode: 
            self.log.info("Lost connection to node: {} with SUT: {}".format(lostNode.name, lostNode.connectedSut))
            connectedList = map(lambda n: n.name, self.nodes)
            waitingList = set(self.expectedNodeList) - set(connectedList)
            self.log.info("Waiting for nodes: [" + ", ".join(waitingList) + "]")      

    def remove_node(self, msg):
        self.log.debug("Removing node with UUID: {}, Reason: {}".format(msg['uuid'], msg['reason']))

        lostNode = None
        for node in self.nodes:
            if node.uuid == msg['uuid']:
                lostNode = node
                self.nodes.remove(node)

        #remove function job
        if lostNode.uuid in self.connectionLostJobs:
            self.connectionLostJobs[lostNode.uuid].remove()

        if lostNode: 
            self.log.info("Node: {} with SUT: {} disconnected".format(lostNode.name, lostNode.connectedSut))
            connectedList = map(lambda n: n.name, self.nodes)
            waitingList = set(self.expectedNodeList) - set(connectedList)
            self.log.info("Waiting for nodes: [" + ", ".join(waitingList) + "]") 


    def send_hello_msg(self):
        if self.nodes:
            self.log.debug("Sending Hello message".format())
            topic = "ALL"
            cmd = "HelloMsg"
            msg = msgpack.packb({"source":"controller"})
            self.dl_socket.send("%s %s %s" % (topic, cmd, msg))

        #reschedule hello msg
        self.log.debug("Re-schedule sending of Hello message function".format())
        execTime =  datetime.datetime.now() + datetime.timedelta(seconds=self.echoMsgInterval)
        self.echoSendJob = self.jobScheduler.add_job(self.send_hello_msg, 'date', run_date=execTime)

    def serve_hello_msg(self, msg):
        self.log.debug("Controller received Hello Message from {}".format(msg["source"]))

        #reschedule remove function
        if msg['source'] in self.connectionLostJobs:
            self.connectionLostJobs[msg['source']].remove()
            execTime = datetime.datetime.now() + datetime.timedelta(seconds=self.echoTimeOut)
            self.connectionLostJobs[msg['source']] = self.jobScheduler.add_job(self.connection_to_agent_lost, 'date', run_date=execTime, kwargs={'lostNodeUuid' : msg['source']})


    def create_qdisc_config_bn_interface(self):

        root_desc = self.qdisc_config_desc['root']
        queues_desc = self.qdisc_config_desc['queues']
        filters_desc = self.qdisc_config_desc['filters']

        qdiscConfig = pytc.QdiscConfig()

        if root_desc['type'] == 'PRIO':
            rootSched = pytc.PrioScheduler(bandNum=root_desc['params']['bands'])
        else:
            rootSched = pytc.PrioScheduler(bandNum=6)

        qdiscConfig.set_root_qdisc(rootSched)

        queues = {}

        for q_desc in queues_desc:
            queues[q_desc['id']] = rootSched.addQueue(pytc.PfifoQueue(limit=q_desc['limit']))
            qdiscConfig.add_queue(queues[q_desc['id']])


        def convertStr(myObj):
            if isinstance(myObj, basestring) and myObj == 'None':
                    return None
            else:
                return myObj

        for f_desc in filters_desc:
            tmp_filter = pytc.Filter(name=f_desc['name'])
            fiveTuple = f_desc['fiveTuple']
            tmp_filter.setFiveTuple(
                                    src=convertStr(fiveTuple['src']),
                                    dst=convertStr(fiveTuple['dst']),
                                    prot=convertStr(fiveTuple['prot']),
                                    srcPort=convertStr(fiveTuple['srcPort']),
                                    dstPort=convertStr(fiveTuple['dstPort'])
                                    )
            tmp_filter.setTarget(queues[f_desc['targetQueueId']])
            tmp_filter.setTos(f_desc['TOS'])
            tmp_filter.setFilterPriority(f_desc['priority'])
            rootSched.addFilter(tmp_filter)
            qdiscConfig.add_filter(tmp_filter)

        self.qdisc_config = qdiscConfig


    def install_egress_scheduler(self, node):
        self.log.debug("Sending QDisc config to node with UUID: {}".format(node.uuid))

        if not self.qdisc_config:
            self.create_qdisc_config_bn_interface()

        #send QDisc configuration to agent
        topic = node.uuid
        cmd = "install_egress_scheduler"
        msg = msgpack.packb(self.qdisc_config.serialize())
        self.dl_socket.send("%s %s %s" % (topic, cmd, msg))

    def set_channel(self, node, channel):
        self.log.debug("Set channel {} to node with UUID: {}".format(channel, node.uuid))

        topic = node.uuid
        cmd = "set_channel"
        msg = msgpack.packb(channel)
        self.dl_socket.send("%s %s %s" % (topic, cmd, msg))

    def monitor_transmission_parameters(self, node):
        self.log.debug("Monitor transmission parameters of BN interface in node with UUID: {}".format(node.uuid))

        topic = node.uuid
        cmd = "monitor_transmission_parameters"
        msg = {"parameters" : ["droppedPackets"]}
        msg = msgpack.packb(msg)
        self.dl_socket.send("%s %s %s" % (topic, cmd, msg))

    def monitor_transmission_parameters_response(self, msg):
        self.log.debug("Monitor transmission parameters response : {}".format(msg))

    def open_connection_to_tms(self):
        pass

    def close_connection_with_tms(self):
        cmd = "EXIT"
        msg = "EXIT"
        msg = msgpack.packb(msg)
        self.tms_socket.send("%s %s" % (cmd, msg))

    def get_sut_nodes_list(self):
        sut_node_list = []
        for node in self.nodes:
            sut_node_list.append(node.connectedSut)

        cmd = "sut_node_list_response"
        msg = sut_node_list
        msg = msgpack.packb(msg)
        self.tms_socket.send("%s %s" % (cmd, msg))

    def recv_channel_list(self,usedChannelList):
        self.log.info("Received used channel list: [" + ", ".join(str(x) for x in usedChannelList) + "]")

        #choose one free channel
        freeChannels = set(self.availableChannels) - set(usedChannelList)
        self.bnChannel = list(freeChannels)[0]

        cmd = "bn_channel_response"
        msg = self.bnChannel
        msg = msgpack.packb(msg)
        self.tms_socket.send("%s %s" % (cmd, msg))

        

    def process_msgs(self):
        while True:
            socks = dict(self.poller.poll())

            if self.ul_socket in socks and socks[self.ul_socket] == zmq.POLLIN:
                msg = self.ul_socket.recv()
                topic, cmd, msg = msg.split()
                msg = msgpack.unpackb(msg)
                self.log.debug("Controller received cmd : {} on topic {}".format(cmd, topic))
                if topic == "NEW_NODE":
                    node = self.add_new_node(msg)
                    self.install_egress_scheduler(node)
                    self.set_channel(node, self.bnChannel)
                    self.monitor_transmission_parameters(node)
                elif topic == "NODE_EXIT":
                    self.remove_node(msg)
                elif cmd == "HelloMsg":
                    self.serve_hello_msg(msg)
                elif cmd == "monitor_transmission_parameters_response":
                    self.monitor_transmission_parameters_response(msg)
                else:
                    self.log.debug("Operation not supported")

            if self.tms_socket in socks and socks[self.tms_socket] == zmq.POLLIN:
                msg = self.tms_socket.recv()
                cmd, msg = msg.split()
                msg = msgpack.unpackb(msg)
                self.log.debug("Controller received cmd : {} from TMS".format(cmd))

                if cmd == "get_sut_nodes_list":
                    self.get_sut_nodes_list()
                elif cmd == "used_channel_list":
                    self.recv_channel_list(msg)


    def run(self):
        self.log.debug("Controller starts".format())
        try:
            self.process_msgs()

        except KeyboardInterrupt:
            self.log.debug("Controller exits")

        except:
            self.log.debug("Unexpected error:".format(sys.exc_info()[0]))
        finally:
            self.log.debug("Exit")
            self.ul_socket.close()
            self.dl_socket.close()
            #self.close_connection_with_tms()
            self.tms_socket.close()
            self.context.term()
