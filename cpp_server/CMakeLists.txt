cmake_minimum_required(VERSION 3.16)
project(cpp_reconstruction_server LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(BLAS REQUIRED)

add_executable(cpp_reconstruction_server
    main.cpp
    cgnr.cpp
    blas_tests.cpp
)

target_link_libraries(cpp_reconstruction_server PRIVATE ${BLAS_LIBRARIES})
target_compile_options(cpp_reconstruction_server PRIVATE -Wall -Wextra -Wpedantic)
