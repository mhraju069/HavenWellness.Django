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

        email_category = 'booking'  # 'activity', 'lunchroom', 'event', 'package', 'vip_sauna', 'sauna', 'saltroom', 'purchase'
        sub_services_list = []
        purchase_info = {}
        duration_display = ""
        is_paid_with_pass = getattr(booking, 'used_pass', False)
        is_paid_with_subscription = getattr(booking, 'used_subscription', False)
        is_paid_with_package = getattr(booking, 'payment_status', '') == 'paid_with_package' or getattr(booking, 'status', '') == 'confirmed_with_package'

        if hasattr(booking, 'activity') and booking.activity:
            email_category = 'activity'
            activity_title = (
                getattr(booking.activity, f'title_{client_lang}', None)
                or booking.activity.title
            )
            booking_type_display = activity_title
            booking_date_display = str(booking.activity.date) if booking.activity.date else "Scheduled Date"
            activity_start = booking.activity.open_time.strftime('%H:%M') if booking.activity.open_time else None
            activity_end = booking.activity.close_time.strftime('%H:%M') if booking.activity.close_time else None
            booking_time_display = f"{activity_start} - {activity_end}" if activity_start and activity_end else "Scheduled Time"
            time_slot_display = ""
        elif hasattr(booking, 'sauna_type'):
            # Check whether VIP Sauna or Shared/Normal Sauna
            start_str = booking.booking_time.strftime('%H:%M') if booking.booking_time else ""
            end_str = ""
            time_slot_val = getattr(booking, 'time_slot', '3_hours')
            duration_minutes = 90 if time_slot_val == '90_mins' else (240 if time_slot_val == '4_hours' else 180)

            if client_lang == 'nl':
                duration_display = "90 minuten" if duration_minutes == 90 else (f"{duration_minutes // 60} uur")
            elif client_lang == 'de':
                duration_display = "90 Minuten" if duration_minutes == 90 else (f"{duration_minutes // 60} Stunden")
            else:
                duration_display = "90 minutes" if duration_minutes == 90 else (f"{duration_minutes // 60} hours")

            if booking.booking_time:
                from datetime import datetime as dt_cls, timedelta as dt_delta
                dummy_dt = dt_cls.combine(booking.booking_date, booking.booking_time)
                calc_end = (dummy_dt + dt_delta(minutes=duration_minutes)).time()
                end_str = calc_end.strftime('%H:%M')

            booking_time_display = f"{start_str} – {end_str}" if (start_str and end_str) else (start_str or "Scheduled Time")
            booking_date_display = str(booking.booking_date)
            time_slot_display = booking.get_time_slot_display() if hasattr(booking, 'get_time_slot_display') else str(getattr(booking, 'time_slot', ''))

            if booking.sauna_type == 'private':
                email_category = 'vip_sauna'
                booking_type_display = 'VIP Sauna'
            else:
                email_category = 'sauna'
                booking_type_display = 'Sauna'

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
                            service_title = 'Salt Room' if client_lang == 'en' else ('Salzkammer' if client_lang == 'de' else 'Zoutkamer')
                        elif service_type == 'lunchroom':
                            service_title = 'Lunchroom'
                        elif service_type == 'activity':
                            service_title = 'Activity' if client_lang == 'en' else ('Aktivität' if client_lang == 'de' else 'Activiteit')
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
                                end_time_str = f" - {sr_obj.end_time.strftime('%H:%M')}" if sr_obj.end_time else ""
                                time_str = f" @ {sr_obj.start_time.strftime('%H:%M')}{end_time_str}"
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
                    'validity': "Unlimited" if client_lang == 'en' else ("Unbegrenzt" if client_lang == 'de' else "Onbeperkt"),
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
            email_category = 'saltroom'
            start_str = booking.start_time.strftime('%H:%M') if hasattr(booking.start_time, 'strftime') else str(booking.start_time)[:5]
            end_str = booking.end_time.strftime('%H:%M') if hasattr(booking.end_time, 'strftime') else str(booking.end_time)[:5]
            booking_time_display = f"{start_str} – {end_str}" if (start_str and end_str) else (start_str or "Scheduled Time")
            booking_date_display = str(booking.date)
            time_slot_display = "Saltroom"
            if client_lang == 'nl':
                booking_type_display = 'Zoutkamer & Halotherapie'
            elif client_lang == 'de':
                booking_type_display = 'Salzkammer & Halotherapie'
            else:
                booking_type_display = 'Salt Room & Halotherapy'
        elif hasattr(booking, 'booking_date') and hasattr(booking, 'booking_time') and getattr(booking, 'booking_id', '').startswith('LR-'):
            email_category = 'lunchroom'
            booking_type_display = 'Lunchroom'
            booking_date_display = str(getattr(booking, 'booking_date', ''))
            booking_time_display = str(getattr(booking, 'booking_time', ''))
            time_slot_display = ""
        else:
            booking_type_display = 'Lunchroom'
            booking_date_display = str(getattr(booking, 'booking_date', ''))
            booking_time_display = str(getattr(booking, 'booking_time', ''))
            time_slot_display = ""

        guests_count_display = getattr(booking, 'guests', None) or getattr(booking, 'capacity', 1)
        is_paid_booking = hasattr(booking, 'total_price') and float(getattr(booking, 'total_price', 0)) > 0

        # Fetch dynamic contact details from DB
        from others.models import ContactInfo
        contact = ContactInfo.objects.first()
        contact_address = contact.address if contact and contact.address else "Slotweg 1, Egmond aan den Hoef"
        contact_phone = contact.phone if contact and contact.phone else "072-3030548"
        contact_email = contact.email if contact and contact.email else (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "info@heaven-on-earth.nl")

        # First name for personalized greeting
        full_name = getattr(booking, 'name', 'Guest') or 'Guest'
        first_name = full_name.strip().split()[0] if full_name.strip() else 'Guest'

        # Adjust subject line based on category
        if email_category == 'activity':
            if client_lang == 'nl':
                subject = f"Wat leuk dat je erbij bent! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Wie schön, dass du dabei bist! ✨ • Heaven on Earth"
            else:
                subject = f"How wonderful to have you joining us! ✨ • Heaven on Earth"
        elif email_category == 'lunchroom':
            if client_lang == 'en':
                subject = f"How lovely that you're coming to enjoy some time with us! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Wie schön, dass Sie bei uns eine genussvolle Zeit verbringen möchten! ✨ • Heaven on Earth"
            else:
                subject = f"Wat leuk dat je bij ons komt genieten! ✨ • Heaven on Earth"
        elif email_category == 'package':
            if client_lang == 'nl':
                subject = f"Wat leuk dat je bij ons komt genieten! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Wie schön, dass du bei uns genießt! ✨ • Heaven on Earth"
            else:
                subject = f"How lovely that you're joining us to enjoy! ✨ • Heaven on Earth"
        elif email_category == 'vip_sauna':
            if client_lang == 'nl':
                subject = f"Een heerlijk moment van ontspanning wacht op je! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Ein herrlicher Moment der Entspannung wartet auf dich! ✨ • Heaven on Earth"
            else:
                subject = f"A wonderful moment of relaxation awaits you! ✨ • Heaven on Earth"
        elif email_category == 'sauna':
            if client_lang == 'nl':
                subject = f"Jouw moment van ontspanning is gereserveerd! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Dein Moment der Entspannung ist reserviert! ✨ • Heaven on Earth"
            else:
                subject = f"Your moment of relaxation is reserved! ✨ • Heaven on Earth"
        elif email_category == 'saltroom':
            if client_lang == 'nl':
                subject = f"Ontdek de bijzondere ervaring van halotherapie! ✨ • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Entdecke die besondere Erfahrung der Halotherapie! ✨ • Heaven on Earth"
            else:
                subject = f"Discover the special experience of halotherapy! ✨ • Heaven on Earth"
        elif email_category == 'event':
            if client_lang == 'nl':
                subject = f"Aanvraag ontvangen! Referentie: {booking.booking_id} • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Anfrage erhalten! Referenz: {booking.booking_id} • Heaven on Earth"
            else:
                subject = f"Enquiry Received! Reference: {booking.booking_id} • Heaven on Earth"
        elif email_category == 'purchase':
            if getattr(booking, 'purchase_type', '') == 'session_pass':
                if client_lang == 'nl':
                    subject = f"Strippenkaart bevestigd! Referentie: {booking.purchase_id} • Heaven on Earth"
                elif client_lang == 'de':
                    subject = f"Mehrfachkarte bestätigt! Referenz: {booking.purchase_id} • Heaven on Earth"
                else:
                    subject = f"Pass Confirmed! Reference: {booking.purchase_id} • Heaven on Earth"
            else:
                if client_lang == 'nl':
                    subject = f"Abonnement bevestigd! Referentie: {booking.purchase_id} • Heaven on Earth"
                elif client_lang == 'de':
                    subject = f"Abonnement bestätigt! Referenz: {booking.purchase_id} • Heaven on Earth"
                else:
                    subject = f"Subscription Confirmed! Reference: {booking.purchase_id} • Heaven on Earth"
        else:
            if client_lang == 'nl':
                subject = f"Reservering bevestigd! Referentie: {booking_id} • Heaven on Earth"
            elif client_lang == 'de':
                subject = f"Reservierung bestätigt! Referenz: {booking_id} • Heaven on Earth"
            else:
                subject = f"Booking Confirmed! Reference: {booking_id} • Heaven on Earth"

        context = {
            'booking': booking,
            'name': full_name,
            'first_name': first_name,
            'lang': client_lang,
            'contact_address': contact_address,
            'contact_phone': contact_phone,
            'contact_email': contact_email,
            'email_category': email_category,
            'is_paid_with_package': is_paid_with_package,
            'is_paid_with_pass': is_paid_with_pass,
            'is_paid_with_subscription': is_paid_with_subscription,
            'sub_services_list': sub_services_list,
            'purchase_info': purchase_info,
            'duration_display': duration_display,
            'booking_type_display': booking_type_display,
            'booking_date_display': booking_date_display,
            'booking_time_display': booking_time_display,
            'time_slot_display': time_slot_display,
            'guests_count_display': guests_count_display,
            'is_paid_booking': is_paid_booking,
        }

        if email_category == 'activity':
            html_message = render_to_string('email/activity_confirmation_email.html', context)
        elif email_category == 'lunchroom':
            html_message = render_to_string('email/lunchroom_confirmation_email.html', context)
        elif email_category == 'event':
            html_message = render_to_string('email/event_confirmation_email.html', context)
        elif email_category == 'package':
            html_message = render_to_string('email/package_confirmation_email.html', context)
        elif email_category == 'vip_sauna':
            html_message = render_to_string('email/vip_sauna_confirmation_email.html', context)
        elif email_category == 'sauna':
            html_message = render_to_string('email/sauna_confirmation_email.html', context)
        elif email_category == 'saltroom':
            html_message = render_to_string('email/saltroom_confirmation_email.html', context)
        elif email_category == 'purchase':
            html_message = render_to_string('email/purchase_confirmation_email.html', context)
        else:
            html_message = render_to_string('email/booking_confirmation_email.html', context)

        time_slot_str = f" ({time_slot_display})" if time_slot_display else ""
        total_paid_str = f"\nTotal Paid: €{booking.total_price}" if hasattr(booking, 'total_price') else ""

        if email_category == 'activity':
            if client_lang == 'nl':
                plain_message = (
                    f"Wat leuk dat je erbij bent! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Bedankt voor je reservering bij Heaven on Earth! Wat gezellig dat je binnenkort bij ons langskomt.\n\n"
                    f"Je betaling is ontvangen en je reservering is definitief bevestigd. Wij kijken ernaar uit om je te verwelkomen!\n\n"
                    f"Jouw reserveringsgegevens\n"
                    f"Reserveringsnummer: {booking.booking_id}\n"
                    f"Activiteit: {booking_type_display}\n"
                    f"Datum: {booking_date_display}\n"
                    f"Tijd: {booking_time_display}\n"
                    f"Aantal personen: {guests_count_display}\n"
                    f"Totaal betaald: € {booking.total_price}\n\n"
                    f"We vragen je om 10 tot 15 minuten voor aanvang aanwezig te zijn, zodat je ontspannen aan jouw activiteit kunt beginnen.\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We helpen je graag!\n\n"
                    f"Tot snel bij Heaven on Earth! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Wie schön, dass du dabei bist! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"Vielen Dank für deine Reservierung bei Heaven on Earth! Wie schön, dass du uns bald besuchen wirst.\n\n"
                    f"Deine Zahlung ist bei uns eingegangen und deine Reservierung ist nun verbindlich bestätigt. Wir freuen uns darauf, dich bei uns willkommen zu heißen!\n\n"
                    f"Deine Reservierungsdetails\n"
                    f"Reservierungsnummer: {booking.booking_id}\n"
                    f"Aktivität: {booking_type_display}\n"
                    f"Datum: {booking_date_display}\n"
                    f"Uhrzeit: {booking_time_display}\n"
                    f"Anzahl der Personen: {guests_count_display}\n"
                    f"Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Wir bitten dich, 10 bis 15 Minuten vor Beginn deiner Aktivität bei uns einzutreffen, damit du ganz entspannt in dein Erlebnis starten kannst.\n\n"
                    f"Hast du noch Fragen oder besondere Wünsche? Dann kontaktiere uns gerne. Wir helfen dir jederzeit weiter!\n\n"
                    f"Bis bald bei Heaven on Earth! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"How wonderful to have you joining us! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"Thank you for your reservation at Heaven on Earth! We're delighted that you'll be visiting us soon.\n\n"
                    f"Your payment has been received, and your reservation is now officially confirmed. We look forward to welcoming you!\n\n"
                    f"Your Reservation Details\n"
                    f"Booking number: {booking.booking_id}\n"
                    f"Activity: {booking_type_display}\n"
                    f"Date: {booking_date_display}\n"
                    f"Time: {booking_time_display}\n"
                    f"Number of guests: {guests_count_display}\n"
                    f"Total paid: € {booking.total_price}\n\n"
                    f"We kindly ask you to arrive 10 to 15 minutes before the start of your activity so you can begin your experience in a relaxed and comfortable way.\n\n"
                    f"Do you have any questions or special requests? Please don't hesitate to contact us. We're always happy to help!\n\n"
                    f"See you soon at Heaven on Earth! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n📞 {contact_phone}"
                )
        elif email_category == 'lunchroom':
            if client_lang == 'en':
                plain_message = (
                    f"How lovely that you're coming to enjoy some time with us! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"Thank you for your reservation at Heaven on Earth! We're delighted that you'll be visiting us soon.\n\n"
                    f"We look forward to welcoming you to our cozy lunchroom, where you can relax, unwind, and enjoy all the delicious dishes we prepare with love.\n\n"
                    f"Your reservation is confirmed, and we've saved a lovely spot just for you!\n\n"
                    f"Do you have any questions or special requests? Please don't hesitate to contact us. We're always happy to help.\n\n"
                    f"See you soon at Heaven on Earth!\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}\n"
                    f"✉️ {contact_email}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Wie schön, dass Sie bei uns eine genussvolle Zeit verbringen möchten! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"vielen Dank für Ihre Reservierung bei Heaven on Earth! Wir freuen uns sehr, dass Sie uns bald besuchen kommen.\n\n"
                    f"Wir freuen uns darauf, Sie in unserem gemütlichen Lunchroom willkommen zu heißen. Hier können Sie sich entspannen, den Alltag hinter sich lassen und all die Köstlichkeiten genießen, die wir mit viel Liebe für Sie zubereiten.\n\n"
                    f"Ihre Reservierung ist bestätigt und wir haben einen schönen Platz für Sie reserviert!\n\n"
                    f"Haben Sie noch Fragen oder besondere Wünsche? Kontaktieren Sie uns gerne. Wir helfen Ihnen jederzeit mit Freude weiter.\n\n"
                    f"Bis bald bei Heaven on Earth!\n\n"
                    f"Mit herzlichen Grüßen,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}\n"
                    f"✉️ {contact_email}"
                )
            else:
                plain_message = (
                    f"Wat leuk dat je bij ons komt genieten! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Bedankt voor je reservering bij Heaven on Earth! Wat gezellig dat je binnenkort bij ons langskomt.\n\n"
                    f"We kijken ernaar uit je te verwelkomen in onze sfeervolle lunchroom, waar je heerlijk kunt ontspannen en genieten van al het lekkers dat we met liefde voor je bereiden.\n\n"
                    f"Je reservering is bevestigd en we hebben een plekje voor je gereserveerd!\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We denken graag met je mee.\n\n"
                    f"Tot snel bij Heaven on Earth!\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}\n"
                    f"✉️ {contact_email}"
                )
        elif email_category == 'event':
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
        elif email_category == 'package':
            if client_lang == 'nl':
                plain_message = (
                    f"Wat leuk dat je bij ons komt genieten! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Bedankt voor je reservering bij Heaven on Earth! Wat fijn dat je hebt gekozen voor een van onze arrangementen.\n\n"
                    f"We kijken ernaar uit je te verwelkomen voor een heerlijke ervaring vol ontspanning, gezelligheid en genieten.\n\n"
                    f"Jouw reserveringsgegevens:\n\n"
                    f"- Reserveringsnummer: {booking.booking_id}\n"
                    f"- Arrangement: {booking_type_display}\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Aantal personen: {guests_count_display}\n"
                    f"- Inbegrepen activiteiten en tijden: {', '.join(sub_services_list) if sub_services_list else 'Inclusief'}\n"
                    f"- Totaal betaald: € {booking.total_price}\n\n"
                    f"Je reservering is bevestigd en we zorgen ervoor dat alles voor je klaarstaat.\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We denken graag met je mee.\n\n"
                    f"Tot snel bij Heaven on Earth, waar genieten samenkomt! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Wie schön, dass du bei uns genießt! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"vielen Dank für deine Reservierung bei Heaven on Earth! Wie schön, dass du dich für eines unserer Arrangements entschieden hast.\n\n"
                    f"Wir freuen uns darauf, dich zu einem wunderbaren Erlebnis voller Entspannung, Gemütlichkeit und Genuss willkommen zu heißen.\n\n"
                    f"Deine Reservierungsdetails:\n\n"
                    f"- Reservierungsnummer: {booking.booking_id}\n"
                    f"- Arrangement: {booking_type_display}\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Anzahl der Personen: {guests_count_display}\n"
                    f"- Enthaltene Aktivitäten und Zeiten: {', '.join(sub_services_list) if sub_services_list else 'Inbegriffen'}\n"
                    f"- Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Deine Reservierung ist bestätigt und wir sorgen dafür, dass alles für dich bereitsteht.\n\n"
                    f"Hast du noch Fragen oder besondere Wünsche? Kontaktiere uns gerne. Wir denken gerne mit dir mit.\n\n"
                    f"Bis bald bei Heaven on Earth, wo Genuss zusammenkommt! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"How lovely that you're joining us to enjoy! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"Thank you for your reservation at Heaven on Earth! We are delighted that you have chosen one of our packages.\n\n"
                    f"We look forward to welcoming you for a wonderful experience full of relaxation, warmth, and enjoyment.\n\n"
                    f"Your reservation details:\n\n"
                    f"- Booking number: {booking.booking_id}\n"
                    f"- Package: {booking_type_display}\n"
                    f"- Date: {booking_date_display}\n"
                    f"- Number of guests: {guests_count_display}\n"
                    f"- Included activities and times: {', '.join(sub_services_list) if sub_services_list else 'Included'}\n"
                    f"- Total paid: € {booking.total_price}\n\n"
                    f"Your reservation is confirmed and we will ensure that everything is ready for you.\n\n"
                    f"Do you have any questions or special requests? Please feel free to contact us. We are happy to help.\n\n"
                    f"See you soon at Heaven on Earth, where enjoyment comes together! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
        elif email_category == 'vip_sauna':
            extras_str = ", ".join(booking.get_feature_names()) if hasattr(booking, 'get_feature_names') and booking.get_feature_names() else ("Geen" if client_lang == 'nl' else ("Keine" if client_lang == 'de' else "None"))
            paid_str = "Inbegrepen in arrangement" if is_paid_with_package and client_lang == 'nl' else (f"€ {booking.total_price}")

            if client_lang == 'nl':
                plain_message = (
                    f"Een heerlijk moment van ontspanning wacht op je! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Wat leuk dat je hebt gekozen voor onze VIP Sauna bij Heaven on Earth!\n\n"
                    f"Je betaling is ontvangen en je reservering is bevestigd. Binnenkort is het tijd om even helemaal tot rust te komen en te genieten van een moment voor jezelf en je gezelschap.\n\n"
                    f"Jouw reserveringsgegevens:\n\n"
                    f"- Reserveringsnummer: {booking.booking_id}\n"
                    f"- Ervaring: VIP Sauna\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Tijd: {booking_time_display}\n"
                    f"- Aantal personen: {guests_count_display}\n"
                    f"- Extra's: {extras_str}\n"
                    f"- Totaal betaald: {paid_str}\n\n"
                    f"Tijdens je bezoek geniet je in alle privacy van onze sfeervolle sauna en heerlijke faciliteiten. Alles staat voor je klaar om er een ontspannen ervaring van te maken.\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We helpen je graag.\n\n"
                    f"We kijken ernaar uit je te verwelkomen bij Heaven on Earth! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Ein herrlicher Moment der Entspannung wartet auf dich! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"wie schön, dass du dich für unsere VIP Sauna bei Heaven on Earth entschieden hast!\n\n"
                    f"Deine Zahlung ist eingegangen und deine Reservierung ist bestätigt. Bald ist es Zeit, vollkommen zur Ruhe zu kommen und einen Moment für dich und deine Begleitung zu genießen.\n\n"
                    f"Deine Reservierungsdetails:\n\n"
                    f"- Reservierungsnummer: {booking.booking_id}\n"
                    f"- Erlebnis: VIP Sauna\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Uhrzeit: {booking_time_display}\n"
                    f"- Anzahl der Personen: {guests_count_display}\n"
                    f"- Extras: {extras_str}\n"
                    f"- Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Während deines Besuchs genießt du in vollkommener Privatsphäre unsere stimmungsvolle Sauna und die wunderbaren Einrichtungen. Alles steht für dich bereit, um deinen Aufenthalt zu einem entspannenden Erlebnis zu machen.\n\n"
                    f"Hast du noch Fragen oder besondere Wünsche? Kontaktiere uns gerne. Wir helfen dir gerne weiter.\n\n"
                    f"Wir freuen uns darauf, dich bei Heaven on Earth willkommen zu heißen! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"A wonderful moment of relaxation awaits you! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"How wonderful that you have chosen our VIP Sauna at Heaven on Earth!\n\n"
                    f"Your payment has been received and your reservation is confirmed. Soon it will be time to completely unwind and enjoy a moment for yourself and your company.\n\n"
                    f"Your reservation details:\n\n"
                    f"- Booking number: {booking.booking_id}\n"
                    f"- Experience: VIP Sauna\n"
                    f"- Date: {booking_date_display}\n"
                    f"- Time: {booking_time_display}\n"
                    f"- Number of guests: {guests_count_display}\n"
                    f"- Add-ons: {extras_str}\n"
                    f"- Total paid: € {booking.total_price}\n\n"
                    f"During your visit, you will enjoy our atmospheric sauna and wonderful facilities in complete privacy. Everything is ready for you to have a relaxing experience.\n\n"
                    f"Do you have any questions or special requests? Please feel free to contact us. We are happy to help.\n\n"
                    f"We look forward to welcoming you to Heaven on Earth! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
        elif email_category == 'sauna':
            dur_text = duration_display or ("90 minuten" if client_lang == 'nl' else ("90 Minuten" if client_lang == 'de' else "90 minutes"))
            paid_str = "Inbegrepen in arrangement" if is_paid_with_package and client_lang == 'nl' else (f"€ {booking.total_price}")

            if client_lang == 'nl':
                plain_message = (
                    f"Jouw moment van ontspanning is gereserveerd! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Wat leuk dat je binnenkort bij ons komt genieten!\n\n"
                    f"Je betaling is ontvangen en je reservering voor onze sauna is bevestigd.\n\n"
                    f"Laat de dagelijkse drukte even achter je en geniet van een heerlijk moment van rust, warmte en ontspanning.\n\n"
                    f"Jouw reserveringsgegevens:\n\n"
                    f"- Reserveringsnummer: {booking.booking_id}\n"
                    f"- Ervaring: Sauna\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Tijd: {booking_time_display}\n"
                    f"- Duur: {dur_text}\n"
                    f"- Aantal personen: {guests_count_display}\n"
                    f"- Totaal betaald: {paid_str}\n\n"
                    f"Goed om te weten\n\n"
                    f"We vragen je om 15 minuten voor aanvang aanwezig te zijn, zodat je rustig kunt aankomen.\n\n"
                    f"In onze sauna is het dragen van badkleding verplicht. Vergeet daarom niet je badkleding, handdoek en slippers mee te nemen.\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We helpen je graag.\n\n"
                    f"We kijken ernaar uit je te verwelkomen bij Heaven on Earth! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Dein Moment der Entspannung ist reserviert! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"wie schön, dass du uns bald besuchen und genießen wirst!\n\n"
                    f"Deine Zahlung ist eingegangen und deine Reservierung für unsere Sauna ist bestätigt.\n\n"
                    f"Lass die Hektik des Alltags hinter dir und genieße einen herrlichen Moment der Ruhe, Wärme und Entspannung.\n\n"
                    f"Deine Reservierungsdetails:\n\n"
                    f"- Reservierungsnummer: {booking.booking_id}\n"
                    f"- Erlebnis: Sauna\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Uhrzeit: {booking_time_display}\n"
                    f"- Dauer: {dur_text}\n"
                    f"- Anzahl der Personen: {guests_count_display}\n"
                    f"- Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Gut zu wissen\n\n"
                    f"Wir bitten dich, 15 Minuten vor Beginn einzutreffen, damit du ganz entspannt ankommen kannst.\n\n"
                    f"In unserer Sauna ist das Tragen von Badebekleidung Pflicht. Bitte denke daran, Badebekleidung, Handtuch und Badeschlappen mitzubringen.\n\n"
                    f"Hast du noch Fragen oder besondere Wünsche? Kontaktiere uns gerne. Wir helfen dir gerne weiter.\n\n"
                    f"Wir freuen uns darauf, dich bei Heaven on Earth willkommen zu heißen! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"Your moment of relaxation is reserved! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"How lovely that you are coming to enjoy your time with us soon!\n\n"
                    f"Your payment has been received and your reservation for our sauna is confirmed.\n\n"
                    f"Leave the daily hustle and bustle behind and indulge in a wonderful moment of peace, warmth, and relaxation.\n\n"
                    f"Your reservation details:\n\n"
                    f"- Booking number: {booking.booking_id}\n"
                    f"- Experience: Sauna\n"
                    f"- Date: {booking_date_display}\n"
                    f"- Time: {booking_time_display}\n"
                    f"- Duration: {dur_text}\n"
                    f"- Number of guests: {guests_count_display}\n"
                    f"- Total paid: € {booking.total_price}\n\n"
                    f"Good to know\n\n"
                    f"We kindly ask you to arrive 15 minutes before your scheduled start time so you can settle in comfortably.\n\n"
                    f"Wearing swimwear is mandatory in our sauna. Please don't forget to bring your swimwear, towel, and slippers.\n\n"
                    f"Do you have any questions or special requests? Please don't hesitate to contact us. We are happy to help.\n\n"
                    f"We look forward to welcoming you to Heaven on Earth! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
        elif email_category == 'saltroom':
            paid_str = "Inbegrepen in arrangement" if is_paid_with_package and client_lang == 'nl' else (
                "Betaald met strippenkaart" if is_paid_with_pass and client_lang == 'nl' else (
                    "Inbegrepen in abonnement" if is_paid_with_subscription and client_lang == 'nl' else (
                        f"€ {booking.total_price}"
                    )
                )
            )

            if client_lang == 'nl':
                plain_message = (
                    f"Ontdek de bijzondere ervaring van halotherapie! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Wat leuk dat je binnenkort bij ons komt genieten!\n\n"
                    f"Je betaling is ontvangen en je reservering voor onze zoutkamer is bevestigd.\n\n"
                    f"In onze sfeervolle zoutkamer ervaar je de bijzondere combinatie van een ontspannen omgeving en de fijne zoutdeeltjes die tijdens de halotherapie in de ruimte worden verspreid.\n\n"
                    f"Een heerlijk moment om even de dagelijkse drukte achter je te laten en bewust tijd voor jezelf te nemen.\n\n"
                    f"Jouw reserveringsgegevens:\n\n"
                    f"- Reserveringsnummer: {booking.booking_id}\n"
                    f"- Ervaring: Zoutkamer & Halotherapie\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Tijd: {booking_time_display}\n"
                    f"- Aantal personen: {guests_count_display}\n"
                    f"- Totaal betaald: {paid_str}\n\n"
                    f"Goed om te weten\n\n"
                    f"We vragen je om 10 minuten voor aanvang aanwezig te zijn, zodat je rustig kunt aankomen en ontspannen aan je sessie kunt beginnen.\n\n"
                    f"Draag bij voorkeur comfortabele kleding waarin je prettig kunt ontspannen.\n\n"
                    f"Heb je nog vragen of speciale wensen? Neem gerust contact met ons op. We helpen je graag!\n\n"
                    f"We kijken ernaar uit je te verwelkomen bij Heaven on Earth! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Entdecke die besondere Erfahrung der Halotherapie! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"wie schön, dass du uns bald besuchen und genießen wirst!\n\n"
                    f"Deine Zahlung ist eingegangen und deine Reservierung für unsere Salzkammer ist bestätigt.\n\n"
                    f"In unserer stimmungsvollen Salzkammer erlebst du die besondere Kombination aus einer entspannenden Atmosphäre und feinsten Salzpartikeln, die während der Halotherapie im Raum verteilt werden.\n\n"
                    f"Ein herrlicher Moment, um die Hektik des Alltags hinter sich zu lassen und sich bewusst Zeit für sich selbst zu nehmen.\n\n"
                    f"Deine Reservierungsdetails:\n\n"
                    f"- Reservierungsnummer: {booking.booking_id}\n"
                    f"- Erlebnis: Salzkammer & Halotherapie\n"
                    f"- Datum: {booking_date_display}\n"
                    f"- Uhrzeit: {booking_time_display}\n"
                    f"- Anzahl der Personen: {guests_count_display}\n"
                    f"- Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Gut zu wissen\n\n"
                    f"Wir bitten dich, 10 Minuten vor Beginn einzutreffen, damit du ganz entspannt ankommen und deine Sitzung beginnen kannst.\n\n"
                    f"Trage vorzugsweise bequeme Kleidung, in der du dich wohlfühlst und gut entspannen kannst.\n\n"
                    f"Hast du noch Fragen oder besondere Wünsche? Kontaktiere uns gerne. Wir helfen dir gerne weiter!\n\n"
                    f"Wir freuen uns darauf, dich bei Heaven on Earth willkommen zu heißen! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"Discover the special experience of halotherapy! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"How lovely that you will be visiting us soon to unwind and enjoy!\n\n"
                    f"Your payment has been received and your reservation for our salt room is confirmed.\n\n"
                    f"In our atmospheric salt room, you will experience the unique combination of a soothing ambiance and the fine micro-salt particles dispersed throughout the space during halotherapy.\n\n"
                    f"A wonderful moment to leave everyday stress behind and intentionally dedicate time to your wellbeing.\n\n"
                    f"Your reservation details:\n\n"
                    f"- Booking number: {booking.booking_id}\n"
                    f"- Experience: Salt Room & Halotherapy\n"
                    f"- Date: {booking_date_display}\n"
                    f"- Time: {booking_time_display}\n"
                    f"- Number of guests: {guests_count_display}\n"
                    f"- Total paid: € {booking.total_price}\n\n"
                    f"Good to know\n\n"
                    f"We kindly ask you to arrive 10 minutes prior to your session so you can arrive relaxed and ready.\n\n"
                    f"Please wear comfortable clothing that allows you to fully relax.\n\n"
                    f"Do you have any questions or special requests? Please don't hesitate to reach out. We are delighted to assist!\n\n"
                    f"We look forward to welcoming you to Heaven on Earth! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
        elif email_category == 'purchase':
            product_label = getattr(booking, 'purchase_type', '')
            if client_lang == 'nl':
                plain_message = (
                    f"Bedankt voor je aankoop bij Heaven on Earth! ✨\n\n"
                    f"Beste {first_name},\n\n"
                    f"Je betaling is ontvangen en je aankoop is geactiveerd.\n\n"
                    f"Aankoopgegevens:\n\n"
                    f"- Referentienummer: {booking.purchase_id}\n"
                    f"- Product: {booking_type_display}\n"
                    f"- Totaal betaald: € {booking.total_price}\n\n"
                    f"Je kunt je sessies en reserveringen op elk moment bekijken en beheren via je persoonlijke dashboard.\n\n"
                    f"Tot snel bij Heaven on Earth! ✨\n\n"
                    f"Met warme groet,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            elif client_lang == 'de':
                plain_message = (
                    f"Vielen Dank für deinen Kauf bei Heaven on Earth! ✨\n\n"
                    f"Liebe/r {first_name},\n\n"
                    f"deine Zahlung ist eingegangen und dein Kauf wurde aktiviert.\n\n"
                    f"Kaufdetails:\n\n"
                    f"- Referenz-ID: {booking.purchase_id}\n"
                    f"- Produkt: {booking_type_display}\n"
                    f"- Gesamtbetrag bezahlt: € {booking.total_price}\n\n"
                    f"Du kannst deine Sitzungen und Reservierungen jederzeit in deinem Kunden-Dashboard einsehen und verwalten.\n\n"
                    f"Bis bald bei Heaven on Earth! ✨\n\n"
                    f"Herzliche Grüße,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
            else:
                plain_message = (
                    f"Thank you for your purchase at Heaven on Earth! ✨\n\n"
                    f"Dear {first_name},\n\n"
                    f"Your payment has been received and your purchase is activated.\n\n"
                    f"Purchase details:\n\n"
                    f"- Purchase ID: {booking.purchase_id}\n"
                    f"- Product: {booking_type_display}\n"
                    f"- Total paid: € {booking.total_price}\n\n"
                    f"You can view and manage your passes and reservations anytime in your customer dashboard.\n\n"
                    f"See you soon at Heaven on Earth! ✨\n\n"
                    f"Warm regards,\n\n"
                    f"Team Heaven on Earth\n"
                    f"📍 {contact_address}\n"
                    f"📞 {contact_phone}"
                )
        else:
            plain_message = (
                f"Hello {booking.name},\n\n"
                f"Thank you for your reservation at Heaven on Earth! Your booking has been confirmed.\n\n"
                f"Reference ID: {booking.booking_id}\n"
                f"Type: {booking_type_display}\n"
                f"Date: {booking_date_display}\n"
                f"Time: {booking_time_display}{time_slot_str}"
                f"{total_paid_str}\n\n"
                f"Heaven on Earth\n📍 {contact_address}\n📞 {contact_phone}\n✉️ {contact_email}"
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
