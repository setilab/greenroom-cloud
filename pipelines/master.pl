#!/bin/bash

PIPELINES=`ls *.pl | grep -v master`

for PL in $PIPELINES; do
    ./$PL
done
