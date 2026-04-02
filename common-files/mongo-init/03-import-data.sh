#!/bin/bash
echo "Waiting for MongoDB..."
sleep 5

echo "Importing data with ecommerce_user..."

mongoimport \
  --host localhost \
  --port 27017 \
  --username ecommerce_user \
  --password ecommerce_pwd \
  --authenticationDatabase ecommerce_db \
  --db ecommerce_db \
  --collection orders \
  --file /docker-entrypoint-initdb.d/orders.json \
  --jsonArray

mongoimport \
  --host localhost \
  --port 27017 \
  --username ecommerce_user \
  --password ecommerce_pwd \
  --authenticationDatabase ecommerce_db \
  --db ecommerce_db \
  --collection refunds \
  --file /docker-entrypoint-initdb.d/refunds.json \
  --jsonArray

echo "Import completed!"