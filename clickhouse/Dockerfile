FROM clickhouse/clickhouse-server:22.11.2

RUN apt-get update && apt-get install -y xmlstarlet \
    && xmlstarlet ed --inplace --subnode '/clickhouse/profiles/default' --type elem \
    -n allow_experimental_object_type -v 1 /etc/clickhouse-server/users.xml \
    && apt-get remove -y xmlstarlet
