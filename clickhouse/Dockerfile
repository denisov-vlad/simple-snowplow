FROM clickhouse/clickhouse-server:23.2.4.12

RUN apt-get update && apt-get install -y xmlstarlet \
    && xmlstarlet ed --inplace --subnode '/clickhouse/profiles/default' --type elem \
    -n allow_experimental_object_type -v 1 /etc/clickhouse-server/users.xml \
    && apt-get remove -y xmlstarlet
