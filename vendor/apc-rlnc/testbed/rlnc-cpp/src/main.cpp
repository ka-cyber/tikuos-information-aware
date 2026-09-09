// Demo / smoke-test harness for the RLNC library (Section 6.2's "RLNC:
// kodo-cpp library with custom hierarchical wrapper" -- this is the
// self-contained substitute; see include/gf256.hpp for why).
//
// Build (no CMake needed for a quick check):
//   g++ -std=c++17 -O2 -I include src/main.cpp -o rlnc_demo
//   ./rlnc_demo --K 32 --R 16 --p 0.225 --trials 2000
//
// Or via CMake (see CMakeLists.txt):
//   mkdir build && cd build && cmake .. && make
#include "rlnc.hpp"
#include "gf256.hpp"
#include <iostream>
#include <random>
#include <string>
#include <cstring>

using namespace apc_rlnc;

struct Args {
    int K = 32;
    int R = 16;
    int payload_len = 16;
    double p = 0.225;   // per-packet erasure probability
    int trials = 2000;
    uint64_t seed = 42;
};

Args parse_args(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        auto next = [&](void) -> std::string { return (i + 1 < argc) ? argv[++i] : ""; };
        if (arg == "--K") a.K = std::stoi(next());
        else if (arg == "--R") a.R = std::stoi(next());
        else if (arg == "--payload-len") a.payload_len = std::stoi(next());
        else if (arg == "--p") a.p = std::stod(next());
        else if (arg == "--trials") a.trials = std::stoi(next());
        else if (arg == "--seed") a.seed = std::stoull(next());
    }
    return a;
}

int main(int argc, char** argv) {
    Args args = parse_args(argc, argv);
    std::mt19937_64 rng(args.seed);
    std::uniform_int_distribution<int> byte_dist(0, 255);
    std::uniform_real_distribution<double> unif(0.0, 1.0);

    int successes = 0;
    for (int t = 0; t < args.trials; ++t) {
        std::vector<std::vector<uint8_t>> packets(args.K, std::vector<uint8_t>(args.payload_len));
        for (auto& pkt : packets)
            for (auto& b : pkt) b = static_cast<uint8_t>(byte_dist(rng));

        RLNCEncoder encoder(packets, args.seed + t);
        auto coded = encoder.generate(args.K + args.R);

        RLNCDecoder decoder(args.K, args.payload_len);
        for (const auto& pkt : coded) {
            if (unif(rng) < args.p) continue;  // simulated erasure
            decoder.add_packet(pkt);
        }

        if (decoder.is_decoded()) {
            auto recovered = decoder.recover();
            bool matches = true;
            for (int k = 0; k < args.K && matches; ++k) {
                if ((*recovered)[k] != packets[k]) matches = false;
            }
            if (matches) ++successes;
        }
    }

    double empirical = static_cast<double>(successes) / args.trials;
    std::cout << "RLNC demo: K=" << args.K << " R=" << args.R
              << " p=" << args.p << " trials=" << args.trials << "\n"
              << "Empirical decode success rate: " << empirical << "\n"
              << "(compare against simulation/coding/rlnc.py::decode_probability"
              << " for the closed-form Eq. (1) value)\n";
    return 0;
}
