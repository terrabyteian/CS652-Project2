#!/usr/bin/env python

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Ryu
from mininet.topo import Topo

class FatTreeTopo(Topo):
    
    def __init__(self,k=4):

            # Initialize topo
            Topo.__init__(self)

            # Initialize core switches
            cores = [self.addSwitch('c%d%d' % (i,j),dpid="%02x:%02x:%02x" % (k,i+1,j+1)) for i in range(int(k/2)) for j in range(int(k/2))]

            # Initialize pods
            pods = [{
                "aggregation": [self.addSwitch('p%da%d' % (p,a),dpid="%02x:%02x:01" % (p,a+int(k/2))) for a in range(int(k/2))], 
                "edge": [self.addSwitch('p%de%d' % (p,e),dpid="%02x:%02x:01" % (p,e)) for e in range(int(k/2))],
                "hosts": [[self.addHost('p%de%dh%d' % (p,e,h),ip="11.%d.%d.%d/24" % (p,e,h+2)) for h in range(int(k/2))] for e in range(int(k/2))]
            } for p in range(k)]

            # Initialize links
            for pod_idx,pod in enumerate(pods):

                # Link hosts to edge
                for host_group_idx,host_group in enumerate(pod['hosts']):
                    for host in host_group:
                        self.addLink(host,pod['edge'][host_group_idx])
                
                # Link edge to aggregation
                for edge in pod['edge']:
                    for agg in pod['aggregation']:
                        self.addLink(edge,agg)

                # Link edge to core
                for agg_idx,agg in enumerate(pod['aggregation']):
                    for i in range(int(k/2)):
                        self.addLink(agg,cores[(agg_idx*int(k/2))+i])

topos = {'fattree': (lambda: FatTreeTopo())}

class FatTreeNet(Mininet):
    def __init__(self,k=4):
        Mininet.__init__(self,topo=FatTreeTopo(k),controller=Ryu)

if __name__ == '__main__':
    net = FatTreeNet()
    net.start()
    net.pingAll()
    CLI(net)
    net.stop()
