from channels.generic.websocket import AsyncJsonWebsocketConsumer


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
        await self.send_json({'type': 'voucher.available', 'voucher_id': event['voucher_id']})
