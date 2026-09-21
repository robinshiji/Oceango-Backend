from rest_framework import viewsets, views, status
from rest_framework.decorators import action
import pandas as pd
import re
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum
from .models import User, Hub, Customer, Parcel, ParcelTrackingLog, WhatsAppLog, Setting
from .serializers import (
    UserSerializer, HubSerializer, CustomerSerializer, 
    ParcelSerializer, ParcelTrackingLogSerializer, 
    WhatsAppLogSerializer, SettingSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class HubViewSet(viewsets.ModelViewSet):
    queryset = Hub.objects.all()
    serializer_class = HubSerializer
    permission_classes = [IsAuthenticated]

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    
    def get_queryset(self):
        return Customer.objects.filter(deleted_at__isnull=True)
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if they are linked to any ACTIVE parcels
        linked_customers = Customer.objects.filter(id__in=ids, sent_parcels__deleted_at__isnull=True).distinct()
        if linked_customers.exists():
            return Response(
                {"error": "Cannot delete some customers because they have active linked shipments."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            Customer.objects.filter(id__in=ids).update(deleted_at=now())
            return Response({"message": f"{len(ids)} customers moved to trash"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Prevent deletion if customer has linked active parcels
        if instance.sent_parcels.filter(deleted_at__isnull=True).exists():
            return Response(
                {"error": "Cannot delete customer because they have active linked shipment."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        instance.deleted_at = now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def trash(self, request):
        # Lazy cleanup of items older than 30 days
        thirty_days_ago = now() - timedelta(days=30)
        Customer.objects.filter(deleted_at__lt=thirty_days_ago).delete()
        
        trashed_customers = Customer.objects.filter(deleted_at__isnull=False)
        serializer = self.get_serializer(trashed_customers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = Customer.objects.filter(pk=pk).first()
        if not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
        instance.deleted_at = None
        instance.save()
        return Response({"status": "restored"})

    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        instance = Customer.objects.filter(pk=pk).first()
        if not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        if instance.sent_parcels.filter(deleted_at__isnull=True).exists():
            return Response(
                {"error": "Cannot permanently delete this customer because they have active linked shipments."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Unlink trashed parcels to avoid ProtectedError
        instance.sent_parcels.filter(deleted_at__isnull=False).update(sender=None)
            
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def empty_trash(self, request):
        # Only permanently delete customers that do NOT have any active linked parcels
        # Find trashed customers who don't have any parcels where deleted_at is null
        trashed = Customer.objects.filter(deleted_at__isnull=False)
        active_customers = Customer.objects.filter(sent_parcels__isnull=False, sent_parcels__deleted_at__isnull=True)
        unlinked_customers = trashed.exclude(id__in=active_customers)
        
        # Unlink trashed parcels to prevent ProtectedError
        Parcel.objects.filter(sender__in=unlinked_customers, deleted_at__isnull=False).update(sender=None)
        
        count, _ = unlinked_customers.delete()
        
        # Check if there were customers we couldn't delete
        linked_count = trashed.filter(id__in=active_customers).count()
        message = f"{count} customers permanently deleted."
        if linked_count > 0:
            message += f" {linked_count} customers were skipped because they have active linked shipments."
            
        return Response({"message": message}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def upload_excel(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        file = request.FILES['file']
        
        try:
            df = pd.read_excel(file)
            
            # Expected columns based on new template: customer id, name&contact, address
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            required_cols = ['customer id', 'name&contact', 'address']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                return Response({
                    "error": f"Missing required columns: {', '.join(missing_cols)}"
                }, status=status.HTTP_400_BAD_REQUEST)
                
            created_count = 0
            skipped_count = 0
            
            for index, row in df.iterrows():
                customer_id = str(row['customer id']).strip() if pd.notna(row['customer id']) else ''
                if customer_id:
                    if customer_id.upper().startswith('OG-'):
                        customer_id = 'OG-' + customer_id[3:]
                    else:
                        customer_id = f"OG-{customer_id}"
                        
                address = str(row['address']).strip() if pd.notna(row['address']) else ''
                name_and_contact = str(row['name&contact']).strip() if pd.notna(row['name&contact']) else ''
                
                # Parse name and contact
                # Look for a phone number (at least 7 digits, possibly with +, -, spaces, or parentheses) at the end
                phone = ""
                name = name_and_contact
                
                match = re.search(r'([\d\s\+\-\(\)]{7,})$', name_and_contact)
                if match:
                    phone = match.group(1).strip()
                    name = name_and_contact[:match.start()].strip()
                    # Clean trailing punctuation
                    name = re.sub(r'[\,\-\:]+$', '', name).strip()
                else:
                    # Alternative: maybe phone is at the beginning
                    match = re.match(r'^([\d\s\+\-\(\)]{7,})', name_and_contact)
                    if match:
                        phone = match.group(1).strip()
                        name = name_and_contact[match.end():].strip()
                        name = re.sub(r'^[\,\-\:]+', '', name).strip()

                if not phone:
                    skipped_count += 1
                    continue
                
                # Clean up phone numbers to match exact formatting if needed, but saving as provided
                
                # Check if customer already exists by phone
                if Customer.objects.filter(phone=phone).exists():
                    skipped_count += 1
                    continue
                    
                if not name or not address:
                    skipped_count += 1
                    continue
                    
                Customer.objects.create(
                    tracking_id=customer_id,
                    name=name,
                    phone=phone,
                    address=address,
                    city='' # City not provided in this specific template
                )
                created_count += 1
                
            return Response({
                "message": "Upload successful",
                "created": created_count,
                "skipped": skipped_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ParcelViewSet(viewsets.ModelViewSet):
    queryset = Parcel.objects.all()

    def get_queryset(self):
        return Parcel.objects.filter(deleted_at__isnull=True)
    serializer_class = ParcelSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        parcel = serializer.save()
        
        request = self.request
        receiver_customer_id = request.data.get('receiver_customer_id', '')
        if receiver_customer_id:
            receiver_customer_id = str(receiver_customer_id).strip()
            if receiver_customer_id.upper().startswith('OG-'):
                receiver_customer_id = 'OG-' + receiver_customer_id[3:]
            else:
                receiver_customer_id = f"OG-{receiver_customer_id}"
        
        # Automatically create or update a Customer record for the receiver
        if parcel.receiver_name and parcel.receiver_phone:
            customer = Customer.objects.filter(phone=parcel.receiver_phone).first()
            if customer:
                # Do NOT overwrite their tracking_id. It is their permanent Customer ID.
                customer.name = parcel.receiver_name
                customer.address = parcel.receiver_address
                # Only set hub if they don't have one
                if not customer.hub:
                    customer.hub = parcel.destination_hub or parcel.origin_hub
                customer.save()
            else:
                # Require a manual Customer ID
                if not receiver_customer_id:
                    raise serializers.ValidationError({"receiver_customer_id": "Receiver Customer ID is required for new customers."})
                    
                Customer.objects.create(
                    tracking_id=receiver_customer_id,
                    name=parcel.receiver_name,
                    phone=parcel.receiver_phone,
                    address=parcel.receiver_address,
                    hub=parcel.destination_hub or parcel.origin_hub
                )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted_at = now()
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def trash(self, request):
        thirty_days_ago = now() - timedelta(days=30)
        Parcel.objects.filter(deleted_at__lt=thirty_days_ago).delete()
        
        trashed_parcels = Parcel.objects.filter(deleted_at__isnull=False)
        serializer = self.get_serializer(trashed_parcels, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = Parcel.objects.filter(pk=pk).first()
        if not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
        instance.deleted_at = None
        instance.save()
        return Response({"status": "restored"})

    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        instance = Parcel.objects.filter(pk=pk).first()
        if not instance:
            return Response(status=status.HTTP_404_NOT_FOUND)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def empty_trash(self, request):
        count, _ = Parcel.objects.filter(deleted_at__isnull=False).delete()
        return Response({"message": f"{count} parcels permanently deleted"}, status=status.HTTP_200_OK)

class ParcelTrackingLogViewSet(viewsets.ModelViewSet):
    queryset = ParcelTrackingLog.objects.all()
    serializer_class = ParcelTrackingLogSerializer
    permission_classes = [IsAuthenticated]

class WhatsAppLogViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppLog.objects.all()
    serializer_class = WhatsAppLogSerializer
    permission_classes = [IsAuthenticated]

class SettingViewSet(viewsets.ModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated]

class DashboardStatsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        total_parcels = Parcel.objects.filter(deleted_at__isnull=True).count()
        delivered_30d = Parcel.objects.filter(status='delivered', created_at__gte=thirty_days_ago).count()
        active_deliveries = Parcel.objects.filter(status__in=['in_transit', 'at_origin_hub', 'at_destination_hub', 'out_for_delivery']).count()
        
        pending_cod_agg = Parcel.objects.filter(payment_method='cod', payment_status='pending').aggregate(Sum('cod_amount'))
        pending_cod = pending_cod_agg['cod_amount__sum'] or 0

        # Chart Data: parcels created per day for last 7 days (simplification for mock)
        chart_data = []
        for i in range(7):
            d = today - timedelta(days=6-i)
            day_name = d.strftime('%a')
            # rough count per day
            count = Parcel.objects.filter(created_at__date=d.date()).count()
            chart_data.append({"name": day_name, "deliveries": count})

        # Recent Parcels
        recent_parcels_qs = Parcel.objects.select_related('sender', 'assigned_delivery_agent').order_by('-created_at')[:4]
        recent_parcels = []
        for p in recent_parcels_qs:
            recent_parcels.append({
                'id': p.tracking_number,
                'sender': p.sender.name if p.sender else 'Unknown',
                'receiver': p.receiver_name,
                'status': p.get_status_display(),
                'driver': p.assigned_delivery_agent.name if p.assigned_delivery_agent else '-'
            })

        return Response({
            'kpis': {
                'total_parcels': total_parcels,
                'delivered_30d': delivered_30d,
                'active_deliveries': active_deliveries,
                'pending_cod': pending_cod
            },
            'chart_data': chart_data,
            'recent_parcels': recent_parcels
        })
