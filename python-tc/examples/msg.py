#!/usr/bin/python

__author__ = 'P.Gawlowicz'

from pytc.Qdisc import *
from pytc.Filter import *
import logging
import time, sys
import msgpack

"""
EU project WISHFUL
"""

if __name__ == '__main__':

    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT)
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    log.warning('Test Traffic Control')

    qdiscConfig = QdiscConfig()
    qdiscConfig.set_interface("wlan0")

    prioSched = PrioScheduler(bandNum=6)
    qdiscConfig.set_root_qdisc(prioSched)

    pfifo0 = prioSched.addQueue(PfifoQueue(limit=100))
    pfifo1 = prioSched.addQueue(PfifoQueue(limit=100))
    pfifo2 = prioSched.addQueue(PfifoQueue(limit=100))
    pfifo3 = prioSched.addQueue(PfifoQueue(limit=100))
    pfifo4 = prioSched.addQueue(PfifoQueue(limit=100))
    pfifo5 = prioSched.addQueue(PfifoQueue(limit=100))

    qdiscConfig.add_queue(pfifo0)
    qdiscConfig.add_queue(pfifo1)
    qdiscConfig.add_queue(pfifo2)
    qdiscConfig.add_queue(pfifo3)
    qdiscConfig.add_queue(pfifo4)
    qdiscConfig.add_queue(pfifo5)

    filter0 = Filter(name="Mesh_Control_Traffic")
    filter0.setFiveTuple(src=None, prot='udp', srcPort='698', dstPort='698')
    filter0.setTarget(pfifo0)
    filter0.setTos(Filter.VO)
    prioSched.addFilter(filter0)

    filter1 = Filter(name="Testbed_Management_Traffic")
    filter1.setFiveTuple(src='10.0.0.1', dst=None, prot='tcp', srcPort=None, dstPort='1234')
    filter1.setTarget(pfifo1)
    filter1.setTos(Filter.VI)
    prioSched.addFilter(filter1)

    filter2 = Filter(name="BN_Wireless_Control_Traffic")
    filter2.setFiveTuple(src='192.168.0.1', dst=None, prot='tcp', srcPort=None, dstPort='9980')
    filter2.setTarget(pfifo2)
    filter2.setTos(Filter.VI)
    prioSched.addFilter(filter2)

    filter3 = Filter(name="SUT_Control_Traffic")
    filter3.setFiveTuple(src='192.168.1.1', dst=None, prot='tcp', srcPort=None, dstPort=None)
    filter3.setTarget(pfifo3)
    filter3.setTos(Filter.BE)
    prioSched.addFilter(filter3)

    filter4 = Filter(name="SUT_Experiment_Control_Traffic")
    filter4.setFiveTuple(src='192.168.2.1', dst=None, prot='tcp', srcPort=None, dstPort="1111")
    filter4.setTarget(pfifo3)
    filter4.setTos(Filter.BE)
    prioSched.addFilter(filter4)

    filter5 = Filter(name="SUT_Experiment_Data_Traffic")
    filter5.setFiveTuple(src='192.168.2.1', dst=None, prot='tcp', srcPort=None, dstPort="1122")
    filter5.setTarget(pfifo4)
    filter5.setTos(Filter.BE)
    prioSched.addFilter(filter5)

    filter6 = Filter(name="SUT_Experiment_Monitoring_Traffic")
    filter6.setFiveTuple(src=None, dst='192.168.2.1', prot='tcp', srcPort=None, dstPort='2222')
    filter6.setTarget(pfifo4)
    filter6.setTos(Filter.BE)
    prioSched.addFilter(filter6)

    filter7 = Filter(name="Background_Monitoring_Traffic")
    filter7.setFiveTuple(src=None, dst=None, prot='tcp', srcPort='3333', dstPort='4444')
    filter7.setTarget(pfifo5)
    filter7.setTos(Filter.BK)
    prioSched.addFilter(filter7)

    qdiscConfig.add_filter(filter0)
    qdiscConfig.add_filter(filter1)
    qdiscConfig.add_filter(filter2)
    qdiscConfig.add_filter(filter3)
    qdiscConfig.add_filter(filter4)
    qdiscConfig.add_filter(filter5)
    qdiscConfig.add_filter(filter6)
    qdiscConfig.add_filter(filter7)

    msg = msgpack.packb(qdiscConfig.serialize())

    print msgpack.unpackb(msg)
