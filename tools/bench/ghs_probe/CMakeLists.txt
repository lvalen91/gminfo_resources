cmake_minimum_required(VERSION 3.18.1)
project("ghsprobe")

add_library(ghsprobe SHARED ghs_probe.c)
target_link_libraries(ghsprobe log)
