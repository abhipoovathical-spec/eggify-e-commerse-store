// EGGIFY Customer JS
document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const flashAlerts = document.querySelectorAll('.flash-alert');
    flashAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });
});

// Price calculation helper function for order page
function updateLiveOrderCalculation() {
    const qtyInput = document.getElementById('egg_quantity');
    if (!qtyInput) return;

    let quantity = parseInt(qtyInput.value) || 12;
    if (quantity < 6) quantity = 6;
    if (quantity > 300) quantity = 300;

    const deliveryTypeRadio = document.querySelector('input[name="delivery_type"]:checked');
    const deliveryType = deliveryTypeRadio ? deliveryTypeRadio.value : 'gym_pickup';
    const distanceKm = parseFloat(document.getElementById('distance_km')?.value || 0.0);

    fetch('/api/calc-price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            quantity: quantity,
            delivery_type: deliveryType,
            distance_km: distanceKm
        })
    })
    .then(res => res.json())
    .then(res => {
        if (res.status === 'success') {
            const data = res.data;
            const subtotalEl = document.getElementById('calc-subtotal');
            const rateEl = document.getElementById('calc-rate');
            const deliveryEl = document.getElementById('calc-delivery');
            const totalEl = document.getElementById('calc-total');
            const submitBtnPrice = document.getElementById('btn-total-amount');

            if (subtotalEl) subtotalEl.textContent = '₹' + data.eggs_subtotal.toFixed(2);
            if (rateEl) rateEl.textContent = '₹' + data.price_per_egg.toFixed(2) + ' / egg';
            if (deliveryEl) deliveryEl.textContent = data.delivery_charge > 0 ? '₹' + data.delivery_charge.toFixed(2) : 'FREE (Gym Pick)';
            if (totalEl) totalEl.textContent = '₹' + data.total_amount.toFixed(2);
            if (submitBtnPrice) submitBtnPrice.textContent = '₹' + data.total_amount.toFixed(2);
        }
    })
    .catch(err => console.error('Calculation error:', err));
}
