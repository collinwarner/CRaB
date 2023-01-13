#!/bin/bash

mkdir -p build
cd build
cmake -DBOOST_ROOT=/home/software/boost/1.70.0 -D CMAKE_C_COMPILER=/home/software/gcc/8.3.0/bin/gcc -DCMAKE_BUILD_TYPE=Debug ..
make
cd ..
