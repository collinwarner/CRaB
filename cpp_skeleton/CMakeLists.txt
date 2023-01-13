cmake_minimum_required(VERSION 3.2)

set(CMAKE_CXX_STANDARD 17)

# Name of the bot
project(CRaB)

include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG master
)
FetchContent_MakeAvailable(fmt)

add_subdirectory(libs)

file(GLOB_RECURSE BOT_SRC ${PROJECT_SOURCE_DIR}/src/*.cpp)
add_executable(pokerbot ${BOT_SRC})
target_include_directories(pokerbot PUBLIC ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(pokerbot skeleton fmt::fmt)
