from rest_framework import viewsets, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Organization, Membership
from .serializers import OrganizationSerializer, MembershipSerializer, RegisterOrganizationSerializer, UserSerializer, CustomTokenObtainPairSerializer
from .permissions import IsOrganizationMember, IsOwnerOrAdmin


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterOrganizationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterOrganizationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=201)


class MeView(generics.GenericAPIView):
    permission_classes = [IsOrganizationMember]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsOrganizationMember]

    def get_queryset(self):
        return Organization.objects.filter(id=self.request.user.current_organization_id)

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy', 'create']:
            return [IsOwnerOrAdmin()]
        return super().get_permissions()


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        return Membership.objects.filter(organization=self.request.user.current_organization).select_related('user', 'organization')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.current_organization)
