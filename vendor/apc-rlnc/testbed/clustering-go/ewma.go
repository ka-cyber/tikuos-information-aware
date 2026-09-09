package main

import "sync"

// ReliabilityTracker maintains per-node EWMA reliability scores s_i(t)
// per Eq. (2): s_i(t) = alpha*l_i(t) + (1-alpha)*s_i(t-1), alpha = 0.2.
type ReliabilityTracker struct {
	mu     sync.RWMutex
	alpha  float64
	scores map[string]float64
}

func NewReliabilityTracker(alpha float64) *ReliabilityTracker {
	return &ReliabilityTracker{
		alpha:  alpha,
		scores: make(map[string]float64),
	}
}

// Update applies Eq. (2) for one node given l_i(t) in [0,1] (instantaneous
// packet success rate for this epoch) and returns the new score.
func (rt *ReliabilityTracker) Update(nodeID string, successRate float64) float64 {
	if successRate < 0 {
		successRate = 0
	}
	if successRate > 1 {
		successRate = 1
	}
	rt.mu.Lock()
	defer rt.mu.Unlock()
	prev, ok := rt.scores[nodeID]
	if !ok {
		prev = 0.9 // optimistic prior for a newly-seen peer
	}
	s := rt.alpha*successRate + (1-rt.alpha)*prev
	rt.scores[nodeID] = s
	return s
}

func (rt *ReliabilityTracker) Score(nodeID string) (float64, bool) {
	rt.mu.RLock()
	defer rt.mu.RUnlock()
	s, ok := rt.scores[nodeID]
	return s, ok
}

func (rt *ReliabilityTracker) Snapshot() map[string]float64 {
	rt.mu.RLock()
	defer rt.mu.RUnlock()
	out := make(map[string]float64, len(rt.scores))
	for k, v := range rt.scores {
		out[k] = v
	}
	return out
}

func (rt *ReliabilityTracker) Drop(nodeID string) {
	rt.mu.Lock()
	defer rt.mu.Unlock()
	delete(rt.scores, nodeID)
}
