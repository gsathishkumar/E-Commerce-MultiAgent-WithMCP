cd ./../product-rag-api
docker build -t ecommerce/product_rag_api:latest .
cd ./../refund-rag-api
docker build -t ecommerce/refund_rag_api:latest .
cd ./../order-api
docker build -t ecommerce/order_mongo_app:latest .
cd ./../refund-api
docker build -t ecommerce/refund_mongo_app:latest .
cd ./../ecommerce-support
docker build -t ecommerce/ecommerce_support_app:latest .
cd ./../common-files

