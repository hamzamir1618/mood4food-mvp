import { useState } from 'react';

export default function RestaurantsSection({ fulfillment, dish }) {
  const restaurants = fulfillment?.restaurants || [];
  if (!restaurants.length) return null;

  return (
    <div className="restaurants-section" id="restaurants-section" style={{ display: 'none' }}>
      <h2><span>🛵</span> Order Nearby</h2>
      <div className="restaurants-grid" id="restaurants-container">
        {restaurants.map((r, i) => (
          <RestaurantCard key={i} restaurant={r} dish={dish} />
        ))}
      </div>
    </div>
  );
}

function RestaurantCard({ restaurant: r, dish }) {
  const dishName = dish?.name || 'Dish';
  const dishPrice = dish?.price_pkr || 0;
  const distanceStr = r.distance_km !== null && r.distance_km !== undefined
    ? ` • ${r.distance_km.toFixed(1)} km away`
    : '';

  return (
    <div className="restaurant-card">
      <div className="restaurant-name">{r.name}</div>
      <div className="restaurant-address" style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
        {r.address || ''}{distanceStr}
      </div>
      <div className="restaurant-dish-offer" style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>
        {dishName}, Rs. {dishPrice}
      </div>
      <div className="restaurant-meta">
        <span>⏱️ {r.delivery_time || '-'}</span>
        <span>🛵 +Rs. {r.delivery_fee || 0} delivery fee</span>
      </div>
      <button className="restaurant-order-btn">Place Order</button>
    </div>
  );
}
