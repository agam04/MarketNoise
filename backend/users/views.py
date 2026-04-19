from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserAPIKey
from .encryption import encrypt_key


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """POST /api/auth/register/ — Create a new user account."""
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response(
            {'error': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already taken.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(username=username, email=email, password=password)
    refresh = RefreshToken.for_user(user)

    return Response({
        'user': {'id': user.id, 'username': user.username, 'email': user.email},
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        },
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """GET /api/auth/profile/ — Get current user profile."""
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'date_joined': user.date_joined,
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_keys_list(request):
    """
    GET  /api/auth/apikeys/ — List user's stored API key services (masked).
    POST /api/auth/apikeys/ — Save or update an API key.
    """
    if request.method == 'GET':
        keys = UserAPIKey.objects.filter(user=request.user)
        return Response([
            {
                'service': k.service,
                'service_display': k.get_service_display(),
                'masked_key': k.masked_key(),
                'updated_at': k.updated_at,
            }
            for k in keys
        ])

    # POST — save or update
    service = request.data.get('service', '').strip()
    key_value = request.data.get('key', '').strip()

    if not service or not key_value:
        return Response(
            {'error': 'Both "service" and "key" are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_services = [s[0] for s in UserAPIKey.SERVICE_CHOICES]
    if service not in valid_services:
        return Response(
            {'error': f'Invalid service. Choose from: {", ".join(valid_services)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    encrypted = encrypt_key(key_value)

    obj, created = UserAPIKey.objects.update_or_create(
        user=request.user,
        service=service,
        defaults={'encrypted_key': encrypted},
    )

    return Response({
        'service': obj.service,
        'service_display': obj.get_service_display(),
        'masked_key': obj.masked_key(),
        'created': created,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def api_keys_detail(request, service):
    """DELETE /api/auth/apikeys/<service>/ — Remove an API key."""
    try:
        key = UserAPIKey.objects.get(user=request.user, service=service)
        key.delete()
        return Response({'deleted': True})
    except UserAPIKey.DoesNotExist:
        return Response(
            {'error': f'No key found for service: {service}'},
            status=status.HTTP_404_NOT_FOUND,
        )
