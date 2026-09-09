package main

import (
	"math"
	"sort"
)

// PeerState is what each node gossips: its own reliability score and its
// current (tentative) cluster assignment.
type PeerState struct {
	NodeID    string  `json:"node_id"`
	Score     float64 `json:"score"`
	ClusterID int     `json:"cluster_id"`
	Epoch     int64   `json:"epoch"`
}

// ClusteringLoss implements Eq. (3):
//
//	L(C_1:C, t) = sum_c [ Var_{i in C_c}[s_i(t)] - lambda*|C_c| ]
func ClusteringLoss(clusters map[int][]float64, lambda float64) float64 {
	total := 0.0
	for _, members := range clusters {
		if len(members) == 0 {
			continue
		}
		total += variance(members) - lambda*float64(len(members))
	}
	return total
}

func variance(xs []float64) float64 {
	if len(xs) < 2 {
		return 0
	}
	mean := 0.0
	for _, x := range xs {
		mean += x
	}
	mean /= float64(len(xs))
	sumSq := 0.0
	for _, x := range xs {
		d := x - mean
		sumSq += d * d
	}
	return sumSq / float64(len(xs))
}

// InitialK returns k = floor(sqrt(N)/2), per Algorithm 1 step 1.
func InitialK(n int) int {
	k := int(math.Floor(math.Sqrt(float64(n)) / 2))
	if k < 1 {
		k = 1
	}
	return k
}

// KMeans1D runs Algorithm 1's core loop: initialize k centroids, then for
// r=1..rMax rounds reassign each node to argmin_c |s_i - mu_c| and update
// centroids via the (here: simple, in the full gossip daemon:
// consensus-weighted) average of assigned members. Returns
// nodeID -> clusterID.
func KMeans1D(scores map[string]float64, k int, rMax int, seedFn func(i int) float64) map[string]int {
	ids := make([]string, 0, len(scores))
	for id := range scores {
		ids = append(ids, id)
	}
	sort.Strings(ids) // deterministic ordering across peers/runs

	if len(ids) == 0 {
		return map[string]int{}
	}
	if k > len(ids) {
		k = len(ids)
	}
	if k < 1 {
		k = 1
	}

	centroids := make([]float64, k)
	for c := 0; c < k; c++ {
		centroids[c] = seedFn(c)
	}
	sort.Float64s(centroids)

	assignment := make(map[string]int, len(ids))
	for r := 0; r < rMax; r++ {
		changed := false
		sums := make([]float64, k)
		counts := make([]int, k)

		for _, id := range ids {
			s := scores[id]
			best, bestDist := 0, math.Inf(1)
			for c := 0; c < k; c++ {
				d := math.Abs(s - centroids[c])
				if d < bestDist {
					bestDist = d
					best = c
				}
			}
			if assignment[id] != best {
				changed = true
			}
			assignment[id] = best
			sums[best] += s
			counts[best]++
		}

		for c := 0; c < k; c++ {
			if counts[c] > 0 {
				centroids[c] = sums[c] / float64(counts[c])
			}
		}
		if !changed && r > 0 {
			break
		}
	}
	return assignment
}
