from rest_framework import serializers
from booking.models import PoojaBooking, PaymentHistory

class BookingStatusSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)


class BookingListSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username')
    pooja = serializers.CharField(source='pooja.name')

    class Meta:
        model = PoojaBooking
        fields = [
            'id', 'user', 'pooja', 'amount',
            'status', 'payment_method',
            'payment_status', 'booked_at', 'approved_at'
        ]


class PaymentHistorySerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source='booking.id')
    user = serializers.CharField(source='booking.user.username')

    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'booking_id', 'user',
            'amount', 'payment_mode',
            'status', 'confirmed_at'
        ]
# for drf         
class PaymentStatusUpdateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=['completed', 'failed', 'pending']
    )
    payment_method = serializers.ChoiceField(
        choices=['upi', 'upi_qr', 'cash']
    )