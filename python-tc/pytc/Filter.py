__author__ = 'P.Gawlowicz'

class FlowDesc(object):
    def __init__(self, src=None, srcPort=None, dst=None, dstPort=None, prot=None, name=None):
        self.mSrcAddress = src
        self.mDstAddress = dst
        self.mSrcPort = srcPort
        self.mDstPort = dstPort
        self.mProt = prot
        self.mName = name


class Filter(object):
    #AC to TOS mapping
    BE = 20
    BK = 40
    VO = 160
    VI = 200

    def __init__(self, name):
        self.name = name
        self.isInstalled = False

        #for traffic control
        self.tcProtocol = 'ip'
        self.parent = None
        self.prio = 1
        self.target = None

        self.srcAddress = None
        self.dstAddress = None
        self.protocol = None
        self.srcPort = None
        self.dstPort = None

        self.mark = None
        self.tos = self.BE

    def get_desc(self):
        desc = { "name" : self.name,
                 "config" : self.get_config(),
               }
        return desc


    def get_config(self):
        config = {"parent" : self.get_parent(),
                  "target" : self.target.mParent.getHexStr(),
                  "priority": self.prio,
                  "flow_desc" : { "srcAddress" : self.srcAddress,
                                  "srcPort" : self.srcPort,
                                  "proto" : self.protocol,
                                  "dstAddress" : self.dstAddress,
                                  "dstPort" : self.dstPort,
                                },
                  "mark" : self.mark,
                  "tos" : self.tos
                  }
        return config


    def setParent(self, parent):
        self.parent = parent
        return


    def get_parent(self):
        if not self.parent:
            return None
        return self.parent.getHexStr()


    def setFilterPriority(self, priority):
        self.prio = priority
        return


    def setFiveTuple(self, src=None, srcPort=None, dst=None, dstPort=None, prot=None):
        self.srcAddress = src
        self.dstAddress = dst
        self.srcPort = srcPort
        self.dstPort = dstPort
        self.protocol = prot


    def setFlowId(self, flowid):
        self.mark = flowid
        return


    def setTos(self, tos):
        if isinstance(tos, basestring):
            if tos == 'VI':
                self.tos = self.VI
            elif tos == 'VO':
                self.tos = self.VO
            elif tos == 'BE':
                self.tos = self.BE
            else:
                self.tos = self.BK
        else:
            self.tos = tos
        return


    def setTarget(self, target):
        self.target = target
        return