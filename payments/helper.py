from django.conf import settings
from django.urls import reverse
from djstripe.models import Customer, PaymentIntent, Session


def create_checkout_session(request, booking, payment, price, customer=None):
    if booking is None or price is None or payment is None:
        raise Exception("Required data for Checkout Session is missing")

    session_data = {
        "payment_method_types": ["card"],
        "mode": "payment",
        "line_items": [
            {
                "price_data": {
                    "currency": "eur",
                    "unit_amount": int(price * 100),
                    "product_data": {
                        "name": "Confirm your booking",
                    },
                },
                "quantity": 1,
            }
        ],
        "success_url": request.build_absolute_uri(reverse("payment_success")),
        "cancel_url": request.build_absolute_uri(reverse("payment_cancel")),
        "metadata": {
            "booking": str(booking),
            "payment": str(payment)
        },
    }

    if customer:
        session_data["customer"] = customer.id if hasattr(customer, "id") else str(customer)

    session_obj = Session._api_create(**session_data)
    Session.sync_from_stripe_data(session_obj)
    return getattr(session_obj, 'url', '')


def create_payment_intent_data(request, booking, payment, price, customer_email, method="web"):
    if booking is None or price is None or payment is None:
        raise Exception("Required payment data (booking, price, or payment ID) is missing")

    customer = Customer.objects.filter(email=customer_email).first()
    if not customer:
        cust_obj = Customer._api_create(email=customer_email)
        customer = Customer.sync_from_stripe_data(cust_obj)

    if method == "web":
        return create_checkout_session(request, booking, payment, price, customer=customer)

    payment_intent_obj = PaymentIntent._api_create(
        amount=int(price * 100),
        currency='eur',
        customer=customer.id,
        automatic_payment_methods={'enabled': True},
        metadata={
            "booking": str(booking),
            "payment": str(payment)
        }
    )
    PaymentIntent.sync_from_stripe_data(payment_intent_obj)

    return {
        "paymentIntent": getattr(payment_intent_obj, 'client_secret', ''),
        "customer": customer.id,
        "publishableKey": getattr(settings, 'STRIPE_PUBLISHABLE_KEY', '') or getattr(settings, 'STRIPE_TEST_PUBLIC_KEY', '')
    }


def send_booking_confirmation_email(booking):
    """
    Sends a beautiful confirmation email with booking details (ID, date, time, total)
    once a booking payment is confirmed.
    """
    if not booking or not booking.email:
        return {"status": False, "log": "Booking email not found."}

    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    try:
        subject = f"Booking Confirmed! Reference: {booking.booking_id} • Haven Wellness"
        email_from = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        recipient_list = [booking.email]

        if hasattr(booking, 'activity') and booking.activity:
            booking_type_display = f"Activity: {booking.activity.title}"
            booking_date_display = str(booking.activity.date) if booking.activity.date else "Scheduled Date"
            booking_time_display = f"{booking.activity.open_time} - {booking.activity.close_time}" if booking.activity.open_time else "Scheduled Time"
            time_slot_display = ""
        elif hasattr(booking, 'sauna_type'):
            booking_type_display = booking.get_sauna_type_display() if hasattr(booking, 'get_sauna_type_display') else str(booking.sauna_type).title()
            booking_date_display = str(booking.booking_date)
            booking_time_display = str(booking.booking_time)
            time_slot_display = booking.get_time_slot_display() if hasattr(booking, 'get_time_slot_display') else str(getattr(booking, 'time_slot', ''))
        elif hasattr(booking, 'booked_services_ids') or (hasattr(booking, 'booking_id') and booking.booking_id.startswith('PKG-')):
            booking_type_display = 'Package Booking' if not getattr(booking, 'is_custom', False) else 'Custom Package Request'
            booking_date_display = str(booking.date)
            booking_time_display = "Scheduled Services"
            time_slot_display = ""
            
            from bookings.models import SaunaBooking, LunchroomBooking, ActivityBooking

            # Extract human-readable summary of included sub-services with time & full title
            services_summary = []
            raw_ids = getattr(booking, 'booked_services_ids', []) or []
            for item in raw_ids:
                if isinstance(item, dict):
                    for service_type, ref_id in item.items():
                        # Map service_type key to proper full name
                        if service_type in ['private', 'private_sauna']:
                            service_title = 'Private Sauna'
                        elif service_type in ['shared', 'shared_sauna']:
                            service_title = 'Shared Sauna'
                        elif service_type in ['saltroom', 'salt_room']:
                            service_title = 'Salt Room'
                        elif service_type == 'lunchroom':
                            service_title = 'Lunchroom'
                        elif service_type == 'activity':
                            service_title = 'Activity'
                        else:
                            service_title = str(service_type).replace('_', ' ').title()

                        # Lookup time from DB object
                        time_str = ""
                        if ref_id.startswith(('PS-', 'SS-', 'SB-')):
                            s_obj = SaunaBooking.objects.filter(booking_id=ref_id).first()
                            if s_obj and s_obj.booking_time:
                                time_str = f" @ {s_obj.booking_time.strftime('%H:%M')}"
                        elif ref_id.startswith('SR-'):
                            from bookings.models import SaltRoomBooking
                            sr_obj = SaltRoomBooking.objects.filter(booking_id=ref_id).first()
                            if sr_obj and sr_obj.start_time:
                                end_str = f" - {sr_obj.end_time.strftime('%H:%M')}" if sr_obj.end_time else ""
                                time_str = f" @ {sr_obj.start_time.strftime('%H:%M')}{end_str}"
                        elif ref_id.startswith('LR-'):
                            l_obj = LunchroomBooking.objects.filter(booking_id=ref_id).first()
                            if l_obj and l_obj.booking_time:
                                time_str = f" @ {l_obj.booking_time.strftime('%H:%M')}"
                        elif ref_id.startswith('ACT-'):
                            a_obj = ActivityBooking.objects.filter(booking_id=ref_id).first()
                            if a_obj and a_obj.activity and a_obj.activity.open_time:
                                time_str = f" @ {a_obj.activity.open_time.strftime('%H:%M')}"

                        services_summary.append(f"{service_title} (ID: {ref_id}{time_str})")
                elif isinstance(item, str):
                    services_summary.append(item)

            if services_summary:
                booking_time_display = ", ".join(services_summary)
        elif hasattr(booking, 'purchase_type'):
            if booking.purchase_type == 'session_pass':
                pass_name = booking.session_pass.name if booking.session_pass else "Session Pass"
                booking_type_display = f"Session Pass: {pass_name}"
            else:
                plan_name = booking.subscription_plan.name if booking.subscription_plan else "Subscription Plan"
                booking_type_display = f"Subscription: {plan_name}"
            booking_date_display = booking.created_at.strftime('%Y-%m-%d') if booking.created_at else ""
            booking_time_display = booking.created_at.strftime('%H:%M') if booking.created_at else ""
            time_slot_display = ""
        elif hasattr(booking, 'guests') and hasattr(booking, 'start_time'):
            booking_type_display = 'Event Booking'
            booking_date_display = str(booking.date)
            booking_time_display = f"{booking.start_time} - {booking.end_time}"
            time_slot_display = ""
        elif hasattr(booking, 'start_time') and hasattr(booking, 'date') and (hasattr(booking, 'used_pass') or booking.booking_id.startswith('SR-')):
            booking_type_display = 'Saltroom Session'
            booking_date_display = str(booking.date)
            booking_time_display = f"{booking.start_time} - {booking.end_time}"
            time_slot_display = "Saltroom"
        else:
            booking_type_display = 'Lunchroom'
            booking_date_display = str(getattr(booking, 'booking_date', ''))
            booking_time_display = str(getattr(booking, 'booking_time', ''))
            time_slot_display = ""

        guests_count_display = getattr(booking, 'guests', None) or getattr(booking, 'capacity', 1)

        is_paid_booking = hasattr(booking, 'total_price') and float(getattr(booking, 'total_price', 0)) > 0

        context = {
            'booking': booking,
            'booking_type_display': booking_type_display,
            'booking_date_display': booking_date_display,
            'booking_time_display': booking_time_display,
            'time_slot_display': time_slot_display,
            'guests_count_display': guests_count_display,
            'is_paid_booking': is_paid_booking,
        }

        html_message = render_to_string('email/booking_confirmation_email.html', context)

        time_slot_str = f" ({time_slot_display})" if time_slot_display else ""
        total_paid_str = f"\nTotal Paid: €{booking.total_price}" if hasattr(booking, 'total_price') else ""

        plain_message = (
            f"Hello {booking.name},\n\n"
            f"Your booking has been confirmed!\n"
            f"Booking ID: {booking.booking_id}\n"
            f"Type: {booking_type_display}\n"
            f"Date: {booking_date_display}\n"
            f"Time: {booking_time_display}{time_slot_str}"
            f"{total_paid_str}\n\n"
            f"Thank you for choosing Haven Wellness!"
        )

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=email_from,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        return {"status": True, "log": f"Confirmation email sent to {booking.email}"}
    except Exception as e:
        print(f"Failed to send booking confirmation email: {e}")
        return {"status": False, "log": str(e)}
