from rest_framework import serializers
from ..models import Seat

class SeatStatusSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    label = serializers.CharField(read_only=True)

    class Meta:
        model = Seat
        fields = ['id', 'row', 'number', 'label', 'status']

    def get_status(self, obj):
        sold = self.context.get('sold_ids', set())
        locked = self.context.get('locked_ids', set())
        if obj.id in sold:
            return 'sold'
        if obj.id in locked:
            return 'locked'
        return 'available'