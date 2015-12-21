__author__ = "Piotr Gawlowicz"
__copyright__ = "Copyright (c) 2015, Technische Universitat Berlin"
__version__ = "0.1.0"
__email__ = "gawlowicz@tkn.tu-berlin.de"

import sys
import os
import time

def create_new_config(channel=11, outfilePath="../configs/tmp_wpa_supplicant.config"):
    ch_to_f = { 1 : 2412,
                2 : 2417,
                3 : 2422,
                4 : 2427,
                5 : 2432,
                6 : 2437,
                7 : 2442,
                8 : 2447,
                9 : 2452,
                10 : 2457,
                11 : 2462,
                12 : 2467,
                13 : 2472,
                14 : 2484,
                34 : 5170,
                36 : 5180,
                38 : 5190,
                40 : 5200,
                42 : 5210,
                44 : 5220,
                46 : 5230,
                48 : 5240,
                52 : 5260,
                56 : 5280,
                60 : 5300,
                64 : 5320,
                100 : 5500,
                104 : 5520,
                108 : 5540,
                112 : 5560,
                116 : 5580,
                120 : 5600,
                124 : 5620,
                128 : 5640,
                132 : 5660,
                136 : 5680,
                140 : 5700,
                149 : 5745,
                153 : 5765,
                157 : 5785,
                161 : 5805,
                165 : 5825,
                184 : 5920,
                188 : 5940,
                192 : 5960,
                196 : 5980,
                200 : 6000,
                204 : 6020,
                208 : 6040,
                212 : 6060,
                216 : 6080
    }
    with open('../configs/bn_wpa_supplicant.conf', 'r') as input_file, open(outfilePath, 'w') as output_file:
        for line in input_file:
            if "ssid=" in line: 
                output_file.write('    ssid="PortableTestbed-{}"\n'.format(channel))
            elif "psk=" in line: 
                output_file.write('    psk="12345678{}"\n'.format(ch_to_f[channel]))
            elif "frequency=" in line: 
                output_file.write('    frequency={}\n'.format(ch_to_f[channel]))
            else:
                output_file.write(line)

def start_ibss(bn_dev, channel=11):
    tmp_config = "./tmp_wpa_supplicant.config"
    create_new_config(channel=channel, outfilePath=tmp_config)

    cmd = "killall wpa_supplicant > /dev/null 2>&1".format()
    os.system(cmd)

    time.sleep(0.2)
    cmd = "wpa_supplicant -Dnl80211 -i {} -c {} -B > /dev/null 2>&1".format(bn_dev,tmp_config)
    os.system(cmd)

def stop_ibss(bn_dev):
    cmd = "ifconfig {} 0.0.0.0 up".format(bn_dev)
    os.system(cmd)
    cmd = "killall wpa_supplicant > /dev/null 2>&1".format()
    os.system(cmd)

def create_vxlan(bn_dev, dut_dev):
    vxlan_dev = "vxlan10"
    vxlan_id = 10
    vxlan_group = "224.10.10.10"
    vxlan_ttl = 10

    #print "Delete old"
    cmd = "ip link set br-vx down > /dev/null 2>&1".format()
    os.system(cmd)
    cmd = "brctl delbr br-vx > /dev/null 2>&1".format()
    os.system(cmd)

    #print "Create new"
    cmd = "brctl addbr br-vx; ip link set br-vx up".format()
    os.system(cmd)
    #print "Configure VXLAN"
    cmd = "ip link add {} type vxlan id {} group {} ttl {} dev {}".format(vxlan_dev,vxlan_id,vxlan_group,vxlan_ttl,bn_dev)
    os.system(cmd)
    cmd = "ip link set {} up".format(vxlan_dev)
    os.system(cmd)
    cmd = "brctl addif br-vx {}".format(vxlan_dev)
    os.system(cmd)
    #print "Configure eth0"
    cmd = "ip link set {} up".format(dut_dev)
    os.system(cmd)
    cmd = "ifconfig {} mtu 1500".format(dut_dev)
    os.system(cmd)
    cmd = "brctl addif br-vx {}".format(dut_dev)
    os.system(cmd)
    cmd = "ifconfig {} mtu 1550".format(bn_dev)
    os.system(cmd)
    time.sleep(0.5)
    cmd = "ifconfig {} mtu 1500".format(vxlan_dev)
    os.system(cmd)

def delete_vxlan(bn_dev, dut_dev):
    vxlan_dev = "vxlan10"
    vxlan_id = 10
    vxlan_group = "224.10.10.10"
    vxlan_ttl = 10

    #print "Delete"
    cmd = "ip link set {} down".format(vxlan_dev)
    os.system(cmd)
    cmd = "ip link set {} down".format(dut_dev)
    os.system(cmd)
    cmd = "brctl delif br-vx {} > /dev/null 2>&1".format(dut_dev)
    os.system(cmd)
    cmd = "brctl delif br-vx {} > /dev/null 2>&1".format(vxlan_dev)
    os.system(cmd)
    cmd = "ip link del {}".format(vxlan_dev)
    os.system(cmd)
    cmd = "ip link set br-vx down > /dev/null 2>&1".format()
    os.system(cmd)
    cmd = "brctl delbr br-vx > /dev/null 2>&1".format()
    os.system(cmd)
    cmd = "ifconfig {} mtu 1500".format(bn_dev)
    os.system(cmd)

def ifconfig(dev, ip, mask):
    time.sleep(0.2)
    cmd = "ifconfig {} {} netmask {} up".format(dev, ip, mask)
    os.system(cmd)

def start_olsrd(bn_dev, config="../configs/olsrd.conf"):
    cmd = "killall olsrd > /dev/null 2>&1".format()
    os.system(cmd)

    cmd = "olsrd -i {} -f {} > /dev/null 2>&1".format(bn_dev, config)
    os.system(cmd)

def stop_olsrd():
    cmd = "killall olsrd > /dev/null 2>&1".format()
    os.system(cmd)

def stop_network_manager():
    cmd = "service network-manager stop > /dev/null 2>&1".format()
    os.system(cmd) 

def start_network_manager():
    cmd = "service network-manager start > /dev/null 2>&1".format()
    os.system(cmd)

def load_bridge_nf():
    cmd = "modprobe br_netfilter > /dev/null 2>&1".format()
    os.system(cmd)
    cmd = "sysctl -w net.bridge.bridge-nf-call-iptables=1 > /dev/null 2>&1".format()
    os.system(cmd)
