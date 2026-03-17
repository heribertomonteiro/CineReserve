from rest_framework import serializers
from ..models import Seat

class SeatStatusSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Seat
        fields = ['id', 'row', 'number', 'label', 'status']

    def get_status(self, obj):
        purchased = self.context.get('purchased_ids', set())
        reserved = self.context.get('reserved_ids', set())
        if obj.id in purchased:
            return 'purchased'
        if obj.id in reserved:
            return 'reserved'
        return 'available'