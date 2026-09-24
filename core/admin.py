from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Hub, Customer, Parcel, ParcelTrackingLog, WhatsAppLog, Setting

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'name', 'phone', 'role', 'hub', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('hub', 'name', 'phone', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('hub', 'name', 'phone', 'role')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Hub)
admin.site.register(Customer)
admin.site.register(Parcel)
admin.site.register(ParcelTrackingLog)
admin.site.register(WhatsAppLog)
admin.site.register(Setting)