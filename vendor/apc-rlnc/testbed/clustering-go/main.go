// apc-cluster-daemon: distributed adaptive clustering daemon (Section 5.2,
// Algorithm 1). Each instance runs on one physical/edge node, tracks its
// own EWMA reliability score, gossips it to peers over UDP broadcast on the
// given wireless interface, and locally recomputes a 1-D k-means clustering
// of the whole known peer set every --epoch-duration.
//
// Usage (matches README):
//
//	go build -o apc-cluster-daemon .
//	./apc-cluster-daemon --interface=wlan0 --epoch-duration=1.5s
package main

import (
	"flag"
	"fmt"
	"log"
	"math/rand"
	"os"
	"strconv"
	"time"
)

func main() {
	ifaceName := flag.String("interface", "wlan0", "wireless interface to gossip on")
	epochDuration := flag.Duration("epoch-duration", 1500*time.Millisecond,
		"reconfiguration period tau (Section 3.5)")
	alpha := flag.Float64("alpha", 0.2, "EWMA smoothing factor (Eq. 2)")
	lambda := flag.Float64("lambda", 0.01, "clustering loss regularizer (Eq. 3)")
	rMax := flag.Int("gossip-rounds", 5, "gossip rounds per epoch (Algorithm 1)")
	nodeID := flag.String("node-id", "", "override this node's ID (default: hostname:pid)")
	staleAfter := flag.Duration("stale-after", 10*time.Second, "peer eviction timeout (churn)")
	flag.Parse()

	if *nodeID == "" {
		host, _ := os.Hostname()
		*nodeID = host + ":" + strconv.Itoa(os.Getpid())
	}

	tracker := NewReliabilityTracker(*alpha)
	tracker.Update(*nodeID, 0.9) // optimistic prior for self

	transport, err := NewGossipTransport(*ifaceName)
	if err != nil {
		log.Fatalf("failed to bind gossip transport on %s: %v", *ifaceName, err)
	}
	defer transport.Close()

	go transport.Listen()

	log.Printf("apc-cluster-daemon started: node=%s iface=%s epoch=%s",
		*nodeID, *ifaceName, epochDuration.String())

	clusterID := 0
	ticker := time.NewTicker(200 * time.Millisecond) // gossip broadcast cadence
	epochTicker := time.NewTicker(*epochDuration)
	defer ticker.Stop()
	defer epochTicker.Stop()

	for {
		select {
		case <-ticker.C:
			// Section 5.1: "Link ACKs" would normally drive successRate;
			// here we synthesize a placeholder success sample so the daemon
			// is runnable standalone. Wire this to real MAC-layer ACK
			// counters in a production deployment.
			successRate := syntheticLinkSuccessSample()
			s := tracker.Update(*nodeID, successRate)

			if err := transport.Broadcast(PeerState{
				NodeID: *nodeID, Score: s, ClusterID: clusterID,
				Epoch: time.Now().Unix(),
			}); err != nil {
				log.Printf("broadcast error: %v", err)
			}

		case <-epochTicker.C:
			dropped := transport.PrunePeers(*staleAfter)
			for _, d := range dropped {
				tracker.Drop(d)
				log.Printf("peer %s pruned (churn)", d)
			}

			scores := map[string]float64{*nodeID: tracker.Update(*nodeID, syntheticLinkSuccessSample())}
			for id, ps := range transport.Snapshot() {
				scores[id] = ps.Score
			}

			k := InitialK(len(scores))
			seedFn := func(i int) float64 {
				return 0.5 + 0.5*rand.Float64() // uniform init over [0.5,1.0] score range
			}
			assignment := KMeans1D(scores, k, *rMax, seedFn)
			if c, ok := assignment[*nodeID]; ok {
				clusterID = c
			}

			clustersByID := make(map[int][]float64)
			for id, c := range assignment {
				clustersByID[c] = append(clustersByID[c], scores[id])
			}
			loss := ClusteringLoss(clustersByID, *lambda)

			fmt.Printf("[epoch %s] k=%d self_cluster=%d loss=%.4f peers=%d\n",
				time.Now().Format(time.RFC3339), k, clusterID, loss, len(scores)-1)
		}
	}
}

// syntheticLinkSuccessSample is a placeholder for real per-packet ACK
// statistics; replace with actual radio/driver counters on deployment.
func syntheticLinkSuccessSample() float64 {
	return 0.8 + 0.2*rand.Float64()
}
