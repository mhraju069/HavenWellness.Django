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
        else:
            booking_type_display = 'Lunchroom'
            booking_date_display = str(getattr(booking, 'booking_date', ''))
            booking_time_display = str(getattr(booking, 'booking_time', ''))
            time_slot_display = ""

        context = {
            'booking': booking,
            'booking_type_display': booking_type_display,
            'booking_date_display': booking_date_display,
            'booking_time_display': booking_time_display,
            'time_slot_display': time_slot_display,
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
