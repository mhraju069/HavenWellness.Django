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


def get_client_language(booking, lang=None):
    """
    Determine recipient client language ('en', 'nl', 'de').
    Checks:
    1. Explicit lang parameter (e.g. 'nl', 'de', 'en')
    2. Booking's linked user language preference
    3. Account language matching booking email
    4. Active Django translation language
    5. Fallback: 'en'
    """
    if lang:
        l = str(lang).lower().strip()
        if 'nl' in l: return 'nl'
        if 'de' in l: return 'de'
        if 'en' in l: return 'en'

    user = getattr(booking, 'user', None)
    if user and getattr(user, 'language', None):
        u_lang = str(user.language).lower().strip()
        if u_lang in ['nl', 'de', 'en']:
            return u_lang

    b_email = getattr(booking, 'email', None)
    if b_email:
        from accounts.models import User
        matched_user = User.objects.filter(email__iexact=str(b_email).strip()).first()
        if matched_user and getattr(matched_user, 'language', None):
            u_lang = str(matched_user.language).lower().strip()
            if u_lang in ['nl', 'de', 'en']:
                return u_lang

    from django.utils import translation
    curr = str(translation.get_language() or '').lower()
    if 'nl' in curr: return 'nl'
    if 'de' in curr: return 'de'
    return 'en'


def send_booking_confirmation_email(booking, lang=None):
    """
    Sends a beautiful confirmation email with booking details (ID, date, time, total)
    once a booking payment is confirmed or an event enquiry is submitted.
    """
    if not booking or not booking.email:
        return {"status": False, "log": "Booking email not found."}

    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    try:
        client_lang = get_client_language(booking, lang=lang)
        booking_id = getattr(booking, 'booking_id', getattr(booking, 'purchase_id', ''))
        subject = f"Booking Confirmed! Reference: {booking_id} • Haven Wellness"
        email_from = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
        recipient_list = [booking.email]

        email_category = 'booking'  # 'booking', 'purchase', 'package', or 'event'
        sub_services_list = []
        purchase_info = {}

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
            email_category = 'package'
            is_custom = getattr(booking, 'is_custom', False)
            booking_type_display = 'Custom Package Request' if is_custom else 'Package Experience'
            booking_date_display = str(booking.date)
            booking_time_display = "Included Package Services"
            time_slot_display = ""
            
            from bookings.models import SaunaBooking, LunchroomBooking, ActivityBooking, SaltRoomBooking

            # Extract human-readable summary of included sub-services with time & full title
            services_summary = []
            raw_ids = getattr(booking, 'booked_services_ids', []) or []
            for item in raw_ids:
                if isinstance(item, dict):
                    for service_type, ref_id in item.items():
                        if service_type in ['private', 'private_sauna']:
                            service_title = 'VIP Sauna'
                        elif service_type in ['shared', 'shared_sauna']:
                            service_title = 'Sauna'
                        elif service_type in ['saltroom', 'salt_room']:
                            service_title = 'Salt Room'
                        elif service_type == 'lunchroom':
                            service_title = 'Lunchroom'
                        elif service_type == 'activity':
                            service_title = 'Activity'
                        else:
                            service_title = str(service_type).replace('_', ' ').title()

                        time_str = ""
                        if ref_id.startswith(('PS-', 'SS-', 'SB-')):
                            s_obj = SaunaBooking.objects.filter(booking_id=ref_id).first()
                            if s_obj and s_obj.booking_time:
                                time_str = f" @ {s_obj.booking_time.strftime('%H:%M')}"
                        elif ref_id.startswith('SR-'):
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

                        desc = f"{service_title} ({ref_id}{time_str})"
                        services_summary.append(desc)
                        sub_services_list.append(desc)
                elif isinstance(item, str):
                    services_summary.append(item)
                    sub_services_list.append(item)

            if services_summary:
                booking_time_display = ", ".join(services_summary)
            elif is_custom and getattr(booking, 'service_names', None):
                sub_services_list = list(booking.service_names)
                booking_time_display = ", ".join(sub_services_list)

        elif hasattr(booking, 'purchase_type'):
            email_category = 'purchase'
            if booking.purchase_type == 'session_pass':
                pass_name = booking.session_pass.name if booking.session_pass else "Session Pass"
                booking_type_display = f"{pass_name}"
                purchase_info = {
                    'total_sessions': booking.total_sessions or 10,
                    'remaining_sessions': booking.remaining_sessions if booking.remaining_sessions is not None else 10,
                    'validity': "Unlimited",
                }
            else:
                plan_name = booking.subscription_plan.name if booking.subscription_plan else "Subscription Plan"
                booking_type_display = f"{plan_name}"
                validity_str = "Ongoing"
                if booking.end_date:
                    validity_str = f"Until {booking.end_date.strftime('%Y-%m-%d')}"
                purchase_info = {
                    'plan_type': getattr(booking.subscription_plan, 'plan_type', 'weekly'),
                    'sessions_per_week': booking.sessions_per_week or 1,
                    'validity': validity_str,
                }
            booking_date_display = booking.created_at.strftime('%Y-%m-%d') if booking.created_at else ""
            booking_time_display = booking.created_at.strftime('%H:%M') if booking.created_at else ""
            time_slot_display = ""
        elif hasattr(booking, 'guests') and hasattr(booking, 'start_time') and not hasattr(booking, 'booked_services_ids') and getattr(booking, 'booking_id', '').startswith('EVNT-'):
            email_category = 'event'
            booking_type_display = 'Event Booking'
            booking_date_display = str(booking.date)
            booking_time_display = f"{booking.start_time} - {booking.end_time}"
            time_slot_display = ""
        elif hasattr(booking, 'start_time') and hasattr(booking, 'date') and (hasattr(booking, 'used_pass') or booking.booking_id.startswith('SR-')):
            booking_type_display = 'Saltroom Session'
            booking_date_display = str(booking.date)
            booking_time_display = f"{booking.start_time} - {booking.end_time}"
            time_slot_display = "Saltroom"
            if getattr(booking, 'payment_status', '') == 'paid_with_package':
                booking_type_display = 'Saltroom (Included in Package)'
            elif getattr(booking, 'used_pass', False):
                booking_type_display = 'Saltroom Session (Paid with Pass)'
            elif getattr(booking, 'used_subscription', False):
                booking_type_display = 'Saltroom Session (Subscription)'
        else:
            booking_type_display = 'Lunchroom'
            booking_date_display = str(getattr(booking, 'booking_date', ''))
            booking_time_display = str(getattr(booking, 'booking_time', ''))
            time_slot_display = ""

        # Check if booking is paid with package
        is_paid_with_package = getattr(booking, 'payment_status', '') == 'paid_with_package' or getattr(booking, 'status', '') == 'confirmed_with_package'

        guests_count_display = getattr(booking, 'guests', None) or getattr(booking, 'capacity', 1)
        is_paid_booking = hasattr(booking, 'total_price') and float(getattr(booking, 'total_price', 0)) > 0

        # Adjust subject line based on category
        if email_category == 'event':
            if client_lang == 'nl':
                subject = f"Aanvraag ontvangen! Referentie: {booking.booking_id} • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Anfrage erhalten! Referenz: {booking.booking_id} • Heaven on Earth"
            else:
                subject = f"Enquiry Received! Reference: {booking.booking_id} • Heaven on Earth"
        elif email_category == 'purchase':
            if getattr(booking, 'purchase_type', '') == 'session_pass':
                subject = f"Pass Confirmed! Reference: {booking.purchase_id} • Haven Wellness"
            else:
                subject = f"Subscription Confirmed! Reference: {booking.purchase_id} • Haven Wellness"
        elif email_category == 'package':
            subject = f"Package Booking Confirmed! Reference: {booking.booking_id} • Haven Wellness"
        elif is_paid_with_package:
            subject = f"Package Reservation Confirmed! Reference: {booking.booking_id} • Haven Wellness"
        else:
            subject = f"Booking Confirmed! Reference: {booking.booking_id} • Haven Wellness"

        context = {
            'booking': booking,
            'name': getattr(booking, 'name', 'Guest'),
            'lang': client_lang,
            'email_category': email_category,
            'is_paid_with_package': is_paid_with_package,
            'sub_services_list': sub_services_list,
            'purchase_info': purchase_info,
            'booking_type_display': booking_type_display,
            'booking_date_display': booking_date_display,
            'booking_time_display': booking_time_display,
            'time_slot_display': time_slot_display,
            'guests_count_display': guests_count_display,
            'is_paid_booking': is_paid_booking,
        }

        if email_category == 'event':
            html_message = render_to_string('email/event_confirmation_email.html', context)
        else:
            html_message = render_to_string('email/booking_confirmation_email.html', context)

        time_slot_str = f" ({time_slot_display})" if time_slot_display else ""
        total_paid_str = f"\nTotal Paid: €{booking.total_price}" if hasattr(booking, 'total_price') else ""

        if email_category == 'event':
            if client_lang == 'nl':
                plain_message = (
                    f"Beste {booking.name},\n\n"
                    f"Wat leuk dat je Heaven on Earth overweegt voor jouw evenement! We hebben je aanvraag goed ontvangen.\n\n"
                    f"Onze eventplanningafdeling controleert eerst of de gewenste datum beschikbaar is. Is dat het geval, dan nemen we contact met je op om je wensen te bespreken en samen naar de mogelijkheden te kijken. We maken met plezier een offerte op maat.\n\n"
                    f"Je aanvraag is nog geen definitieve reservering. De datum is pas bevestigd zodra we alles hebben afgestemd en je akkoord bent met de offerte.\n\n"
                    f"We kijken ernaar uit om samen met je iets moois van jouw evenement te maken!\n\n"
                    f"Referentienummer: {booking.booking_id}\n"
                    f"Datum: {booking_date_display}\n"
                    f"Tijd: {booking_time_display}\n"
                    f"Aantal gasten: {guests_count_display}\n\n"
                    f"Warme groet,\n\n"
                    f"Team Heaven on Earth"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Hallo {booking.name},\n\n"
                    f"Wie schön, dass du Heaven on Earth für deine Veranstaltung in Betracht ziehst! Wir haben deine Anfrage erhalten.\n\n"
                    f"Unser Eventplanungsteam prüft zunächst, ob dein Wunschtermin noch verfügbar ist. Wenn das der Fall ist, melden wir uns bei dir, um deine Wünsche zu besprechen und gemeinsam die Möglichkeiten anzuschauen. Gerne erstellen wir ein individuelles Angebot für dich.\n\n"
                    f"Deine Anfrage ist noch keine verbindliche Reservierung. Der Termin ist erst bestätigt, wenn wir alles besprochen haben und du dem Angebot zugestimmt hast.\n\n"
                    f"Wir freuen uns darauf, gemeinsam etwas Schönes für deine Veranstaltung zu gestalten!\n\n"
                    f"Referenz-ID: {booking.booking_id}\n"
                    f"Datum: {booking_date_display}\n"
                    f"Uhrzeit: {booking_time_display}\n"
                    f"Gästeanzahl: {guests_count_display}\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Dein Team von Heaven on Earth"
                )
            else:
                plain_message = (
                    f"Hi {booking.name},\n\n"
                    f"How lovely that you’re considering Heaven on Earth for your event! We’ve received your enquiry.\n\n"
                    f"Our event planning team will first check whether your preferred date is available. If it is, we’ll get in touch to discuss your wishes and explore the possibilities together. We’ll be happy to put together a personalised quote for you.\n\n"
                    f"Your enquiry is not yet a confirmed reservation. The date will only be confirmed once we’ve discussed everything and you’ve agreed to the quote.\n\n"
                    f"We look forward to creating something special for your event together!\n\n"
                    f"Reference ID: {booking.booking_id}\n"
                    f"Date: {booking_date_display}\n"
                    f"Time: {booking_time_display}\n"
                    f"Number of Guests: {guests_count_display}\n\n"
                    f"Warm regards,\n\n"
                    f"The Heaven on Earth Team"
                )
        elif email_category == 'purchase':
            intro_plain = "Thank you for your purchase. Your pass/subscription has been activated and linked to your account."
        elif email_category == 'package':
            intro_plain = "Thank you for booking with us. Your package experience has been confirmed."
        elif is_paid_with_package:
            intro_plain = "Your reservation has been confirmed as part of your package experience."
        else:
            intro_plain = "Thank you for choosing Haven Wellness! Your booking has been confirmed."

        plain_message = (
            f"Hello {booking.name},\n\n"
            f"{intro_plain}\n\n"
            f"Reference ID: {booking.booking_id}\n"
            f"Type: {booking_type_display}\n"
            f"Date: {booking_date_display}\n"
            f"Time: {booking_time_display}{time_slot_str}"
            f"{total_paid_str}\n\n"
            f"Haven Wellness\nsupport@havenwellness.com"
        )

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=email_from,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )

        # Trigger real-time notifications (User & Admin)
        user = getattr(booking, 'user', None)
        b_id = getattr(booking, 'booking_id', getattr(booking, 'purchase_id', ''))
        booking_url = f"/bookings/{b_id}" if b_id else "/bookings"
        guest_name = getattr(booking, 'name', 'Guest')
        total_price = getattr(booking, 'total_price', getattr(booking, 'price', None))

        # 1. Notify User (if linked user)
        if user:
            try:
                from notifications.views import notify_user
                notify_user(
                    user=user,
                    title="Booking Confirmed!",
                    body=f"Your booking ({booking_type_display}) with reference {b_id} has been confirmed.",
                    notification_type='booking',
                    link=booking_url,
                    data={
                        "booking_id": b_id,
                        "type": booking_type_display,
                        "date": booking_date_display,
                        "time": booking_time_display,
                        "link": booking_url,
                    }
                )
            except Exception as notify_err:
                print(f"Failed to dispatch user real-time notification: {notify_err}")

        # 2. Notify Admins about new confirmed booking / purchase
        try:
            from notifications.views import notify_admins
            admin_link = f"/admin/bookings/{b_id}" if b_id else "/admin/dashboard"
            price_text = f" (€{total_price})" if total_price is not None else ""
            notify_admins(
                title=f"New Booking: {booking_type_display}",
                body=f"{guest_name} confirmed a booking ({b_id}){price_text} on {booking_date_display}.",
                notification_type='booking',
                link=admin_link,
                data={
                    "booking_id": b_id,
                    "customer_name": guest_name,
                    "type": booking_type_display,
                    "date": booking_date_display,
                    "time": booking_time_display,
                    "total_price": str(total_price) if total_price else "0",
                    "link": admin_link,
                }
            )
        except Exception as admin_err:
            print(f"Failed to dispatch admin real-time notification: {admin_err}")

        return {"status": True, "log": f"Confirmation email sent to {booking.email}"}
    except Exception as e:
        print(f"Failed to send booking confirmation email: {e}")
        return {"status": False, "log": str(e)}
