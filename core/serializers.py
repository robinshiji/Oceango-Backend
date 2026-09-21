from rest_framework import serializers
from .models import User, Hub, Customer, Parcel, ParcelTrackingLog, WhatsAppLog, Setting

class HubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hub
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'name', 'phone', 'role', 'hub']

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

    def validate_tracking_id(self, value):
        if value:
            value = str(value).strip()
            if value.upper().startswith('OG-'):
                return 'OG-' + value[3:]
            return f"OG-{value}"
        return value

class ParcelSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_phone = serializers.CharField(source='sender.phone', read_only=True)
    
    class Meta:
        model = Parcel
        fields = '__all__'

class ParcelTrackingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParcelTrackingLog
        fields = '__all__'

class WhatsAppLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppLog
        fields = '__all__'

class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = '__all__'
