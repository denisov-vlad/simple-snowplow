FROM clickhouse/clickhouse-server:23.3.6.7-alpine

RUN apk update && apk add xmlstarlet \
    && xmlstarlet ed --inplace --subnode '/clickhouse/profiles/default' --type elem \
    -n allow_experimental_object_type -v 1 /etc/clickhouse-server/users.xml \
    && apk del xmlstarlet
