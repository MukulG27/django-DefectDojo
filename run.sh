#!/bin/bash

./dc-down.sh
./dc-build.sh
./dc-up-d.sh postgres-redis
