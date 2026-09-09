"""
High-fidelity discrete-event simulator (Section 6.1 / README `run_sim.py`
entry point wraps this module).

Ties together:
  core.ewma            - per-node EWMA reliability scores (Eq. 2)
  core.channel_models  - Bernoulli / 2-state Markov / velocity-fading channels
  core.clustering      - Algorithm 1 distributed adaptive clustering (Eq. 3)
  networks.topology    - node churn (Poisson process)
  networks.mobility    - random-waypoint vehicular mobility
  coding.hierarchical  - hierarchical RLNC encode/decode (Eq. 4-6)

Three encoding "schemes" are implemented as --scheme options, matching the
paper's ablation structure:
  random  - uniform RLNC, fixed R=16, single global cluster (no adaptation)
  static  - cluster once at t=0 via Algorithm 1, never reconfigure
  apc     - full APC-RLNC: reconfigure clusters every tau steps (default)

NOTE on scope: the paper's Table 1/2 baselines also include PACE (Pandi et
al. 2017) and ARLNC (Dilanchian et al. 2024). Faithfully reproducing those
two *external* published algorithms is out of scope for this repository
(that would require reimplementing someone else's paper, not APC-RLNC) --
only `random`, `static`, and `apc` are provided here.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from core.ewma import ReliabilityTracker
from core.channel_models import BernoulliChannel, MarkovChannel, VelocityFadingChannel
from core.clustering import ClusteringOptimizer
from networks.topology import DynamicTopology
from networks.mobility import RandomWaypointMobility
from coding.hierarchical import HierarchicalRLNC, ClusterResult
from metrics import RunMetrics

E_TX, E_RX, E_COMP = 0.2, 0.1, 0.05  # Joules (Section 5.4)


@dataclass
class SimConfig:
    n_nodes: int = 30
    channel: str = 'bernoulli'          # 'bernoulli' | 'markov' | 'velocity'
    burst_duration: int = 50            # only used when channel == 'markov'
    scheme: str = 'apc'                 # 'random' | 'static' | 'apc'
    T: int = 500                        # simulation steps
    generation_interval: int = 5        # steps between generations
    K: int = 32
    beta: float = 1.5
    lam: float = 0.01
    tau: int = 20                       # reconfiguration period (steps)
    churn_rate: float = 0.02
    payload_len: int = 32
    seed: int = 0


class Simulator:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.topology = DynamicTopology(cfg.n_nodes, cfg.churn_rate, rng=self.rng)
        self.tracker = ReliabilityTracker(alpha=0.2)
        self.clusterer = ClusteringOptimizer(lam=cfg.lam, rng=self.rng)
        self.mobility = RandomWaypointMobility(rng=self.rng) if cfg.channel == 'velocity' else None

        for n in self.topology.node_ids():
            self.tracker.register(n)
            if self.mobility:
                self.mobility.add_node(n)

        if cfg.channel == 'bernoulli':
            self.channel = BernoulliChannel(rng=self.rng)
        elif cfg.channel == 'markov':
            self.channel = MarkovChannel.from_burst_duration(cfg.burst_duration, rng=self.rng)
        elif cfg.channel == 'velocity':
            self.channel = VelocityFadingChannel(rng=self.rng)
        else:
            raise ValueError(f"unknown channel model: {cfg.channel}")

        self.clusters: dict[int, list[int]] = {0: self.topology.node_ids()}
        self.metrics = RunMetrics()

    # -- clustering -------------------------------------------------------
    def _reconfigure_clusters(self) -> None:
        node_ids = self.topology.node_ids()
        scores = self.tracker.scores()
        prev = self.clusters
        self.clusters = self.clusterer.fit(node_ids, scores)
        self._record_retention(prev, self.clusters)

    def _record_retention(self, prev: dict[int, list[int]], cur: dict[int, list[int]]) -> None:
        if not prev:
            return
        prev_owner = {n: c for c, members in prev.items() for n in members}
        cur_owner = {n: c for c, members in cur.items() for n in members}
        common = [n for n in cur_owner if n in prev_owner]
        if not common:
            return
        # "Retention" = fraction of nodes whose new cluster still contains a
        # majority of their previous clustermates (proxy for "same cluster"
        # identity across a re-numbered partition).
        retained = 0
        for c_id, members in cur.items():
            prev_labels = [prev_owner.get(n) for n in members if n in prev_owner]
            if not prev_labels:
                continue
            majority_label = max(set(prev_labels), key=prev_labels.count)
            retained += sum(1 for lbl in prev_labels if lbl == majority_label)
        self.metrics.record_retention(retained / max(1, len(common)))

    # -- one simulation run -------------------------------------------------
    def run(self) -> dict:
        cfg = self.cfg
        for t in range(1, cfg.T + 1):
            node_ids = self.topology.node_ids()
            if self.mobility:
                self.mobility.step()

            erasures = self.channel.step(node_ids)

            for n in node_ids:
                was_erased = self.rng.random() < erasures.get(n, 0.1)
                self.tracker.update_from_erasure(n, was_erased)

            departed, joined = self.topology.step_churn()
            for d in departed:
                self.tracker.drop(d)
                self.channel.drop(d)
                if self.mobility:
                    self.mobility.remove_node(d)
            for j in joined:
                self.tracker.register(j)
                if self.mobility:
                    self.mobility.add_node(j)

            if cfg.scheme == 'apc' and t % cfg.tau == 0:
                self._reconfigure_clusters()
            elif cfg.scheme == 'static' and t == cfg.tau:
                self._reconfigure_clusters()
            elif cfg.scheme == 'random':
                self.clusters = {0: self.topology.node_ids()}

            if t % cfg.generation_interval == 0:
                self._run_generation(erasures)

        return self.metrics.summary()

    def _run_generation(self, erasures: dict[int, float]) -> None:
        cfg = self.cfg
        packets = self.rng.integers(0, 256, size=(cfg.K, cfg.payload_len),
                                     dtype=np.uint16).astype(np.uint8)

        if cfg.scheme == 'random':
            # Uniform RLNC baseline: fixed R=16, no clustering.
            from coding.rlnc import RLNCEncoder, RLNCDecoder
            p_mean = float(np.mean(list(erasures.values()))) if erasures else 0.1
            R = 16
            enc = RLNCEncoder(packets, rng=self.rng)
            coded = enc.generate(cfg.K + R)
            dec = RLNCDecoder(cfg.K, cfg.payload_len)
            dof = 0
            for pkt in coded:
                if self.rng.random() < p_mean:
                    continue
                if dec.add_packet(pkt):
                    dof += 1
            self.metrics.record_generation(dec.is_decoded(), cfg.K + R, R / (cfg.K + R))
            energy = E_TX * (cfg.K + R) + E_RX * dof + E_COMP
            self.metrics.record_energy(energy)
            return

        clusters = self.clusters if self.clusters else {0: self.topology.node_ids()}
        hrlnc = HierarchicalRLNC(cfg.K, cfg.payload_len, beta=cfg.beta, rng=self.rng)
        results, bridge = hrlnc.encode_and_transmit(packets, clusters, erasures)

        any_cluster_decoded = any(r.decoded for r in results)
        total_tx = sum(r.K + r.R for r in results) + bridge.shape[0]
        total_R = sum(r.R for r in results) + bridge.shape[0]
        total_dof = sum(r.dof_received for r in results)

        decoded = any_cluster_decoded or (total_dof + bridge.shape[0] >= cfg.K)
        redundancy_ratio = total_R / max(1, total_tx)

        self.metrics.record_generation(decoded, total_tx, redundancy_ratio)
        energy = E_TX * total_tx + E_RX * total_dof + E_COMP * len(clusters)
        self.metrics.record_energy(energy)


def run_many(cfg: SimConfig, n_runs: int) -> list[dict]:
    summaries = []
    for r in range(n_runs):
        run_cfg = SimConfig(**{**cfg.__dict__, 'seed': cfg.seed + r})
        sim = Simulator(run_cfg)
        summaries.append(sim.run())
    return summaries
