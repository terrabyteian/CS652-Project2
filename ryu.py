from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ipv6
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types


class FatTreeSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    k = 4

    def __init__(self, *args, **kwargs):
        super(FatTreeSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

    def add_flow(self, datapath, in_port, actions, dst,src,ipv4_dst=None,ipv4_src=None):
        ofproto = datapath.ofproto

        match = datapath.ofproto_parser.OFPMatch(
            nw_dst=ipv4_dst, nw_src=ipv4_src,
            in_port=in_port,
            dl_dst=haddr_to_bin(dst), dl_src=haddr_to_bin(src))

        mod = datapath.ofproto_parser.OFPFlowMod(
            datapath=datapath, match=match, cookie=0,
            command=ofproto.OFPFC_ADD, idle_timeout=0, hard_timeout=0,
            priority=ofproto.OFP_DEFAULT_PRIORITY,
            flags=ofproto.OFPFF_SEND_FLOW_REM, actions=actions)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        ip6_pkt = pkt.get_protocol(ipv6.ipv6)
        arp_pkt = pkt.get_protocol(arp.arp)

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})
      
        # ignore lddp or ipv6 packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP or ip6_pkt is not None:
            return
        
        # DPIDs are in the form ..:00:x:y:z
        x = (dpid >> 16) & 15
        y = (dpid >> 8) & 15
        z = dpid & 15

        # collect dest ip octets
        if ip_pkt is not None:
            octets = [int(o) for o in ip_pkt.dst.split('.')]
        elif arp_pkt is not None:
            octets = [int(o) for o in arp_pkt.dst_ip.split('.')]
       
        #if dst in self.mac_to_port[dpid]:
        if (ip_pkt is not None or arp_pkt is not None) and x == octets[1] and y == octets[2]:
             out_port = octets[-1] - 1
        
        # if dest IP is not on this switch
        elif ip_pkt is not None or arp_pkt is not None:

            # if this is a core switch
            if x == self.k:
                out_port = octets[1] + 1

            # if IP is in this pod and this is an aggregation switch
            elif octets[1] == x and y >= int(self.k/2):
                out_port = octets[2] + 1

            # if dest IP is on a differnet switch
            else:
                # derive i from last octet of dest IP
                i = octets[-1]

                # calculate out_port using i,y,k
                # this is the key to evenly distributing traffic load
                out_port = int((i-2+y)%(self.k/2) + (self.k/2)) + 1
        else:
            out_port = ofproto.OFPP_FLOOD
            print("The flood have breached",x,y,z,dst)
        
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = msg.in_port

        # install a flow to avoid packet_in next time
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            if ip_pkt is not None:
                self.add_flow(datapath, msg.in_port, actions, dst,src,ip_pkt.dst,ip_pkt.src)

        # send packet out
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def _port_status_handler(self, ev):
        msg = ev.msg
        reason = msg.reason
        port_no = msg.desc.port_no

        ofproto = msg.datapath.ofproto
        if reason == ofproto.OFPPR_ADD:
            self.logger.info("port added %s", port_no)
        elif reason == ofproto.OFPPR_DELETE:
            self.logger.info("port deleted %s", port_no)
        elif reason == ofproto.OFPPR_MODIFY:
            self.logger.info("port modified %s", port_no)
        else:
            self.logger.info("Illeagal port state %s %s", port_no, reason)
