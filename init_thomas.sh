#!/bin/bash

# This script initializes the MesLibrairies database with a set of authors.
authors=(
    "1949874:stephen-king"
    "2275033:christopher-ruocchio"
    "1238357:guillaume-meurice"
    "2376903:salome-saque"
    "2324837:salome-saque"
    "2080981:becky-chambers"
    "2247267:alain-damasio"
    "192180:raymond-e-feist"
    "827784:maxime-chattam"
    "747318:david-gemmell"
    "683764:terry-goodkind"
    "684032:robin-hobb"
    "1015327:karine-giebel"
    "75742:frank-margerin"
    "2373210:brian-mcclellan"
    "2036866:clement-bouhelier"
    "2012893:shaun-hamill"
    "64332:ken-follett"
    "2024723:jean-luc-deparis"
    "1979552:robert-jackson-bennett"
    "1590622:camille-leboulanger"
    "826537:jean-marc-jancovici"
    "981749:michel-robert"
    "1917465:jean-hegland"
)

for entry in "${authors[@]}"; do
    IFS=':' read -r id slug <<< "$entry"
    python3 main.py add --author_id="$id" --author_slug="$slug"
done