cmake_minimum_required(VERSION 3.22)
project(apc_rlnc_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "-O3")

add_library(apc_rlnc INTERFACE)
target_include_directories(apc_rlnc INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(rlnc_demo src/main.cpp)
target_link_libraries(rlnc_demo PRIVATE apc_rlnc)

# --------------------------------------------------------------------------
# Optional: link against real kodo-cpp instead of the bundled substitute.
# If you have a Steinwurf kodo-cpp license/build, point KODO_CPP_ROOT at it
# and enable USE_KODO_CPP; you'll need to swap include/rlnc.hpp's API calls
# for kodo-cpp's rlnc::full_vector_encoder/decoder in src/main.cpp (their
# API differs from this header-only substitute's).
# --------------------------------------------------------------------------
option(USE_KODO_CPP "Link against a locally-installed kodo-cpp instead of the bundled GF(256)/RLNC substitute" OFF)
if(USE_KODO_CPP)
    if(NOT DEFINED KODO_CPP_ROOT)
        message(FATAL_ERROR "Set -DKODO_CPP_ROOT=/path/to/kodo-cpp when USE_KODO_CPP=ON")
    endif()
    target_include_directories(rlnc_demo PRIVATE ${KODO_CPP_ROOT}/src)
    target_link_directories(rlnc_demo PRIVATE ${KODO_CPP_ROOT}/build)
    target_link_libraries(rlnc_demo PRIVATE kodo)
    target_compile_definitions(rlnc_demo PRIVATE APC_RLNC_USE_KODO_CPP=1)
endif()

enable_testing()
add_test(NAME rlnc_demo_smoke COMMAND rlnc_demo --K 32 --R 16 --p 0.1 --trials 500)
