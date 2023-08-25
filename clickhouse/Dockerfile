FROM clickhouse/clickhouse-server:23.7.4.5-alpine

RUN apk update && apk add xmlstarlet \
    && xmlstarlet ed --inplace --subnode '/clickhouse/profiles/default' --type elem \
    -n allow_experimental_object_type -v 1 /etc/clickhouse-server/users.xml \
    && apk del xmlstarlet
