import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # This method is called when the WebSocket is first connected
        pass

    async def disconnect(self, close_code):
        # This method is called when the WebSocket is closed
        pass

    async def receive(self, text_data):
        # This method is called when a message is received from the WebSocket
        pass

    async def sync_status(self, event):
        \"\"\"
        Handles 'sync.status' messages pushed from the backend task.
        Sends the status update to the connected client.
        \"\"\"
        account_id = event['account_id']
        status = event['status']
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'sync_status', # Frontend can use this type field
            'payload': {
                'accountId': account_id,
                'status': status,
                'message': message
            }
        }))

    # Ensure this consumer type is registered in routing.py with the correct path
    # and that the group_name used in the task matches the group the user joins on connect. 