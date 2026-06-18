#include "cgnr.hpp"

#include <cblas.h>

#include <chrono>
#include <fstream>
#include <iomanip>
#include <random>
#include <sstream>
#include <string>
#include <vector>
#include <sys/resource.h>

namespace {

long rss_bytes() {
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
#if defined(__APPLE__)
    return usage.ru_maxrss;
#else
    return usage.ru_maxrss * 1024L;
#endif
}

template <typename Fn>
std::string measure(const std::string& name, const std::string& shape, Fn fn) {
    const long mem_before = rss_bytes();
    const auto start = std::chrono::steady_clock::now();
    fn();
    const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    const long mem_after = rss_bytes();
    std::ostringstream out;
    out << "{\"operation\":\"" << name << "\",\"time_seconds\":" << std::setprecision(12) << elapsed
        << ",\"result_shape\":\"" << shape << "\",\"memory_used_bytes\":" << (mem_after > mem_before ? mem_after - mem_before : 0)
        << ",\"memory_rss_bytes\":" << mem_after << "}";
    return out.str();
}

}  // namespace

void run_blas_tests(int size, const std::string& output_path) {
    std::mt19937_64 rng(42);
    std::normal_distribution<double> dist(0.0, 1.0);
    std::vector<double> M(size * size), N(size * size), R(size * size), v(size), y(size);
    for (double& item : M) item = dist(rng);
    for (double& item : N) item = dist(rng);
    for (double& item : v) item = dist(rng);
    const double scalar = 2.5;

    std::vector<std::string> results;
    results.push_back(measure("MN = M * N", std::to_string(size) + "x" + std::to_string(size), [&] {
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, size, size, size, 1.0, M.data(), size, N.data(), size, 0.0, R.data(), size);
    }));
    results.push_back(measure("aM = a * M (scalar)", std::to_string(size) + "x" + std::to_string(size), [&] {
        R = M;
        cblas_dscal(size * size, scalar, R.data(), 1);
    }));
    results.push_back(measure("aM = a * M (vector left)", "1x" + std::to_string(size), [&] {
        cblas_dgemv(CblasRowMajor, CblasTrans, size, size, 1.0, M.data(), size, v.data(), 1, 0.0, y.data(), 1);
    }));
    results.push_back(measure("Ma = M * a (scalar)", std::to_string(size) + "x" + std::to_string(size), [&] {
        R = M;
        cblas_dscal(size * size, scalar, R.data(), 1);
    }));
    results.push_back(measure("Ma = M * a (vector right)", std::to_string(size) + "x1", [&] {
        cblas_dgemv(CblasRowMajor, CblasNoTrans, size, size, 1.0, M.data(), size, v.data(), 1, 0.0, y.data(), 1);
    }));

    std::ofstream out(output_path);
    out << "{\"service\":\"cpp\",\"blas_backend\":\"CBLAS/OpenBLAS\",\"matrix_size\":" << size << ",\"results\":[";
    for (std::size_t i = 0; i < results.size(); ++i) {
        if (i != 0) out << ',';
        out << results[i];
    }
    out << "]}";
}
