#!/bin/bash
# Creates the three additional databases on first boot.
# cloudia_brand_dna is already created by POSTGRES_DB in the compose file.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE cloudia_campaigns;
    CREATE DATABASE cloudia_ads;
    CREATE DATABASE cloudia_webdev;
EOSQL
