cd ./../product-rag-api
docker build -t ecommerce/product_rag_api:with-mcp .
cd ./../refund-rag-api
docker build -t ecommerce/refund_rag_api:with-mcp .
cd ./../order-api
docker build -t ecommerce/order_mongo_app:with-mcp .
cd ./../refund-api
docker build -t ecommerce/refund_mongo_app:with-mcp .
cd ./../ecommerce-support
docker build -t ecommerce/ecommerce_support_app:with-mcp .
cd ./../common-files

