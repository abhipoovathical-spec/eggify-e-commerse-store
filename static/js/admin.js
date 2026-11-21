// EGGIFY Admin JS
document.addEventListener('DOMContentLoaded', function() {
    // Admin Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const adminSidebar = document.getElementById('admin-sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');

    if (sidebarToggle && adminSidebar) {
        sidebarToggle.addEventListener('click', () => {
            adminSidebar.classList.toggle('-translate-x-full');
            if (sidebarOverlay) sidebarOverlay.classList.toggle('hidden');
        });
    }

    if (sidebarOverlay && adminSidebar) {
        sidebarOverlay.addEventListener('click', () => {
            adminSidebar.classList.add('-translate-x-full');
            sidebarOverlay.classList.add('hidden');
        });
    }

    // Initialize Tooltips / modals
    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('hidden');
    };

    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('hidden');
    };
});

// View order details in modal
function viewOrderDetails(orderId) {
    fetch(`/admin/orders/${orderId}/view`)
    .then(r => r.json())
    .then(res => {
        if (res.status === 'success') {
            const o = res.order;
            const content = document.getElementById('order-detail-content');
            if (!content) return;

            content.innerHTML = `
                <div class="space-y-4">
                    <div class="flex items-center justify-between pb-3 border-b border-gray-200">
                        <div>
                            <span class="text-xs uppercase font-bold text-gray-500">Order Code</span>
                            <h4 class="text-xl font-extrabold text-gray-900 font-outfit">#${o.code}</h4>
                        </div>
                        <span class="px-3 py-1 rounded-full text-xs font-bold ${o.payment_status === 'PAID' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
                            ${o.payment_status}
                        </span>
                    </div>

                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <p class="text-gray-500 text-xs">Customer Name</p>
                            <p class="font-semibold text-gray-800">${o.customer_name}</p>
                        </div>
                        <div>
                            <p class="text-gray-500 text-xs">Mobile Number</p>
                            <p class="font-semibold text-gray-800">${o.customer_phone}</p>
                        </div>
                        <div>
                            <p class="text-gray-500 text-xs">Pickup Gym</p>
                            <p class="font-semibold text-gray-800">${o.gym_name}</p>
                        </div>
                        <div>
                            <p class="text-gray-500 text-xs">Fulfillment Date</p>
                            <p class="font-semibold text-gray-800">${o.preferred_date} (${o.preferred_time_slot})</p>
                        </div>
                    </div>

                    <div class="bg-amber-50 p-3 rounded-xl border border-amber-200">
                        <div class="flex justify-between items-center text-sm font-semibold text-amber-900">
                            <span>Quantity: ${o.egg_quantity} Fresh Eggs</span>
                            <span>Total: ₹${o.total_amount.toFixed(2)}</span>
                        </div>
                        <div class="text-xs text-amber-700 mt-1">
                            Rate: ₹${o.price_per_egg.toFixed(2)}/egg | Delivery: ₹${o.delivery_charge.toFixed(2)} | UTR: ${o.transaction_id}
                        </div>
                    </div>

                    ${o.delivery_address ? `
                    <div class="text-sm bg-gray-50 p-3 rounded-lg border border-gray-200">
                        <span class="text-xs font-bold text-gray-500 uppercase">Home Delivery Address</span>
                        <p class="text-gray-700 mt-1">${o.delivery_address}</p>
                    </div>` : ''}

                    ${o.customer_notes ? `
                    <div class="text-sm bg-gray-50 p-2.5 rounded-lg">
                        <span class="text-xs font-bold text-gray-500">Customer Note:</span>
                        <p class="text-gray-700 text-xs italic mt-0.5">"${o.customer_notes}"</p>
                    </div>` : ''}

                    <div class="pt-3 border-t border-gray-200">
                        <p class="text-xs font-bold text-gray-600 mb-2">1-Click WhatsApp Notification:</p>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <a href="${res.whatsapp.ready_url}" target="_blank" class="text-center px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition">
                                <i class="fab fa-whatsapp mr-1"></i> Send Ready for Pickup
                            </a>
                            <a href="${res.whatsapp.confirmation_url}" target="_blank" class="text-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition">
                                <i class="fab fa-whatsapp mr-1"></i> Send Confirmation
                            </a>
                        </div>
                    </div>
                </div>
            `;
            openModal('orderDetailModal');
        }
    });
}
