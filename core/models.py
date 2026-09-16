import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Hub(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hub = models.ForeignKey(Hub, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('hub_manager', 'Hub Manager'),
        ('delivery_agent', 'Delivery Agent'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='delivery_agent')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    hub = models.ForeignKey(Hub, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    
    STATUS_CHOICES = [
        ('At Hub', 'At Hub'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    ]
    delivery_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='At Hub')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class Parcel(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('at_origin_hub', 'At Origin Hub'),
        ('in_transit', 'In Transit'),
        ('at_destination_hub', 'At Destination Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking_number = models.CharField(max_length=100, unique=True)
    sender = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name='sent_parcels')
    receiver_name = models.CharField(max_length=255)
    receiver_phone = models.CharField(max_length=20)
    receiver_address = models.TextField()
    origin_hub = models.ForeignKey(Hub, on_delete=models.RESTRICT, related_name='origin_parcels')
    destination_hub = models.ForeignKey(Hub, on_delete=models.SET_NULL, null=True, blank=True, related_name='destination_parcels')
    current_hub = models.ForeignKey(Hub, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_parcels')
    assigned_delivery_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_parcels')
    
    item_description = models.TextField(null=True, blank=True)
    quantity = models.IntegerField(default=1)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    dimensions = models.CharField(max_length=100, null=True, blank=True)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='created')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='prepaid')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.tracking_number

class ParcelTrackingLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name='tracking_logs')
    status = models.CharField(max_length=50, choices=Parcel.STATUS_CHOICES)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    hub = models.ForeignKey(Hub, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parcel.tracking_number} - {self.status}"

class WhatsAppLog(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('booking_confirmed', 'Booking Confirmed'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('delayed', 'Delayed'),
        ('payment_received', 'Payment Received'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parcel = models.ForeignKey(Parcel, on_delete=models.CASCADE, related_name='whatsapp_logs')
    customer_phone = models.CharField(max_length=20)
    message_type = models.CharField(max_length=50, choices=MESSAGE_TYPE_CHOICES)
    message_body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    provider_message_id = models.CharField(max_length=255, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} for {self.customer_phone}"

class Setting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=255, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=500, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key
