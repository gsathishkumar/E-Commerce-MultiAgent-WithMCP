db = db.getSiblingDB('ecommerce_db');

// Create empty collections
db.createCollection('orders');
db.createCollection('refunds');

print('Collections created successfully!');
