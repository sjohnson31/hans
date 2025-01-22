cmake_minimum_required(VERSION 3.30)
option(SKBUILD_PROJECT_NAME "A thing" "transcribe")
project(${SKBUILD_PROJECT_NAME} LANGUAGES CXX)

option(BUILD_SHARED_LIBS "Build using shared libraries" OFF)

set(PYBIND11_FINDPYTHON ON)
add_subdirectory(extern/pybind11)
add_subdirectory(extern/whisper.cpp)

pybind11_add_module(_core MODULE src/main.cpp src/library.cpp src/grammar-parser.cpp)

target_link_libraries(_core PRIVATE whisper)

install(
    TARGETS _core DESTINATION ${SKBUILD_PROJECT_NAME}
)
