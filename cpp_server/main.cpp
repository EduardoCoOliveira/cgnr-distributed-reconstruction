#include "cgnr.hpp"

#include <arpa/inet.h>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <netinet/in.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unistd.h>

namespace {

std::atomic<int> active_reconstructions{0};

std::string extract_string(const std::string& body, const std::string& key, const std::string& fallback = "") {
    const std::string needle = "\"" + key + "\"";
    const std::size_t key_pos = body.find(needle);
    if (key_pos == std::string::npos) return fallback;
    const std::size_t colon = body.find(':', key_pos);
    const std::size_t first_quote = body.find('"', colon + 1);
    const std::size_t second_quote = body.find('"', first_quote + 1);
    if (colon == std::string::npos || first_quote == std::string::npos || second_quote == std::string::npos) return fallback;
    return body.substr(first_quote + 1, second_quote - first_quote - 1);
}

bool extract_bool(const std::string& body, const std::string& key, bool fallback = true) {
    const std::string needle = "\"" + key + "\"";
    const std::size_t key_pos = body.find(needle);
    if (key_pos == std::string::npos) return fallback;
    const std::size_t colon = body.find(':', key_pos);
    if (colon == std::string::npos) return fallback;
    const std::string rest = body.substr(colon + 1, 8);
    if (rest.find("false") != std::string::npos) return false;
    if (rest.find("true") != std::string::npos) return true;
    return fallback;
}

std::string project_path(const std::string& path) {
    if (path.empty() || path[0] == '/') return path;
    return (std::filesystem::current_path().parent_path() / path).string();
}

void send_response(int client, int status, const std::string& reason, const std::string& body) {
    std::ostringstream response;
    response << "HTTP/1.1 " << status << ' ' << reason << "\r\n";
    response << "Content-Type: application/json; charset=utf-8\r\n";
    response << "Content-Length: " << body.size() << "\r\n";
    response << "Connection: close\r\n\r\n";
    response << body;
    const std::string text = response.str();
    send(client, text.data(), text.size(), 0);
}

std::string read_request(int client) {
    std::string request;
    char buffer[8192];
    while (true) {
        const ssize_t received = recv(client, buffer, sizeof(buffer), 0);
        if (received <= 0) break;
        request.append(buffer, static_cast<std::size_t>(received));
        const std::size_t header_end = request.find("\r\n\r\n");
        if (header_end != std::string::npos) {
            const std::size_t content_length_pos = request.find("Content-Length:");
            std::size_t content_length = 0;
            if (content_length_pos != std::string::npos) {
                const std::size_t start = content_length_pos + std::strlen("Content-Length:");
                content_length = static_cast<std::size_t>(std::stoul(request.substr(start, request.find("\r\n", start) - start)));
            }
            if (request.size() >= header_end + 4 + content_length) break;
        }
    }
    return request;
}

void handle_client(int client, int max_concurrent) {
    try {
        const std::string request = read_request(client);
        if (request.rfind("GET /health", 0) == 0) {
            send_response(client, 200, "OK", "{\"status\":\"ok\",\"service\":\"cpp\"}");
            close(client);
            return;
        }
        if (request.rfind("POST /reconstruct", 0) != 0) {
            send_response(client, 404, "Not Found", "{\"status\":\"error\",\"error\":\"endpoint não encontrado\"}");
            close(client);
            return;
        }
        if (active_reconstructions.fetch_add(1) >= max_concurrent) {
            active_reconstructions.fetch_sub(1);
            send_response(client, 429, "Too Many Requests", "{\"status\":\"error\",\"error\":\"Servidor C++ saturado\"}");
            close(client);
            return;
        }

        const std::size_t body_pos = request.find("\r\n\r\n");
        const std::string body = body_pos == std::string::npos ? "" : request.substr(body_pos + 4);
        ReconstructionInput input;
        input.signal_file = project_path(extract_string(body, "signal_file"));
        input.model_file = project_path(extract_string(body, "model_file"));
        input.apply_gain = extract_bool(body, "apply_gain", true);
        input.algorithm = extract_string(body, "algorithm", "cgnr");
        input.output_dir = (std::filesystem::current_path().parent_path() / "results").string();
        if (input.algorithm != "cgnr" && input.algorithm != "cgne") {
            throw std::runtime_error("algorithm deve ser 'cgnr' ou 'cgne'");
        }

        const ReconstructionResult result = reconstruct(input);
        send_response(client, 200, "OK", result_to_json(result));
        active_reconstructions.fetch_sub(1);
    } catch (const std::exception& exc) {
        active_reconstructions.fetch_sub(1);
        std::string message = "{\"status\":\"error\",\"error\":\"";
        message += exc.what();
        message += "\"}";
        send_response(client, 500, "Internal Server Error", message);
    }
    close(client);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "--blas-tests") {
        const std::string output = argc > 2 ? argv[2] : "../results/cpp_blas_report.json";
        run_blas_tests(512, output);
        std::cout << "BLAS report written to " << output << "\n";
        return 0;
    }

    const int port = std::getenv("CPP_SERVER_PORT") ? std::atoi(std::getenv("CPP_SERVER_PORT")) : 8001;
    const int max_concurrent = std::getenv("MAX_CONCURRENT_RECONSTRUCTIONS") ? std::atoi(std::getenv("MAX_CONCURRENT_RECONSTRUCTIONS")) : 2;
    const int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        throw std::runtime_error("não foi possível criar socket");
    }
    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(static_cast<uint16_t>(port));
    if (bind(server_fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0) {
        throw std::runtime_error("bind falhou");
    }
    if (listen(server_fd, 64) < 0) {
        throw std::runtime_error("listen falhou");
    }
    std::cout << "C++ reconstruction server listening on port " << port << "\n";

    while (true) {
        sockaddr_in client_address{};
        socklen_t length = sizeof(client_address);
        const int client = accept(server_fd, reinterpret_cast<sockaddr*>(&client_address), &length);
        if (client >= 0) {
            std::thread(handle_client, client, max_concurrent).detach();
        }
    }
}
