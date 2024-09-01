FROM clickhouse/clickhouse-server:24.8.2.3-alpine

RUN apk update && apk add xmlstarlet \
    && xmlstarlet ed --inplace --subnode '/clickhouse/profiles/default' --type elem \
    -n allow_experimental_json_type -v 1 /etc/clickhouse-server/users.xml \
    && apk del xmlstarlet
