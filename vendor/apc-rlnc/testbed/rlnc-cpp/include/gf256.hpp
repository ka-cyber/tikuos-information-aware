// GF(256) finite field arithmetic.
//
// IMPORTANT NOTE ON SCOPE: the README references `kodo-cpp` (Steinwurf's
// commercially-licensed RLNC library) for the testbed's coding layer.
// kodo-cpp requires a paid/research license and its source cannot be
// bundled or reconstructed here. This header, together with rlnc.hpp,
// is a self-contained, dependency-free, MIT-licensed GF(256) + RLNC
// implementation that is a drop-in *algorithmic* substitute: it implements
// the same generation model (Section 3.2, Eq. 1) and exposes an encoder /
// decoder API that testbed/orchestration and rlnc-cpp/src/main.cpp use in
// place of kodo-cpp's rlnc::full_vector_encoder/decoder. If you do have a
// kodo-cpp license, swap this header pair out for kodo-cpp's own headers
// and the call sites in main.cpp need only minor signature changes.
#pragma once
#include <cstdint>
#include <array>
#include <vector>
#include <stdexcept>

namespace apc_rlnc {

// Primitive polynomial x^8 + x^4 + x^3 + x^2 + 1 (0x11D). Matches
// simulation/coding/gf256.py exactly, so testbed and simulator agree
// bit-for-bit on field arithmetic.
class GF256 {
public:
    static constexpr uint16_t kPoly = 0x11D;

    GF256() { build_tables(); }

    static const GF256& instance() {
        static GF256 inst;
        return inst;
    }

    inline uint8_t mul(uint8_t a, uint8_t b) const {
        if (a == 0 || b == 0) return 0;
        int idx = log_table_[a] + log_table_[b];
        if (idx >= 255) idx -= 255;
        return exp_table_[idx];
    }

    inline uint8_t inv(uint8_t a) const {
        if (a == 0) throw std::domain_error("GF(256) inverse of 0 is undefined");
        int idx = 255 - log_table_[a];
        return exp_table_[idx];
    }

    inline uint8_t div(uint8_t a, uint8_t b) const {
        if (b == 0) throw std::domain_error("division by zero in GF(256)");
        if (a == 0) return 0;
        int idx = log_table_[a] - log_table_[b];
        if (idx < 0) idx += 255;
        return exp_table_[idx];
    }

    static inline uint8_t add(uint8_t a, uint8_t b) { return a ^ b; }

private:
    std::array<uint8_t, 512> exp_table_{};
    std::array<uint8_t, 256> log_table_{};

    void build_tables() {
        int x = 1;
        for (int i = 0; i < 255; ++i) {
            exp_table_[i] = static_cast<uint8_t>(x);
            log_table_[static_cast<uint8_t>(x)] = static_cast<uint8_t>(i);
            x <<= 1;
            if (x & 0x100) x ^= kPoly;
        }
        for (int i = 255; i < 512; ++i) {
            exp_table_[i] = exp_table_[i - 255];
        }
        log_table_[0] = 0; // undefined; guarded in inv()/div()
    }
};

// Multiply an entire byte vector by a scalar (the hot loop for encode/decode).
inline void axpy(std::vector<uint8_t>& dst, uint8_t scalar,
                  const std::vector<uint8_t>& src) {
    const GF256& gf = GF256::instance();
    if (scalar == 0) return;
    for (size_t i = 0; i < src.size(); ++i) {
        if (src[i] != 0) {
            dst[i] = GF256::add(dst[i], gf.mul(scalar, src[i]));
        }
    }
}

}  // namespace apc_rlnc
