import logging
import time
import datetime
import sys
import zmq.green as zmq
import uuid
import msgpack
import gevent
from gevent import Greenlet
from gevent.event import AsyncResult

__author__ = "Piotr Gawlowicz"
__copyright__ = "Copyright (c) 2015, Technische Universität Berlin"
__version__ = "0.1.0"
__email__ = "gawlowicz@tkn.tu-berlin.de"

class Interface(Greenlet):
    def __init__(self, bnc):
        Greenlet.__init__(self)
        self.log = logging.getLogger("{module}.{name}".format(
            module=self.__class__.__module__, name=self.__class__.__name__))

        self.myUuid = uuid.uuid4()
        self.myUuidStr = str(self.myUuid)

        self.sutLostCallback = None

        self.loopGevent = None
        self.bnc = bnc
        self.connected = False

        self.context = zmq.Context()
        self.poller = zmq.Poller()
        self.socket = self.context.socket(zmq.PAIR)
        self.poller.register(self.socket, zmq.POLLIN)
        self.socket.connect(bnc)
        self.connected = True

        self.asyncResults = {}

    def register_sut_lost_callback(self, callback):
        self.sutLostCallback = callback

    def stop(self):
        self.log.debug("Exit")
        self.running = False
        self.socket.close()
        self.context.term()

    def _run(self):
        self.running = True

        while self.running:
            self.process_msgs()

    def get_sut_list(self):
        if self.connected:
            self.asyncResults["sut_node_list"] = AsyncResult()

            cmd = "get_sut_nodes_list"
            msg = ["all_available"]
            msg = msgpack.packb(msg)
            self.socket.send("%s %s" % (cmd, msg))

            sut_list = self.asyncResults["sut_node_list"].get()
            del self.asyncResults["sut_node_list"]

            return sut_list

    def recv_sut_list(self, msg):
        if "sut_node_list" in self.asyncResults:
            self.asyncResults["sut_node_list"].set(msg)

    def reserve_sut_node(self, sut_list):
        return sut_list

    def reboot_sut_node(self, sut_mac):
        if self.connected:
            sut_list = []

            if hasattr(sut_mac, '__iter__'):
                sut_list.extend(sut_mac)
            else:
                sut_list.append(sut_mac)

            cmd = "reboot_sut"
            msg = sut_list
            msg = msgpack.packb(msg)
            self.socket.send("%s %s" % (cmd, msg))


    def start_experiment(self):
        pass

    def stop_experiment(self):
        pass

    def send_used_channel_list(self, sut_list, channel_list):
        if self.connected:
            self.asyncResults["bn_channel"] = AsyncResult()

            cmd = "used_channel_list"
            msg = channel_list
            msg = msgpack.packb(msg)
            self.socket.send("%s %s" % (cmd, msg))

            bn_channel = self.asyncResults["bn_channel"].get()
            del self.asyncResults["bn_channel"]

            return bn_channel

    def recv_bn_channel(self, msg):
        if "bn_channel" in self.asyncResults:
            self.asyncResults["bn_channel"].set(msg)

    def sent_qdisc_config(self, nodelist, qdisc_config):
        if self.connected:
            cmd = "qdisc_config"
            msg = qdisc_config
            msg = msgpack.packb(msg)
            self.socket.send("%s %s" % (cmd, msg))

    def process_msgs(self):
            socks = dict(self.poller.poll())

            if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                msg = self.socket.recv()
                cmd, msg = msg.split()
                msg = msgpack.unpackb(msg)
                self.log.debug("Interface received cmd : {} on topic:".format(cmd))

                if cmd == "EXIT":
                    self.connected = False
                elif cmd == "sut_node_list_response":
                    self.recv_sut_list(msg)
                elif cmd == "bn_channel_response":
                    self.recv_bn_channel(msg)
                else:
                    self.log.debug("Operation not supported")


    def test_run(self):
        self.log.debug("Controller starts".format())
        try:
            self.process_msgs()
        except KeyboardInterrupt:
            self.log.debug("Controller exits")
        except:
             self.log.debug("Unexpected error:".format(sys.exc_info()[0]))
        finally:
            self.log.debug("Exit")
            self.socket.close()
            self.context.term()
