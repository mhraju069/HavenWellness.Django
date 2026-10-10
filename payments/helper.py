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

        booking_type_display = 'Lunchroom'
        if hasattr(booking, 'get_sauna_type_display'):
            booking_type_display = booking.get_sauna_type_display()
        elif hasattr(booking, 'sauna_type'):
            booking_type_display = str(booking.sauna_type).title()

        time_slot_display = ""
        if hasattr(booking, 'get_time_slot_display'):
            time_slot_display = booking.get_time_slot_display()
        elif hasattr(booking, 'time_slot'):
            time_slot_display = str(booking.time_slot)

        context = {
            'booking': booking,
            'booking_type_display': booking_type_display,
            'time_slot_display': time_slot_display,
        }

        html_message = render_to_string('email/booking_confirmation_email.html', context)

        time_slot_str = ""
        if hasattr(booking, 'time_slot'):
            time_slot_str = f" ({getattr(booking, 'get_time_slot_display', lambda: booking.time_slot)()})"

        total_paid_str = f"\nTotal Paid: €{booking.total_price}" if hasattr(booking, 'total_price') else ""

        plain_message = (
            f"Hello {booking.name},\n\n"
            f"Your booking has been confirmed!\n"
            f"Booking ID: {booking.booking_id}\n"
            f"Type: {booking_type_display}\n"
            f"Date: {booking.booking_date}\n"
            f"Time: {booking.booking_time}{time_slot_str}"
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
