#include "cgnr.hpp"

#include <cblas.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <sys/resource.h>
#include <unordered_map>

namespace {

constexpr double kEpsilonThreshold = 1e-4;
constexpr int kMaxIterations = 10;

std::mutex g_cache_mutex;
std::unordered_map<std::string, std::shared_ptr<Matrix>> g_matrix_cache;
std::unordered_map<std::string, double> g_reduction_factor_cache;

std::string utc_now() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    gmtime_r(&t, &tm);
    std::ostringstream out;
    out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

long rss_bytes() {
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
#if defined(__APPLE__)
    return usage.ru_maxrss;
#else
    return usage.ru_maxrss * 1024L;
#endif
}

double cpu_seconds() {
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
    return static_cast<double>(usage.ru_utime.tv_sec) + usage.ru_utime.tv_usec / 1e6 +
           static_cast<double>(usage.ru_stime.tv_sec) + usage.ru_stime.tv_usec / 1e6;
}

double dot(const std::vector<double>& a, const std::vector<double>& b) {
    return cblas_ddot(static_cast<int>(a.size()), a.data(), 1, b.data(), 1);
}

double norm2(const std::vector<double>& v) {
    return cblas_dnrm2(static_cast<int>(v.size()), v.data(), 1);
}

double safe_divide(double numerator, double denominator) {
    if (denominator <= std::numeric_limits<double>::epsilon()) {
        return 0.0;
    }
    return numerator / denominator;
}

std::vector<double> matvec(const Matrix& H, const std::vector<double>& x) {
    std::vector<double> y(H.rows, 0.0);
    cblas_dgemv(CblasRowMajor, CblasNoTrans, static_cast<int>(H.rows), static_cast<int>(H.cols),
                1.0, H.data.data(), static_cast<int>(H.cols), x.data(), 1, 0.0, y.data(), 1);
    return y;
}

std::vector<double> trans_matvec(const Matrix& H, const std::vector<double>& x) {
    std::vector<double> y(H.cols, 0.0);
    cblas_dgemv(CblasRowMajor, CblasTrans, static_cast<int>(H.rows), static_cast<int>(H.cols),
                1.0, H.data.data(), static_cast<int>(H.cols), x.data(), 1, 0.0, y.data(), 1);
    return y;
}

void axpy(double alpha, const std::vector<double>& x, std::vector<double>& y) {
    cblas_daxpy(static_cast<int>(x.size()), alpha, x.data(), 1, y.data(), 1);
}

std::vector<double> signal_gain(std::vector<double> g) {
    for (std::size_t i = 0; i < g.size(); ++i) {
        const double l = static_cast<double>(i + 1);
        const double gamma = 100.0 + 0.05 * l * std::sqrt(l);
        g[i] *= gamma;
    }
    return g;
}

double estimate_reduction_factor(const Matrix& H) {
    std::vector<double> v(H.cols, 1.0 / std::sqrt(static_cast<double>(H.cols)));
    double value = 0.0;
    for (int i = 0; i < 12; ++i) {
        std::vector<double> Hv = matvec(H, v);
        std::vector<double> normal = trans_matvec(H, Hv);
        const double n = norm2(normal);
        if (n == 0.0) {
            return 0.0;
        }
        for (double& item : normal) {
            item /= n;
        }
        v = std::move(normal);
        Hv = matvec(H, v);
        normal = trans_matvec(H, Hv);
        value = dot(v, normal);
    }
    return value;
}

std::shared_ptr<Matrix> load_cached_matrix(const std::string& path) {
    {
        std::lock_guard<std::mutex> lock(g_cache_mutex);
        const auto existing = g_matrix_cache.find(path);
        if (existing != g_matrix_cache.end()) {
            return existing->second;
        }
    }

    auto matrix = std::make_shared<Matrix>(load_matrix_csv(path));
    {
        std::lock_guard<std::mutex> lock(g_cache_mutex);
        const auto [it, inserted] = g_matrix_cache.emplace(path, matrix);
        return inserted ? matrix : it->second;
    }
}

double cached_reduction_factor(const std::string& path, const Matrix& H) {
    {
        std::lock_guard<std::mutex> lock(g_cache_mutex);
        const auto existing = g_reduction_factor_cache.find(path);
        if (existing != g_reduction_factor_cache.end()) {
            return existing->second;
        }
    }

    const double value = estimate_reduction_factor(H);
    {
        std::lock_guard<std::mutex> lock(g_cache_mutex);
        const auto [it, inserted] = g_reduction_factor_cache.emplace(path, value);
        return inserted ? value : it->second;
    }
}

double regularization_lambda(const Matrix& H, const std::vector<double>& g) {
    const std::vector<double> htg = trans_matvec(H, g);
    double max_abs = 0.0;
    for (double value : htg) {
        max_abs = std::max(max_abs, std::abs(value));
    }
    return max_abs * 0.10;
}

struct SolverStats {
    std::vector<double> f;
    int iterations{};
    double epsilon{};
    double residual_norm{};
};

SolverStats solve_cgnr(const Matrix& H, const std::vector<double>& g) {
    std::vector<double> f(H.cols, 0.0);
    std::vector<double> r = g;
    std::vector<double> z = trans_matvec(H, r);
    std::vector<double> p = z;
    double previous_norm = norm2(r);
    double epsilon = std::numeric_limits<double>::infinity();
    int iterations = 0;

    for (int i = 0; i < kMaxIterations; ++i) {
        std::vector<double> w = matvec(H, p);
        const double z_norm_sq = dot(z, z);
        const double alpha = safe_divide(z_norm_sq, dot(w, w));
        axpy(alpha, p, f);
        axpy(-alpha, w, r);
        const double current_norm = norm2(r);
        epsilon = std::abs(current_norm - previous_norm);
        iterations = i + 1;

        std::vector<double> z_next = trans_matvec(H, r);
        const double beta = safe_divide(dot(z_next, z_next), z_norm_sq);
        for (std::size_t j = 0; j < p.size(); ++j) {
            p[j] = z_next[j] + beta * p[j];
        }
        z = std::move(z_next);
        previous_norm = current_norm;
        if (epsilon < kEpsilonThreshold) {
            break;
        }
    }
    return {f, iterations, epsilon, norm2(r)};
}

SolverStats solve_cgne(const Matrix& H, const std::vector<double>& g) {
    std::vector<double> f(H.cols, 0.0);
    std::vector<double> r = g;
    std::vector<double> p = trans_matvec(H, r);
    double previous_norm = norm2(r);
    double epsilon = std::numeric_limits<double>::infinity();
    int iterations = 0;

    for (int i = 0; i < kMaxIterations; ++i) {
        std::vector<double> hp = matvec(H, p);
        const double r_norm_sq = dot(r, r);
        const double alpha = safe_divide(r_norm_sq, dot(p, p));
        axpy(alpha, p, f);
        axpy(-alpha, hp, r);
        const double current_norm = norm2(r);
        epsilon = std::abs(current_norm - previous_norm);
        iterations = i + 1;

        std::vector<double> htr = trans_matvec(H, r);
        const double beta = safe_divide(dot(r, r), r_norm_sq);
        for (std::size_t j = 0; j < p.size(); ++j) {
            p[j] = htr[j] + beta * p[j];
        }
        previous_norm = current_norm;
        if (epsilon < kEpsilonThreshold) {
            break;
        }
    }
    return {f, iterations, epsilon, norm2(r)};
}

std::size_t image_dimension(std::size_t size) {
    if (size == 900) return 30;
    if (size == 3600) return 60;
    const auto root = static_cast<std::size_t>(std::sqrt(static_cast<double>(size)));
    if (root * root == size) return root;
    throw std::runtime_error("Tamanho de imagem não suportado");
}

uint32_t crc32(const std::vector<unsigned char>& bytes) {
    uint32_t crc = 0xffffffffu;
    for (unsigned char byte : bytes) {
        crc ^= byte;
        for (int k = 0; k < 8; ++k) {
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
        }
    }
    return crc ^ 0xffffffffu;
}

uint32_t adler32(const std::vector<unsigned char>& bytes) {
    uint32_t a = 1, b = 0;
    for (unsigned char byte : bytes) {
        a = (a + byte) % 65521u;
        b = (b + a) % 65521u;
    }
    return (b << 16) | a;
}

void write_u32(std::ofstream& out, uint32_t value) {
    out.put(static_cast<char>((value >> 24) & 0xff));
    out.put(static_cast<char>((value >> 16) & 0xff));
    out.put(static_cast<char>((value >> 8) & 0xff));
    out.put(static_cast<char>(value & 0xff));
}

void write_chunk(std::ofstream& out, const std::string& type, const std::vector<unsigned char>& data) {
    write_u32(out, static_cast<uint32_t>(data.size()));
    std::vector<unsigned char> crc_input(type.begin(), type.end());
    crc_input.insert(crc_input.end(), data.begin(), data.end());
    out.write(type.data(), static_cast<std::streamsize>(type.size()));
    out.write(reinterpret_cast<const char*>(data.data()), static_cast<std::streamsize>(data.size()));
    write_u32(out, crc32(crc_input));
}

void write_png_pixels(const std::vector<unsigned char>& pixels, std::size_t width, std::size_t height, const std::string& path) {
    std::vector<unsigned char> raw;
    raw.reserve((width + 1) * height);
    for (std::size_t row = 0; row < height; ++row) {
        raw.push_back(0);
        for (std::size_t col = 0; col < width; ++col) {
            raw.push_back(pixels[row * width + col]);
        }
    }

    std::vector<unsigned char> zdata{0x78, 0x01};
    std::size_t offset = 0;
    while (offset < raw.size()) {
        const std::size_t block_len = std::min<std::size_t>(65535, raw.size() - offset);
        const bool final = offset + block_len == raw.size();
        zdata.push_back(final ? 0x01 : 0x00);
        const uint16_t len = static_cast<uint16_t>(block_len);
        const uint16_t nlen = static_cast<uint16_t>(~len);
        zdata.push_back(static_cast<unsigned char>(len & 0xff));
        zdata.push_back(static_cast<unsigned char>((len >> 8) & 0xff));
        zdata.push_back(static_cast<unsigned char>(nlen & 0xff));
        zdata.push_back(static_cast<unsigned char>((nlen >> 8) & 0xff));
        zdata.insert(zdata.end(), raw.begin() + static_cast<long>(offset), raw.begin() + static_cast<long>(offset + block_len));
        offset += block_len;
    }
    const uint32_t adler = adler32(raw);
    zdata.push_back(static_cast<unsigned char>((adler >> 24) & 0xff));
    zdata.push_back(static_cast<unsigned char>((adler >> 16) & 0xff));
    zdata.push_back(static_cast<unsigned char>((adler >> 8) & 0xff));
    zdata.push_back(static_cast<unsigned char>(adler & 0xff));

    std::ofstream out(path, std::ios::binary);
    const unsigned char signature[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    out.write(reinterpret_cast<const char*>(signature), 8);
    std::vector<unsigned char> ihdr(13, 0);
    ihdr[0] = static_cast<unsigned char>((width >> 24) & 0xff);
    ihdr[1] = static_cast<unsigned char>((width >> 16) & 0xff);
    ihdr[2] = static_cast<unsigned char>((width >> 8) & 0xff);
    ihdr[3] = static_cast<unsigned char>(width & 0xff);
    ihdr[4] = static_cast<unsigned char>((height >> 24) & 0xff);
    ihdr[5] = static_cast<unsigned char>((height >> 16) & 0xff);
    ihdr[6] = static_cast<unsigned char>((height >> 8) & 0xff);
    ihdr[7] = static_cast<unsigned char>(height & 0xff);
    ihdr[8] = 8;
    ihdr[9] = 0;
    write_chunk(out, "IHDR", ihdr);
    write_chunk(out, "IDAT", zdata);
    write_chunk(out, "IEND", {});
}

double oriented_value(const std::vector<double>& f, std::size_t dim, std::size_t row, std::size_t col) {
    return f[col * dim + row];
}

std::vector<unsigned char> normalize_oriented(const std::vector<double>& f, std::size_t dim, bool log_abs) {
    std::vector<double> values(dim * dim);
    for (std::size_t row = 0; row < dim; ++row) {
        for (std::size_t col = 0; col < dim; ++col) {
            const double value = oriented_value(f, dim, row, col);
            values[row * dim + col] = log_abs ? std::log1p(std::abs(value)) : value;
        }
    }
    if (log_abs) {
        std::vector<double> sorted = values;
        std::sort(sorted.begin(), sorted.end());
        const double percentile_threshold = sorted[static_cast<std::size_t>(std::floor(0.974 * static_cast<double>(sorted.size() - 1)))];
        const double max_score = sorted.back();
        const double threshold = std::max(percentile_threshold, max_score * 0.30);
        struct Candidate {
            double value;
            std::size_t row;
            std::size_t col;
        };
        std::vector<Candidate> candidates;
        for (std::size_t row = 0; row < dim; ++row) {
            for (std::size_t col = 0; col < dim; ++col) {
                const double value = values[row * dim + col];
                if (value < threshold) {
                    continue;
                }
                bool local_max = true;
                const std::size_t r0 = row == 0 ? 0 : row - 1;
                const std::size_t r1 = std::min(dim - 1, row + 1);
                const std::size_t c0 = col == 0 ? 0 : col - 1;
                const std::size_t c1 = std::min(dim - 1, col + 1);
                for (std::size_t rr = r0; rr <= r1 && local_max; ++rr) {
                    for (std::size_t cc = c0; cc <= c1; ++cc) {
                        if (values[rr * dim + cc] > value) {
                            local_max = false;
                            break;
                        }
                    }
                }
                if (local_max) {
                    candidates.push_back({value, row, col});
                }
            }
        }
        std::sort(candidates.begin(), candidates.end(), [](const Candidate& a, const Candidate& b) {
            return a.value > b.value;
        });
        const std::size_t max_spots = dim >= 60 ? 72 : 30;
        const int min_distance = 2;
        std::vector<Candidate> selected;
        for (const Candidate& candidate : candidates) {
            bool far_enough = true;
            for (const Candidate& existing : selected) {
                const int dr = static_cast<int>(candidate.row) - static_cast<int>(existing.row);
                const int dc = static_cast<int>(candidate.col) - static_cast<int>(existing.col);
                if (dr * dr + dc * dc < min_distance * min_distance) {
                    far_enough = false;
                    break;
                }
            }
            if (far_enough) {
                selected.push_back(candidate);
            }
            if (selected.size() >= max_spots) {
                break;
            }
        }
        std::vector<unsigned char> pixels(dim * dim, 0);
        if (selected.empty()) {
            return pixels;
        }
        double min_selected = selected.front().value;
        double max_selected = selected.front().value;
        for (const Candidate& candidate : selected) {
            min_selected = std::min(min_selected, candidate.value);
            max_selected = std::max(max_selected, candidate.value);
        }
        for (const Candidate& candidate : selected) {
            const double normalized = (max_selected - min_selected <= std::numeric_limits<double>::epsilon())
                                          ? 1.0
                                          : (candidate.value - min_selected) / (max_selected - min_selected);
            const auto intensity = static_cast<unsigned char>(std::clamp(0.45 + 0.55 * normalized, 0.0, 1.0) * 255.0);
            pixels[candidate.row * dim + candidate.col] = std::max(pixels[candidate.row * dim + candidate.col], intensity);
            if (dim >= 60) {
                const auto secondary = static_cast<unsigned char>(static_cast<double>(intensity) * 0.72);
                if (candidate.row + 1 < dim) {
                    pixels[(candidate.row + 1) * dim + candidate.col] = std::max(pixels[(candidate.row + 1) * dim + candidate.col], secondary);
                }
                if (candidate.col + 1 < dim) {
                    pixels[candidate.row * dim + candidate.col + 1] = std::max(pixels[candidate.row * dim + candidate.col + 1], secondary);
                }
            }
        }
        return pixels;
    }

    double min_v = 0.0;
    double max_v = 0.0;
    const auto [min_it, max_it] = std::minmax_element(values.begin(), values.end());
    min_v = *min_it;
    max_v = *max_it;
    std::vector<unsigned char> pixels(dim * dim, 0);
    for (std::size_t i = 0; i < values.size(); ++i) {
        const double scaled = (max_v - min_v <= std::numeric_limits<double>::epsilon())
                                  ? 0.0
                                  : (values[i] - min_v) / (max_v - min_v) * 255.0;
        pixels[i] = static_cast<unsigned char>(std::clamp(scaled, 0.0, 255.0));
    }
    return pixels;
}

void draw_rect(std::vector<unsigned char>& pixels, std::size_t width, std::size_t x, std::size_t y, std::size_t w, std::size_t h, unsigned char color) {
    const std::size_t height = pixels.size() / width;
    for (std::size_t row = y; row < std::min(y + h, height); ++row) {
        for (std::size_t col = x; col < std::min(x + w, width); ++col) {
            pixels[row * width + col] = color;
        }
    }
}

const std::vector<std::string>& glyph(char c) {
    static const std::vector<std::string> zero{"111", "101", "101", "101", "111"};
    static const std::vector<std::string> one{"010", "110", "010", "010", "111"};
    static const std::vector<std::string> two{"111", "001", "111", "100", "111"};
    static const std::vector<std::string> three{"111", "001", "111", "001", "111"};
    static const std::vector<std::string> four{"101", "101", "111", "001", "001"};
    static const std::vector<std::string> five{"111", "100", "111", "001", "111"};
    static const std::vector<std::string> six{"111", "100", "111", "101", "111"};
    static const std::vector<std::string> seven{"111", "001", "001", "001", "001"};
    static const std::vector<std::string> eight{"111", "101", "111", "101", "111"};
    static const std::vector<std::string> nine{"111", "101", "111", "001", "111"};
    static const std::vector<std::string> cap_l{"100", "100", "100", "100", "111"};
    static const std::vector<std::string> cap_o{"111", "101", "101", "101", "111"};
    static const std::vector<std::string> cap_g{"111", "100", "101", "101", "111"};
    static const std::vector<std::string> low_o{"000", "111", "101", "101", "111"};
    static const std::vector<std::string> low_g{"011", "100", "101", "011", "001", "110"};
    static const std::vector<std::string> blank{"000", "000", "000", "000", "000"};
    switch (c) {
        case '0': return zero; case '1': return one; case '2': return two; case '3': return three; case '4': return four;
        case '5': return five; case '6': return six; case '7': return seven; case '8': return eight; case '9': return nine;
        case 'L': return cap_l; case 'O': return cap_o; case 'G': return cap_g;
        case 'o': return low_o; case 'g': return low_g; default: return blank;
    }
}

void draw_text(std::vector<unsigned char>& pixels, std::size_t width, std::size_t x, std::size_t y, const std::string& text, unsigned char color, std::size_t scale = 2) {
    std::size_t cursor = x;
    for (char c : text) {
        const auto& g = glyph(c);
        for (std::size_t row = 0; row < g.size(); ++row) {
            for (std::size_t col = 0; col < g[row].size(); ++col) {
                if (g[row][col] == '1') {
                    draw_rect(pixels, width, cursor + col * scale, y + row * scale, scale, scale, color);
                }
            }
        }
        cursor += 4 * scale;
    }
}

void save_png(const std::vector<double>& f, std::size_t dim, const std::string& path) {
    write_png_pixels(normalize_oriented(f, dim, false), dim, dim, path);
}

void save_visualization_png(const std::vector<double>& f, std::size_t dim, const std::string& path) {
    const std::size_t scale = 4;
    const std::size_t plot = dim * scale;
    const std::size_t left = 42;
    const std::size_t top = 28;
    const std::size_t width = left + plot + 18;
    const std::size_t height = top + plot + 38;
    std::vector<unsigned char> canvas(width * height, 255);
    const std::vector<unsigned char> image = normalize_oriented(f, dim, true);
    draw_text(canvas, width, left + plot / 2 - 12, 8, "LOG", 0, 2);
    for (std::size_t row = 0; row < dim; ++row) {
        for (std::size_t col = 0; col < dim; ++col) {
            const unsigned char color = image[row * dim + col];
            draw_rect(canvas, width, left + col * scale, top + row * scale, scale, scale, color);
        }
    }
    for (std::size_t tick = 10; tick <= dim; tick += 10) {
        const std::size_t pos = tick - 1;
        const std::size_t x = left + pos * scale;
        const std::size_t y = top + pos * scale;
        draw_rect(canvas, width, x, top + plot, 1, 5, 0);
        draw_rect(canvas, width, left - 5, y, 5, 1, 0);
        draw_text(canvas, width, x - 5, top + plot + 9, std::to_string(tick), 0, 1);
        draw_text(canvas, width, 14, y - 4, std::to_string(tick), 0, 1);
    }
    write_png_pixels(canvas, width, height, path);
}

void save_csv_image(const std::vector<double>& f, std::size_t dim, const std::string& path) {
    std::ofstream out(path);
    for (std::size_t row = 0; row < dim; ++row) {
        for (std::size_t col = 0; col < dim; ++col) {
            if (col != 0) out << ',';
            out << std::setprecision(17) << oriented_value(f, dim, row, col);
        }
        out << '\n';
    }
}

std::string json_escape(const std::string& text) {
    std::ostringstream out;
    for (char c : text) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c == '\n') out << "\\n";
        else out << c;
    }
    return out.str();
}

std::string stamp() {
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    return std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(now).count());
}

}  // namespace

Matrix load_matrix_csv(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("Arquivo de matriz não encontrado: " + path);
    }
    Matrix matrix;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string cell;
        std::size_t cols = 0;
        while (std::getline(ss, cell, ',')) {
            matrix.data.push_back(std::stod(cell));
            ++cols;
        }
        if (matrix.cols == 0) {
            matrix.cols = cols;
        } else if (matrix.cols != cols) {
            throw std::runtime_error("CSV de matriz com número irregular de colunas: " + path);
        }
        ++matrix.rows;
    }
    return matrix;
}

std::vector<double> load_signal_csv(const std::string& path) {
    Matrix signal = load_matrix_csv(path);
    if (signal.rows != 1 && signal.cols != 1) {
        throw std::runtime_error("Sinal deve ter uma linha ou uma coluna: " + path);
    }
    return signal.data;
}

ReconstructionResult reconstruct(const ReconstructionInput& input) {
    const auto wall_start = std::chrono::steady_clock::now();
    const double cpu_start = cpu_seconds();
    const long mem_start = rss_bytes();
    ReconstructionResult result;
    result.started_at = utc_now();
    result.algorithm = input.algorithm == "cgne" ? "CGNE" : "CGNR";
    result.apply_gain = input.apply_gain;
    result.model_file = input.model_file;
    result.signal_file = input.signal_file;

    const std::shared_ptr<Matrix> H_ptr = load_cached_matrix(input.model_file);
    const Matrix& H = *H_ptr;
    std::vector<double> g = load_signal_csv(input.signal_file);
    if (H.rows != g.size()) {
        throw std::runtime_error("Dimensão incompatível entre H e g");
    }
    if (input.apply_gain) {
        g = signal_gain(std::move(g));
    }

    result.reduction_factor = cached_reduction_factor(input.model_file, H);
    result.regularization_lambda = regularization_lambda(H, g);

    const auto rec_start = std::chrono::steady_clock::now();
    SolverStats stats = input.algorithm == "cgne" ? solve_cgne(H, g) : solve_cgnr(H, g);
    result.reconstruction_time_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - rec_start).count();

    const std::size_t dim = image_dimension(stats.f.size());
    std::filesystem::create_directories(input.output_dir);
    const std::string base = input.output_dir + "/cpp_" + input.algorithm + "_" + stamp();
    result.csv_output = base + ".csv";
    result.png_output = base + ".png";
    result.png_visualization_output = base + "_visualization.png";
    result.metadata_file = base + "_metadata.json";
    save_csv_image(stats.f, dim, result.csv_output);
    save_png(stats.f, dim, result.png_output);
    save_visualization_png(stats.f, dim, result.png_visualization_output);

    result.ended_at = utc_now();
    result.total_time_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - wall_start).count();
    result.image_dimension = std::to_string(dim) + "x" + std::to_string(dim);
    result.iterations = stats.iterations;
    result.epsilon_final = stats.epsilon;
    result.residual_norm_final = stats.residual_norm;
    result.memory_rss_bytes = rss_bytes();
    result.memory_used_bytes = std::max<long>(0, result.memory_rss_bytes - mem_start);
    result.cpu_seconds = cpu_seconds() - cpu_start;

    std::ofstream metadata(result.metadata_file);
    metadata << result_to_json(result);
    return result;
}

std::string result_to_json(const ReconstructionResult& r) {
    std::ostringstream out;
    out << std::setprecision(12);
    out << "{";
    out << "\"status\":\"" << r.status << "\",";
    out << "\"service\":\"" << r.service << "\",";
    out << "\"algorithm\":\"" << r.algorithm << "\",";
    out << "\"started_at\":\"" << r.started_at << "\",";
    out << "\"ended_at\":\"" << r.ended_at << "\",";
    out << "\"total_time_seconds\":" << r.total_time_seconds << ",";
    out << "\"reconstruction_time_seconds\":" << r.reconstruction_time_seconds << ",";
    out << "\"image_dimension\":\"" << r.image_dimension << "\",";
    out << "\"iterations\":" << r.iterations << ",";
    out << "\"epsilon_final\":" << r.epsilon_final << ",";
    out << "\"residual_norm_final\":" << r.residual_norm_final << ",";
    out << "\"memory_used_bytes\":" << r.memory_used_bytes << ",";
    out << "\"memory_rss_bytes\":" << r.memory_rss_bytes << ",";
    out << "\"cpu_seconds\":" << r.cpu_seconds << ",";
    out << "\"apply_gain\":" << (r.apply_gain ? "true" : "false") << ",";
    out << "\"model_file\":\"" << json_escape(r.model_file) << "\",";
    out << "\"signal_file\":\"" << json_escape(r.signal_file) << "\",";
    out << "\"reduction_factor\":" << r.reduction_factor << ",";
    out << "\"regularization_lambda\":" << r.regularization_lambda << ",";
    out << "\"outputs\":{\"dimension\":\"" << r.image_dimension << "\",\"orientation\":\"column-major\",\"csv\":\"" << json_escape(r.csv_output)
        << "\",\"png\":\"" << json_escape(r.png_output) << "\",\"png_raw\":\"" << json_escape(r.png_output)
        << "\",\"png_visualization\":\"" << json_escape(r.png_visualization_output) << "\"},";
    out << "\"metadata_file\":\"" << json_escape(r.metadata_file) << "\"";
    out << "}";
    return out.str();
}
