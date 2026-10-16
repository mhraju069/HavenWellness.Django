from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import ContactInfo, TermsAndConditions, PrivacyPolicy, FAQ, SupportMessage
from .serializers import (
    ContactInfoSerializer,
    TermsAndConditionsSerializer,
    PrivacyPolicySerializer,
    FAQSerializer,
    SupportMessageSerializer,
    SupportMessageCreateSerializer,
)


# ============================================================================
# 1. Contact Information API (GET, POST, PUT, PATCH)
# ============================================================================

class ContactInfoView(APIView):
    """
    Contact Information API:
    - GET: Retrieve business contact details (email, phone, address).
           If no entry exists in the database, automatically initializes default contact info.
    - POST: Create or update contact information.
    - PATCH / PUT: Update contact information fields.
    """
    permission_classes = [AllowAny]

    def _get_or_create_contact(self):
        contact = ContactInfo.objects.first()
        if not contact:
            contact = ContactInfo.objects.create(
                email="hello@serene.com",
                phone="+31 20 123 4567",
                address="Singel 450, 1017 AW Amsterdam, Netherlands"
            )
        return contact

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Get Contact Information",
        description="Returns the active business contact information (email, phone, address).",
        responses={200: ContactInfoSerializer},
    )
    def get(self, request):
        contact = self._get_or_create_contact()
        serializer = ContactInfoSerializer(contact)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Create or Update Contact Information",
        description="Creates or updates the business contact information.",
        request=ContactInfoSerializer,
        responses={200: ContactInfoSerializer},
    )
    def post(self, request):
        data = request.data
        contact = ContactInfo.objects.first()

        if not contact:
            serializer = ContactInfoSerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save()
                return Response({
                    "success": True,
                    "message": "Contact info created successfully.",
                    "data": ContactInfoSerializer(instance).data
                }, status=status.HTTP_201_CREATED)
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Update existing
        serializer = ContactInfoSerializer(contact, data=data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response({
                "success": True,
                "message": "Contact info updated successfully.",
                "data": ContactInfoSerializer(instance).data
            }, status=status.HTTP_200_OK)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Partially Update Contact Information",
        request=ContactInfoSerializer,
        responses={200: ContactInfoSerializer},
    )
    def patch(self, request):
        return self.post(request)

    def put(self, request):
        return self.post(request)


# ============================================================================
# 2. Privacy Policy API (GET, POST, PUT, PATCH)
# ============================================================================

class PrivacyPolicyView(APIView):
    """
    Privacy Policy API:
    - GET: Retrieve current privacy policy content.
           Auto-initializes with standard default sections if empty.
    - POST: Create or update privacy policy.
    - PATCH / PUT: Update privacy policy sections.
    """
    permission_classes = [AllowAny]

    def _get_or_create_policy(self):
        policy = PrivacyPolicy.objects.first()
        if not policy:
            policy = PrivacyPolicy.objects.create(
                effective_date=timezone.now().date(),
                info_we_collect="We collect personal information such as name, email address, phone number, and booking preferences when you interact with our wellness center services.",
                how_we_use_data="Your information is used solely to manage your reservations, process payments, provide tailored spa and sauna services, and send service updates.",
                child_safety="Our services are intended for adults. We do not knowingly collect personal information from children under 16 without parental consent.",
                user_rights="You have the right to access, rectify, or request deletion of your personal data at any time by contacting our support team.",
                security="We implement industry-standard encryption, secure cloud infrastructure, and access control policies to safeguard your personal data."
            )
        return policy

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Get Privacy Policy",
        description="Returns the active Privacy Policy sections and effective date.",
        responses={200: PrivacyPolicySerializer},
    )
    def get(self, request):
        policy = self._get_or_create_policy()
        serializer = PrivacyPolicySerializer(policy)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Create or Update Privacy Policy",
        description="Creates or updates the Privacy Policy content.",
        request=PrivacyPolicySerializer,
        responses={200: PrivacyPolicySerializer},
    )
    def post(self, request):
        data = request.data
        policy = PrivacyPolicy.objects.first()

        if not policy:
            serializer = PrivacyPolicySerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save()
                return Response({
                    "success": True,
                    "message": "Privacy policy created successfully.",
                    "data": PrivacyPolicySerializer(instance).data
                }, status=status.HTTP_201_CREATED)
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PrivacyPolicySerializer(policy, data=data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response({
                "success": True,
                "message": "Privacy policy updated successfully.",
                "data": PrivacyPolicySerializer(instance).data
            }, status=status.HTTP_200_OK)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Partially Update Privacy Policy",
        request=PrivacyPolicySerializer,
        responses={200: PrivacyPolicySerializer},
    )
    def patch(self, request):
        return self.post(request)

    def put(self, request):
        return self.post(request)


# ============================================================================
# 3. Terms and Conditions API (GET, POST, PUT, PATCH)
# ============================================================================

class TermsAndConditionsView(APIView):
    """
    Terms and Conditions API:
    - GET: Retrieve current Terms and Conditions content.
           Auto-initializes with standard default sections if empty.
    - POST: Create or update Terms and Conditions.
    - PATCH / PUT: Update Terms and Conditions sections.
    """
    permission_classes = [AllowAny]

    def _get_or_create_terms(self):
        terms = TermsAndConditions.objects.first()
        if not terms:
            terms = TermsAndConditions.objects.create(
                effective_date=timezone.now().date(),
                acceptance_of_terms="By accessing our facilities or booking services via our platform, you agree to comply with and be bound by these terms and conditions.",
                user_responsibilities="Guests must follow all health and safety guidelines, shower before using sauna or pool facilities, and maintain a quiet, respectful atmosphere.",
                ticket_purchase="All bookings, passes, and event admissions must be paid in full prior to arrival unless otherwise specified.",
                refund_policy="Cancellations made at least 24 hours in advance receive a full refund or credit. No-shows or late cancellations within 24 hours are non-refundable.",
                limitation_of_liability="Our facility is not liable for loss or damage to personal belongings or injuries resulting from failure to adhere to posted wellness safety rules.",
                changes_to_terms="We reserve the right to revise these terms at any time. Updates take effect immediately upon publication on this platform."
            )
        return terms

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Get Terms and Conditions",
        description="Returns the active Terms and Conditions content and effective date.",
        responses={200: TermsAndConditionsSerializer},
    )
    def get(self, request):
        terms = self._get_or_create_terms()
        serializer = TermsAndConditionsSerializer(terms)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Create or Update Terms and Conditions",
        description="Creates or updates the Terms and Conditions content.",
        request=TermsAndConditionsSerializer,
        responses={200: TermsAndConditionsSerializer},
    )
    def post(self, request):
        data = request.data
        terms = TermsAndConditions.objects.first()

        if not terms:
            serializer = TermsAndConditionsSerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save()
                return Response({
                    "success": True,
                    "message": "Terms and conditions created successfully.",
                    "data": TermsAndConditionsSerializer(instance).data
                }, status=status.HTTP_201_CREATED)
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TermsAndConditionsSerializer(terms, data=data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response({
                "success": True,
                "message": "Terms and conditions updated successfully.",
                "data": TermsAndConditionsSerializer(instance).data
            }, status=status.HTTP_200_OK)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Contact & Legal"],
        summary="Partially Update Terms and Conditions",
        request=TermsAndConditionsSerializer,
        responses={200: TermsAndConditionsSerializer},
    )
    def patch(self, request):
        return self.post(request)

    def put(self, request):
        return self.post(request)


# ============================================================================
# 4. Support Messages API (POST from frontend, GET/PATCH/DELETE for Admin)
# ============================================================================

class SupportMessageView(APIView):
    """
    Support Messages API:
    - POST: Public / User endpoint to submit a message or contact inquiry.
            Automatically attaches authenticated user if logged in.
    - GET: List all submitted messages with search, filter (is_read), and pagination.
           Also supports retrieving a single message by ID via URL path or query `?id=...`.
    - PATCH / PUT: Update message status (e.g. mark as is_read: true/false).
    - DELETE: Delete a message by ID.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Support Messages"],
        summary="List support messages or retrieve single message",
        parameters=[
            OpenApiParameter(name="id", description="Message ID to retrieve single message", required=False, type=int),
            OpenApiParameter(name="search", description="Search across name, email, phone, subject, or message", required=False, type=str),
            OpenApiParameter(name="is_read", description="Filter by read status (true / false)", required=False, type=bool),
            OpenApiParameter(name="page", description="Page number (default: 1)", required=False, type=int),
            OpenApiParameter(name="page_size", description="Results per page (default: 20)", required=False, type=int),
        ],
        responses={200: SupportMessageSerializer(many=True)},
    )
    def get(self, request, pk=None):
        target_id = pk or request.query_params.get('id')

        # 1. Single message detail lookup
        if target_id and str(target_id).isdigit():
            msg = SupportMessage.objects.filter(id=int(target_id)).first()
            if not msg:
                return Response({
                    "success": False,
                    "message": f"Support message with ID {target_id} not found."
                }, status=status.HTTP_404_NOT_FOUND)

            # Auto-mark as read on single inspection
            if not msg.is_read:
                msg.is_read = True
                msg.save(update_fields=['is_read'])

            return Response({
                "success": True,
                "data": SupportMessageSerializer(msg).data
            }, status=status.HTTP_200_OK)

        # 2. List with filters & pagination
        qs = SupportMessage.objects.select_related('sender').all().order_by('-created_at')

        is_read_param = request.query_params.get('is_read')
        if is_read_param is not None:
            val = str(is_read_param).strip().lower() in ['true', '1', 'yes']
            qs = qs.filter(is_read=val)

        search = (request.query_params.get('search') or request.query_params.get('q') or '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(subject__icontains=search) |
                Q(message__icontains=search) |
                Q(sender__username__icontains=search) |
                Q(sender__name__icontains=search)
            )

        total_count = qs.count()
        unread_count = SupportMessage.objects.filter(is_read=False).count()
        read_count = SupportMessage.objects.filter(is_read=True).count()

        # Pagination
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = max(1, min(100, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page_size = 20

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_qs = qs[start_idx:end_idx]

        serializer = SupportMessageSerializer(paginated_qs, many=True)
        return Response({
            "success": True,
            "summary": {
                "total_messages": total_count,
                "unread_messages": unread_count,
                "read_messages": read_count,
            },
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "has_next": end_idx < total_count,
            "has_previous": page > 1,
            "data": serializer.data,
            "results": serializer.data,
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Support Messages"],
        summary="Submit a new Support Message",
        description="Public endpoint for users/visitors to send a contact or support inquiry.",
        request=SupportMessageCreateSerializer,
        responses={201: SupportMessageSerializer},
    )
    def post(self, request):
        data = request.data
        raw_message = (data.get('message') or '').strip()

        if not raw_message:
            return Response({
                "success": False,
                "message": "Field 'message' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        sender_user = request.user if (request.user and request.user.is_authenticated) else None

        name = data.get('name')
        if not name and sender_user:
            name = getattr(sender_user, 'name', None) or getattr(sender_user, 'username', '')

        email = data.get('email')
        if not email and sender_user:
            email = getattr(sender_user, 'email', '')

        phone = data.get('phone') or getattr(sender_user, 'phone', '') if sender_user else data.get('phone')
        subject = (data.get('subject') or '').strip()

        msg_obj = SupportMessage.objects.create(
            sender=sender_user,
            name=name or "Guest",
            email=email or "",
            phone=phone or "",
            subject=subject,
            message=raw_message,
            is_read=False
        )

        return Response({
            "success": True,
            "message": "Your message has been sent successfully. We will get back to you shortly.",
            "data": SupportMessageSerializer(msg_obj).data
        }, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Support Messages"],
        summary="Update Support Message Status",
        description="Update read status (is_read: true/false) or details of a message.",
        parameters=[
            OpenApiParameter(name="id", description="Message ID", required=False, type=int),
        ],
        responses={200: SupportMessageSerializer},
    )
    def patch(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Message ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        msg = SupportMessage.objects.filter(id=int(target_id)).first()
        if not msg:
            return Response({
                "success": False,
                "message": f"Support message with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'is_read' in data:
            msg.is_read = bool(data['is_read'])
        if 'subject' in data:
            msg.subject = data['subject']
        if 'message' in data and data['message']:
            msg.message = data['message']

        msg.save()

        return Response({
            "success": True,
            "message": "Support message updated successfully.",
            "data": SupportMessageSerializer(msg).data
        }, status=status.HTTP_200_OK)

    def put(self, request, pk=None):
        return self.patch(request, pk)

    @extend_schema(
        tags=["Support Messages"],
        summary="Delete a Support Message",
        parameters=[
            OpenApiParameter(name="id", description="Message ID to delete", required=False, type=int),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def delete(self, request, pk=None):
        target_id = pk or request.data.get('id') or request.query_params.get('id')
        if not target_id or not str(target_id).isdigit():
            return Response({
                "success": False,
                "message": "Message ID is required to delete."
            }, status=status.HTTP_400_BAD_REQUEST)

        msg = SupportMessage.objects.filter(id=int(target_id)).first()
        if not msg:
            return Response({
                "success": False,
                "message": f"Support message with ID {target_id} not found."
            }, status=status.HTTP_404_NOT_FOUND)

        del_id = msg.id
        msg.delete()

        return Response({
            "success": True,
            "message": f"Support message #{del_id} deleted successfully."
        }, status=status.HTTP_200_OK)
