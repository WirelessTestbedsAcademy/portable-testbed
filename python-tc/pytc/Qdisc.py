__author__ = 'P.Gawlowicz'

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class MajorHandleGenerator(object):
    __metaclass__ = Singleton
    def __init__(self):
        self.value = 1

    def GenerateValue(self):
        curVal = self.value
        self.value += 1
        return curVal

class MinorHandleGenerator(object):
    def __init__(self):
        self.value = 1

    def GenerateValue(self):
        curVal = self.value
        self.value += 1
        return curVal


class Handle(object):
    def __init__(self, major, minor):
        self.mMajor = major
        self.mMinor = minor
        pass

    def __str__(self):
        return ("%d:%d" % (self.mMajor, self.mMinor))

    def __repr__(self):
        return self.__str__()

    def getStr(self):
        return ("%d:%d" % (self.mMajor, self.mMinor))

    def getHexStr(self):
        return ("%s:%s" % (hex(self.mMajor).split('x')[1], hex(self.mMinor).split('x')[1]))

    def getHex(self):
        return int(hex((self.mMajor<<16) + self.mMinor), 0)


class QdiscConfig(object):
    def __init__(self):
        self.interface = None
        self.root = None
        self.queues = []
        self.filters = []

    def set_interface(self, ifname):
        self.interface = ifname

    def set_root_qdisc(self, root):
        self.root = root

    def add_queue(self, queue):
        self.queues.append(queue)

    def add_filter(self, tcfilter):
        self.filters.append(tcfilter)

    def serialize(self):
        data=  { "interface":self.interface,
                 "root": self.root.get_desc(),
                 "queues" : [],
                 "filters" : [],
                 }

        for q in self.queues:
            data["queues"].append( q.get_desc() )

        for f in self.filters:
            data["filters"].append( f.get_desc() )

        return data


class TcClass(object):
    def __init__(self, handle=None, parent=None, installed=False):
        self.mHandle = handle
        self.mParent = parent
        self.mInstalled = installed
        self.leaf = None
        self.mInterface = None
        pass


class Qdisc(object):
    def __init__(self):
        self.mMinorHandleGen = MinorHandleGenerator()
        majorHandleGen = MajorHandleGenerator()
        self.mHandle = Handle(majorHandleGen.GenerateValue(),0)
        self.mParent = None

    def setParent(self, parent):
        self.mParent = parent

    def get_type(self):
        pass

    def get_parent(self):
        if not self.mParent:
            return None

        return self.mParent.getHexStr()

    def get_handle(self):
        return self.mHandle.getHexStr()

    def get_params(self):
        pass

    def get_desc(self):
        desc = { "type" : self.get_type(),
                 "handle" : self.get_handle(),
                 "parent":self.get_parent(),
                 "params" : self.get_params()
                 }
        return desc

class ClasslessQdisc(Qdisc):
    def __init__(self):
        super(ClasslessQdisc,self).__init__()
        pass


class ClassfulQdisc(Qdisc):
    def __init__(self):
        super(ClassfulQdisc,self).__init__()
        self.classes = []
        self.queues = []
        self.filters = []
        pass

    def addClass(self, installed=False):
        classMinorVal = self.mMinorHandleGen.GenerateValue()
        classHandle = Handle(self.mHandle.mMajor, classMinorVal)
        parentHandle = Handle(self.mHandle.mMajor, 0)
        newClass = TcClass(classHandle, parentHandle, installed)
        self.classes.append(newClass)
        return newClass

    def addQueue(self, queue):
        found=False
        for c in self.classes:
            if not c.leaf:
                found=True
                break
    
        parentHandle = c.mHandle
        queue.setParent(parentHandle)
        c.leaf = queue
        self.queues.append(queue)
        return queue

    def addFilter(self, tcfilter):
        tcfilter.setParent(self.mHandle)
        self.filters.append(tcfilter)
        pass


class PfifoQueue(ClasslessQdisc):
    def __init__(self, limit=100):
        super(PfifoQueue,self).__init__()
        self.limit = limit

    def get_type(self):
        return "pfifo"

    def get_params(self):
        data = [{"key":"limit", "value": self.limit}]
        return data


class BfifoQueue(ClasslessQdisc):
    def __init__(self, limit=10240):
        super(BfifoQueue,self).__init__()
        self.limit = limit

    def get_type(self):
        return "bfifo"

    def get_params(self):
        data = [{"key":"limit", "value": self.limit}]
        return data


class PfifoFastQueue(ClasslessQdisc):
    def __init__(self, limit=100):
        super(PfifoFastQueue,self).__init__()
        self.limit = limit

    def get_type(self):
        return "pfifo_fast"

    def get_params(self):
        data = [{"key":"limit", "value": self.limit}]
        return data


class TbfQueue(ClasslessQdisc):
    def __init__(self, rate=2**22-1, burst=10*1024, limit=10000):
        super(TbfQueue,self).__init__()
        self.rate = rate
        self.burst = burst
        self.limit = limit

    def get_type(self):
        return "tbf"

    def get_params(self):
        data = [{"key":"rate", "value": self.rate},
                {"key":"burst", "value": self.burst},
                {"key":"limit", "value": self.limit}
                ]
        return data


class SfqQueue(ClasslessQdisc):
    def __init__(self, limit=127, quantum=1514, depth=127, divisor=1024, perturb=10):
        super(SfqQueue,self).__init__()
        self.perturb = perturb
        self.limit=limit,
        self.quantum=quantum,
        self.depth=depth,
        self.divisor=divisor,

    def get_type(self):
        return "sfq"

    def get_params(self):
        data = [{"key":"perturb", "value": self.perturb},
                {"key":"limit", "value": self.limit},
                {"key":"quantum", "value": self.quantum},
                {"key":"depth", "value": self.depth},
                {"key":"divisor", "value": self.divisor}
                ]
        return data


class PrioScheduler(ClassfulQdisc):
    def __init__(self, bandNum):
        super(PrioScheduler,self).__init__()
        self.bandNum = bandNum
        for i in range(0, self.bandNum):
            self.addClass(installed=True)

    def get_type(self):
        return "prio"

    def get_params(self):
        data = [{"key":"bands", "value": self.bandNum}]
        return data
