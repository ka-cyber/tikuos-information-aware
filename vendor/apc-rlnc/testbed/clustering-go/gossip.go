package main

import (
	"encoding/json"
	"log"
	"net"
	"sync"
	"time"
)

const gossipPort = 47632 // arbitrary fixed UDP port for peer broadcasts

// GossipTransport broadcasts this node's PeerState over UDP on the given
// interface's broadcast address and listens for peers' broadcasts,
// implementing Section 5.1's "Neighbor exchange: peers broadcast s_i(t)
// (2 bytes) periodically" and Algorithm 1 step 3's "each node broadcasts
// (s_i, clusterID_i)".
type GossipTransport struct {
	iface     *net.Interface
	broadcast net.IP
	conn      *net.UDPConn

	mu    sync.RWMutex
	peers map[string]PeerState // nodeID -> last known state
	seen  map[string]time.Time // nodeID -> last-seen timestamp (for liveness)
}

func NewGossipTransport(ifaceName string) (*GossipTransport, error) {
	iface, err := net.InterfaceByName(ifaceName)
	if err != nil {
		return nil, err
	}
	bcast, err := broadcastAddrForInterface(iface)
	if err != nil {
		return nil, err
	}

	conn, err := net.ListenUDP("udp4", &net.UDPAddr{Port: gossipPort})
	if err != nil {
		return nil, err
	}

	return &GossipTransport{
		iface:     iface,
		broadcast: bcast,
		conn:      conn,
		peers:     make(map[string]PeerState),
		seen:      make(map[string]time.Time),
	}, nil
}

func broadcastAddrForInterface(iface *net.Interface) (net.IP, error) {
	addrs, err := iface.Addrs()
	if err != nil {
		return nil, err
	}
	for _, a := range addrs {
		ipNet, ok := a.(*net.IPNet)
		if !ok || ipNet.IP.To4() == nil {
			continue
		}
		ip := ipNet.IP.To4()
		mask := ipNet.Mask
		bcast := make(net.IP, 4)
		for i := 0; i < 4; i++ {
			bcast[i] = ip[i] | ^mask[i]
		}
		return bcast, nil
	}
	// Fall back to the limited broadcast address if the interface has no
	// IPv4 addr configured yet (common in netem/emulation setups).
	return net.IPv4bcast, nil
}

// Broadcast sends this node's current state to the subnet broadcast address.
func (g *GossipTransport) Broadcast(state PeerState) error {
	payload, err := json.Marshal(state)
	if err != nil {
		return err
	}
	dst := &net.UDPAddr{IP: g.broadcast, Port: gossipPort}
	_, err = g.conn.WriteToUDP(payload, dst)
	return err
}

// Listen runs forever (intended to run in its own goroutine), ingesting
// peer broadcasts into the local peer table.
func (g *GossipTransport) Listen() {
	buf := make([]byte, 2048)
	for {
		n, _, err := g.conn.ReadFromUDP(buf)
		if err != nil {
			log.Printf("gossip: read error: %v", err)
			continue
		}
		var ps PeerState
		if err := json.Unmarshal(buf[:n], &ps); err != nil {
			continue // ignore malformed/foreign packets
		}
		g.mu.Lock()
		g.peers[ps.NodeID] = ps
		g.seen[ps.NodeID] = time.Now()
		g.mu.Unlock()
	}
}

// Snapshot returns a copy of all currently known peer states (self excluded
// by the caller), used to build the score map fed into KMeans1D.
func (g *GossipTransport) Snapshot() map[string]PeerState {
	g.mu.RLock()
	defer g.mu.RUnlock()
	out := make(map[string]PeerState, len(g.peers))
	for k, v := range g.peers {
		out[k] = v
	}
	return out
}

// PrunePeers evicts peers not heard from within staleAfter (handles churn:
// Section 3.1's departing nodes).
func (g *GossipTransport) PrunePeers(staleAfter time.Duration) []string {
	g.mu.Lock()
	defer g.mu.Unlock()
	var dropped []string
	now := time.Now()
	for id, t := range g.seen {
		if now.Sub(t) > staleAfter {
			delete(g.peers, id)
			delete(g.seen, id)
			dropped = append(dropped, id)
		}
	}
	return dropped
}

func (g *GossipTransport) Close() error {
	return g.conn.Close()
}
