db = db.getSiblingDB('ecommerce_db');

db.createUser({
  user: 'ecommerce_user',
  pwd: 'ecommerce_pwd',
  roles: [
    {
      role: 'readWrite',
      db: 'ecommerce_db',
    },
  ],
});
