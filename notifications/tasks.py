import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
except ImportError:
    # Fallback dummy decorator if celery isn't loaded in current local environment
    def shared_task(func):
        return func


@shared_task
def send_24h_booking_reminders():
    """
    Periodic task to send 24-hour advance booking reminders to users.
    Looks for confirmed bookings happening between 23 and 25 hours from now.
    """
    from bookings.models import (
        SaunaBooking,
        LunchroomBooking,
        ActivityBooking,
        EventBooking,
        PackageBooking,
        SaltRoomBooking,
    )
    from notifications.models import Notification
    from notifications.views import notify_user

    now = timezone.now()
    target_start = (now + timedelta(hours=23)).date()
    target_end = (now + timedelta(hours=25)).date()

    reminded_count = 0

    # Helper to check and remind
    def process_booking(booking, service_name, b_date, b_time):
        nonlocal reminded_count
        user = getattr(booking, 'user', None)
        if not user:
            return

        b_id = getattr(booking, 'booking_id', None)
        if not b_id:
            return

        # Check if reminder notification was already sent for this booking
        already_reminded = Notification.objects.filter(
            user=user,
            notification_type='reminder',
            data__booking_id=b_id
        ).exists()

        if already_reminded:
            return

        time_str = f" at {b_time}" if b_time else ""
        date_str = str(b_date)
        booking_link = f"/bookings/{b_id}"

        notify_user(
            user=user,
            title=f"Reminder: Upcoming {service_name}",
            body=f"Your {service_name} session ({b_id}) is scheduled for tomorrow ({date_str}{time_str}). We look forward to welcoming you!",
            notification_type='reminder',
            link=booking_link,
            data={
                "booking_id": b_id,
                "type": service_name,
                "date": date_str,
                "time": str(b_time) if b_time else "",
                "link": booking_link,
            }
        )
        reminded_count += 1

    # 1. Sauna Bookings
    for b in SaunaBooking.objects.filter(booking_date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, "Sauna", b.booking_date, b.booking_time)

    # 2. Salt Room Bookings
    for b in SaltRoomBooking.objects.filter(booking_date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, "Salt Room", b.booking_date, b.start_time)

    # 3. Lunchroom Bookings
    for b in LunchroomBooking.objects.filter(booking_date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, "Lunchroom", b.booking_date, b.booking_time)

    # 4. Activity Bookings
    for b in ActivityBooking.objects.filter(activity__date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, getattr(b.activity, 'title', 'Activity'), b.activity.date, getattr(b.activity, 'open_time', None))

    # 5. Package Bookings
    for b in PackageBooking.objects.filter(date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, "Package Experience", b.date, None)

    # 6. Event Bookings
    for b in EventBooking.objects.filter(event__date__range=[target_start, target_end], status='confirmed'):
        process_booking(b, getattr(b.event, 'title', 'Event'), b.event.date, getattr(b.event, 'start_time', None))

    logger.info(f"Dispatched {reminded_count} booking reminder notifications.")
    return f"Dispatched {reminded_count} reminders"
