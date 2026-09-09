#!/usr/bin/env bash
# emulate_channels.sh -- emulate the paper's 2-state Markov erasure channel
# (Section 3.3) on a real wireless interface using Linux tc/netem.
#
# netem's Gilbert-Elliott loss model ("loss gemodel p r 1-h 1-k") maps
# directly onto our 2-state Markov model:
#   p   = P(good -> bad) transition probability   = --transition
#   r   = P(bad  -> good) transition probability  = --transition (symmetric,
#         matching Section 3.3's P_gb = P_bg = 0.10 default)
#   1-h = loss probability while in the BAD state = --loss-bad
#   1-k = loss probability while in the GOOD state = --loss-good
#
# Usage:
#   sudo ./emulate_channels.sh apply --interface wlan0 \
#       --loss-good 0.05 --loss-bad 0.40 --transition 0.10
#   sudo ./emulate_channels.sh clear --interface wlan0
#   sudo ./emulate_channels.sh status --interface wlan0
set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 {apply|clear|status} --interface IFACE [options]

Options (apply only):
  --loss-good FLOAT    packet loss probability in the good state (default 0.05)
  --loss-bad  FLOAT    packet loss probability in the bad state  (default 0.40)
  --transition FLOAT   good<->bad transition probability, symmetric
                        (default 0.10, matches P_gb = P_bg in Section 3.3)
  --delay MS           optional fixed one-way delay to add (default: none)

Requires: iproute2 (tc), root privileges, and a kernel with sch_netem.
EOF
    exit 1
}

[[ $# -ge 1 ]] || usage
CMD="$1"; shift

IFACE=""
LOSS_GOOD=0.05
LOSS_BAD=0.40
TRANSITION=0.10
DELAY_MS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interface) IFACE="$2"; shift 2 ;;
        --loss-good) LOSS_GOOD="$2"; shift 2 ;;
        --loss-bad) LOSS_BAD="$2"; shift 2 ;;
        --transition) TRANSITION="$2"; shift 2 ;;
        --delay) DELAY_MS="$2"; shift 2 ;;
        *) echo "unknown argument: $1"; usage ;;
    esac
done

[[ -n "$IFACE" ]] || { echo "error: --interface is required"; usage; }

# Convert fractional probabilities (0-1) to the percentages tc/netem expects.
to_pct() { awk -v v="$1" 'BEGIN{printf "%.4f", v*100}'; }

case "$CMD" in
    apply)
        command -v tc >/dev/null || { echo "error: tc (iproute2) not found"; exit 1; }

        P=$(to_pct "$TRANSITION")   # good -> bad
        R=$(to_pct "$TRANSITION")   # bad -> good (symmetric)
        ONE_MINUS_H=$(to_pct "$LOSS_BAD")   # loss probability in bad state
        ONE_MINUS_K=$(to_pct "$LOSS_GOOD")  # loss probability in good state

        # Remove any existing qdisc on this interface first (idempotent apply).
        tc qdisc del dev "$IFACE" root 2>/dev/null || true

        if [[ -n "$DELAY_MS" ]]; then
            tc qdisc add dev "$IFACE" root netem \
                loss gemodel "${P}%" "${R}%" "${ONE_MINUS_H}%" "${ONE_MINUS_K}%" \
                delay "${DELAY_MS}ms"
        else
            tc qdisc add dev "$IFACE" root netem \
                loss gemodel "${P}%" "${R}%" "${ONE_MINUS_H}%" "${ONE_MINUS_K}%"
        fi

        echo "Applied 2-state Markov channel emulation on $IFACE:"
        echo "  P(good->bad) = P(bad->good) = ${TRANSITION} (${P}%)"
        echo "  loss(good)   = ${LOSS_GOOD} (${ONE_MINUS_K}%)"
        echo "  loss(bad)    = ${LOSS_BAD} (${ONE_MINUS_H}%)"
        [[ -n "$DELAY_MS" ]] && echo "  extra delay  = ${DELAY_MS}ms"
        echo "Steady-state mean erasure (Section 4.1): $(awk -v g="$LOSS_GOOD" -v b="$LOSS_BAD" 'BEGIN{printf "%.4f", 0.5*g+0.5*b}')"
        ;;

    clear)
        tc qdisc del dev "$IFACE" root 2>/dev/null && \
            echo "Cleared netem qdisc on $IFACE" || \
            echo "No netem qdisc was active on $IFACE"
        ;;

    status)
        tc qdisc show dev "$IFACE"
        ;;

    *)
        usage
        ;;
esac
