#pragma once

#include <cstddef>
#include <string>
#include <vector>

struct Matrix {
    std::size_t rows{};
    std::size_t cols{};
    std::vector<double> data;
};

struct ReconstructionInput {
    std::string signal_file;
    std::string model_file;
    bool apply_gain{true};
    std::string algorithm{"cgnr"};
    std::string output_dir{"../results"};
};

struct ReconstructionResult {
    std::string status{"ok"};
    std::string service{"cpp"};
    std::string algorithm;
    std::string started_at;
    std::string ended_at;
    double total_time_seconds{};
    double reconstruction_time_seconds{};
    std::string image_dimension;
    int iterations{};
    double epsilon_final{};
    double residual_norm_final{};
    long memory_used_bytes{};
    long memory_rss_bytes{};
    double cpu_seconds{};
    bool apply_gain{};
    std::string model_file;
    std::string signal_file;
    double reduction_factor{};
    double regularization_lambda{};
    std::string csv_output;
    std::string png_output;
    std::string png_visualization_output;
    std::string metadata_file;
};

Matrix load_matrix_csv(const std::string& path);
std::vector<double> load_signal_csv(const std::string& path);
ReconstructionResult reconstruct(const ReconstructionInput& input);
std::string result_to_json(const ReconstructionResult& result);
void run_blas_tests(int size, const std::string& output_path);
