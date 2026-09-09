// RLNC encoder/decoder over GF(256), mirroring simulation/coding/rlnc.py
// bit-for-bit (same field, same generation model, Section 3.2 / Eq. 1).
#pragma once
#include "gf256.hpp"
#include <cstdint>
#include <vector>
#include <random>
#include <optional>
#include <map>
#include <algorithm>

namespace apc_rlnc {

struct CodedPacket {
    std::vector<uint8_t> coefficients;  // length K
    std::vector<uint8_t> payload;       // length payload_len
};

class RLNCEncoder {
public:
    RLNCEncoder(std::vector<std::vector<uint8_t>> packets, uint64_t seed = std::random_device{}())
        : packets_(std::move(packets)), rng_(seed) {
        K_ = static_cast<int>(packets_.size());
        payload_len_ = K_ > 0 ? static_cast<int>(packets_[0].size()) : 0;
    }

    // Produce n_coded random linear combinations c_j = sum_k alpha_{j,k} p_k.
    std::vector<CodedPacket> generate(int n_coded) {
        std::uniform_int_distribution<int> dist(1, 255);
        std::vector<CodedPacket> out;
        out.reserve(n_coded);
        for (int j = 0; j < n_coded; ++j) {
            CodedPacket pkt;
            pkt.coefficients.resize(K_);
            pkt.payload.assign(payload_len_, 0);
            for (int k = 0; k < K_; ++k) {
                uint8_t coeff = static_cast<uint8_t>(dist(rng_));
                pkt.coefficients[k] = coeff;
                axpy(pkt.payload, coeff, packets_[k]);
            }
            out.push_back(std::move(pkt));
        }
        return out;
    }

    int K() const { return K_; }
    int payload_len() const { return payload_len_; }

private:
    std::vector<std::vector<uint8_t>> packets_;
    int K_ = 0, payload_len_ = 0;
    std::mt19937_64 rng_;
};

class RLNCDecoder {
public:
    RLNCDecoder(int K, int payload_len) : K_(K), payload_len_(payload_len) {}

    int rank() const { return static_cast<int>(coeff_rows_.size()); }
    bool is_decoded() const { return rank() >= K_; }

    // Reduce an incoming coded packet against the current basis. Returns
    // true if it was innovative (increased the rank).
    bool add_packet(const CodedPacket& pkt) {
        std::vector<uint8_t> coeffs = pkt.coefficients;
        std::vector<uint8_t> payload = pkt.payload;
        const GF256& gf = GF256::instance();

        for (const auto& [pivot_col, row_idx] : pivots_) {
            if (coeffs[pivot_col] != 0) {
                uint8_t factor = coeffs[pivot_col];
                axpy(coeffs, factor, coeff_rows_[row_idx]);
                axpy(payload, factor, payload_rows_[row_idx]);
            }
        }

        int pivot_col = -1;
        for (int i = 0; i < K_; ++i) {
            if (coeffs[i] != 0) { pivot_col = i; break; }
        }
        if (pivot_col < 0) return false;  // not innovative

        uint8_t inv = gf.inv(coeffs[pivot_col]);
        for (auto& c : coeffs) c = gf.mul(inv, c);
        for (auto& p : payload) p = gf.mul(inv, p);

        int row_idx = static_cast<int>(coeff_rows_.size());
        coeff_rows_.push_back(std::move(coeffs));
        payload_rows_.push_back(std::move(payload));
        pivots_[pivot_col] = row_idx;
        return true;
    }

    // Back-substitute to recover the original K packets, or nullopt if not
    // yet full rank.
    std::optional<std::vector<std::vector<uint8_t>>> recover() const {
        if (!is_decoded()) return std::nullopt;

        std::vector<std::vector<uint8_t>> coeff_mat(K_), payload_mat(K_);
        for (int c = 0; c < K_; ++c) {
            int row = pivots_.at(c);
            coeff_mat[c] = coeff_rows_[row];
            payload_mat[c] = payload_rows_[row];
        }
        for (int i = K_ - 1; i >= 0; --i) {
            for (int j = 0; j < i; ++j) {
                uint8_t factor = coeff_mat[j][i];
                if (factor != 0) {
                    axpy(coeff_mat[j], factor, coeff_mat[i]);
                    axpy(payload_mat[j], factor, payload_mat[i]);
                }
            }
        }
        return payload_mat;
    }

private:
    int K_, payload_len_;
    std::vector<std::vector<uint8_t>> coeff_rows_;
    std::vector<std::vector<uint8_t>> payload_rows_;
    std::map<int, int> pivots_;  // pivot column -> row index
};

}  // namespace apc_rlnc
