from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async


class VoucherConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f'voucher_user_{user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def voucher_available(self, event):
        if not await self._can_receive(event['voucher_id']):
            await self.close(code=4403)
            return
        await self.send_json({'type': 'voucher.available', 'voucher_id': event['voucher_id']})

    @database_sync_to_async
    def _can_receive(self, voucher_id):
        from django.contrib.auth import get_user_model
        from .models import VoucherDelivery
        from .voucher_delivery import eligible_vouchers_for
        user = get_user_model().objects.filter(pk=self.scope['user'].pk, is_active=True).first()
        if not user:
            return False
        delivery = VoucherDelivery.objects.filter(recipient=user, voucher_id=voucher_id).first()
        return bool(delivery and eligible_vouchers_for(user, delivery.recipient_role).filter(pk=voucher_id).exists())
