from rest_framework import viewsets, permissions
from knowledge.models import KnowledgeField
from .serializers import KnowledgeFieldSerializer

class KnowledgeFieldViewSet(viewsets.ModelViewSet):
    """API endpoint that allows user's knowledge fields to be viewed or edited."""
    serializer_class = KnowledgeFieldSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """This view should only return knowledge fields for the currently authenticated user."""
        return KnowledgeField.objects.filter(user=self.request.user)

    # Perform_create is handled by the serializer's create method
    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user) 