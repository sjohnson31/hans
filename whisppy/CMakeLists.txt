cmake_minimum_required(VERSION 3.30)
option(SKBUILD_PROJECT_NAME "whisper.cpp bindings for hans" "whisppy")
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

# Some systems fail to correctly load the dynamic libraries in a venv
# Always using static libraries is reasonable
set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build using shared libraries")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(PYBIND11_FINDPYTHON ON)
add_subdirectory(extern/pybind11)
add_subdirectory(extern/whisper.cpp)

pybind11_add_module(_whisppy MODULE src/bindings.cpp src/library.cpp src/grammar-parser.cpp)

target_link_libraries(_whisppy PRIVATE whisper)

install(
    TARGETS _whisppy DESTINATION ${SKBUILD_PROJECT_NAME}
)
