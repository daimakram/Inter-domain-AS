import sys
from collections import defaultdict
from router import Router
from packet import Packet
from json import dumps, loads
from dijkstar import Graph, find_path


class LSrouter(Router):
    """Link state routing protocol implementation."""

    def __init__(self, addr, heartbeatTime):
        Router.__init__(self, addr) # initialize superclass - don't remove
        self.heartbeatTime = heartbeatTime
        self.last_time = 0
        self.graph = Graph(undirected=True)
        self.global_seq = {}  #to store sequence numbers of all nodes
        self.neighbours = {}  #dict with nodes as key and [cost,port] as value
        self.seq_no = 0       #seq no
        self.address = addr                                         
        self.linked_state = [self.address,self.neighbours,self.seq_no]  #local link state
        self.global_view = {} #dict to store all link states (global view)
        self.fT = {} #forwarding table


    def handlePacket(self, port, packet):
        """TODO: process incoming packet"""
        
        if packet.isTraceroute():
            send_add = self.pathFinder(packet.dstAddr) #finds appropirate nextHop 
            if send_add != 0: #if path found
                try:
                    final_add = self.neighbours[send_add][1] #finding port
                    self.send(final_add, packet)
                except:
                    return
            else:
                return
        else:
            data = loads(packet.content) #loading packet in data
            src = packet.srcAddr
            addr = packet.dstAddr
            seq = data[2]
            node_neighbour = data[1]
            node_id = data[0]
            if node_id in self.global_seq.keys() and seq <= self.global_seq[node_id]: #stale link state
                return
            else:
                self.global_seq[node_id] = seq #adding seq no

            if node_id in self.graph.keys(): #if node is in global graph view

                self.updateFt() #update forwarding table
                self.updateGraph( node_id, node_neighbour)  #update graph
                self.forwardReceivedLS( packet, node_id) #broadcast link state to neighbours



    def handleNewLink(self, port, endpoint, cost):

        self.graph.add_edge( self.addr, endpoint, cost) #add edge
        self.neighbours[endpoint] = [ cost, port]   #add item in neighbour dict
        self.global_view[port] = self.neighbours  #update global view
        self.seq_no = self.seq_no + 1 
        self.updateFt() #update forwarding tabel
        self.broadcastLS() #broadcast LS
        


    def handleRemoveLink(self, port):
        add = self.addFinder(port) #finding appropirate port
        self.neighbours.pop(add) #removing from dict
        self.graph.remove_edge( self.addr, add) #updating graph
        self.seq_no = self.seq_no + 1 
        self.updateFt() #update forwarding tabel
        self.broadcastLS() #broadcast LS

    def handleTime(self, timeMillisecs):
        if timeMillisecs - self.last_time >= self.heartbeatTime:
            self.seq_no = self.seq_no + 1
            self.broadcastLS() #broadcast LS
            self.last_time = timeMillisecs


    def debugString(self):
        """TODO: generate a string for debugging in network visualizer"""
        return ""
    
    #.............. Helper Functions..............

    #finds appropriate port from node_address in neighbour dict
    def addFinder(self, port):
        for i in self.neighbours.keys():
            if self.neighbours[i][1] == port:
                return i

    #runs dijkstar alogrithm to find path
    def pathFinder(self,i):
        try:
            path = find_path(self.graph,self.address,i)
            return path.nodes[1]
        except:
            return 0
    
    #update forwarding table
    def updateFt(self):
        for j in self.global_view.keys():
            for i in self.global_view[j].keys():
                try:
                    path = find_path( self.graph, self.address, i[1]) #runs dijkstar alogrithm to find path
                    node = path.nodes[1]
                    cost = path.total_cost
                    if i[1] not in self.fT.keys:
                        self.fT[i] = [ node, cost]   #update fT
                    else:
                        if cost < self.fT[i][1]:   # if efficient path
                            self.fT[i] = [ node, cost] #update fT
                except:
                    continue
    
    #broadcast Local link state to neighbours
    def broadcastLS(self):
        for i in self.neighbours.keys():
            self.linked_state[2] = self.seq_no
            pac = Packet( Packet.ROUTING, self.address, self.neighbours[i])
            pac.content = dumps(self.linked_state)
            self.send(self.neighbours[i][1], pac)
    
    #forward link state recieved, to other neighbours (except sender) / packet flooding
    def forwardReceivedLS(self,pac,sender_add):
        for i in self.neighbours.keys():
            if i != sender_add:
                self.send(self.neighbours[i][1], pac)

    #updates Graph
    def updateGraph(self,node_id,node_neighbour):
        if len(list(node_neighbour)) < len(list(self.graph[node_id])):  # catters link chnages 
            for node in self.graph[node_id]:
                if node in node_neighbour:   # no change in link 
                    continue
                else:     #link down
                    self.graph.remove_edge(node_id, node) #remove edge
                    break       
        else:    #new link added                             
            for key in node_neighbour.keys():
                self.graph.add_edge(node_id, key, node_neighbour[key][0]) #add edge
            


