# CS652-Project2 - Fat Tree Topology w/ Routing Mechanism

## Requirements

* Mininet
* Ryu
* Python 3.6+


## Fat Tree Topology (Mininet)

```topo.py``` uses Mininet Python APIs to generate a Fat Tree network topology. It takes a value of k, which can be configured my modifying the default on the ```__init__``` function for the ```FatTreeTopo``` class.

Based on the value of k, the topology is generated in the following order:

1. Initialize core switches
2. Initialize pods (including aggregation switches, edge switches, and hosts)
3. Link hosts to edge layer
4. Link edge layer to aggregation layer
5. Link aggregation layer to the core

To start the topology:

```shell
cd <PROJECT_DIR>
sudo mn --custom topo.py --topo fattree --controller remote
```

## Switch Controller (Ryu)

```ryu.py``` uses Ryu Python APIs to build a controller to manage our Fat Tree topo. It takes a value of k, which can be configured by modifying the default value of k within the ```FatTreeSwitch``` class. 

The main switch class in this code is designed to intelligently build flows by analyzing the DPIDs of the switches, reading packet information, and calcuating expected flow paths in a balanced manner, such that traffic is evenly distributed across the system. ARP packets are first directed across the toplogy to their destined hosts by the controller, and then responses are relayed back. Once ARP resolution completes between two hosts, the controller directs the first IP packet destined between the two. By calculating the path that should be taken to equally balance the traffic, the controller adds an entry to the flow table for the switch. Once this flow is in place, all future packets will properly flow to the respective hosts along those determined paths.  

To start the controller:

```shell
cd <PROJECT_DIR>
ryu-manager ryu.py
```

## Execution Example

The following screenshot shows an example of a Fat Tree topo being generated using k = 4. 

During the first pingall, the controller distributes ARP packets between each host and then directs the flow of the packets, adding flow table entries as it goes.

During the second pingall, since the flow table entries have already been created, the controller performs no packet_in requests and allows the switches to automatically direct the packets based on the flow table entries. All subsequent packets sent between hosts will follow these flows. 

