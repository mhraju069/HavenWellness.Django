from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ContactInfo, TermsAndConditions, PrivacyPolicy, FAQ, SupportMessage, SocialMediaLink


@admin.register(ContactInfo)
class ContactInfoAdmin(ModelAdmin):
    list_display = ('id', 'email', 'phone', 'address', 'updated_at')
    search_fields = ('email', 'phone', 'address')


@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(ModelAdmin):
    list_display = ('id', 'effective_date', 'updated_at')


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(ModelAdmin):
    list_display = ('id', 'effective_date', 'updated_at')


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ('id', 'question', 'updated_at')
    search_fields = ('question', 'answer')


@admin.register(SupportMessage)
class SupportMessageAdmin(ModelAdmin):
    list_display = ('id', 'get_sender', 'email', 'phone', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'phone', 'subject', 'message')

    def get_sender(self, obj):
        return obj.name or (obj.sender.username if obj.sender else "Anonymous")
    get_sender.short_description = "Sender"


@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(ModelAdmin):
    list_display = ('id', 'media_type', 'url', 'updated_at')
    list_editable = ('url',)
    search_fields = ('media_type', 'url')
