from django.contrib.auth import authenticate
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from . import models
from .models import Care_recipient, Care_giver
from .serializers import CaregiverSerializer, SignupSerializer, CareRecipientSerializer


class CaregiverProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get the profile information of the authenticated caregiver",
        responses={
            200: openapi.Response(
                description="Caregiver profile retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Username of the user"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email",
                                                description="Email of the user"),
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="First name of the user"),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING, description="Last name of the user"),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description="Indicates if the user is active"),
                        "date_joined": openapi.Schema(type=openapi.TYPE_STRING, format="date-time",
                                                      description="Date when the user joined"),
                        "is_cg": openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                description="Indicates if the user is a caregiver"),
                        "care_receivers": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user": openapi.Schema(type=openapi.TYPE_STRING,
                                                           description="Username of the care_receiver"),
                                    "user_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                              description="ID of the care_receiver user"),
                                    "profile_picture": openapi.Schema(type=openapi.TYPE_STRING, format="url",
                                                                      description="URL to the care_receiver's profile picture"),
                                }
                            ),
                            description="List of care_receivers associated with the care giver"
                        )
                    }
                )
            ),
            404: openapi.Response(description="Caregiver not found")
        }
    )
    def get(self, request):
        # try:
        user = request.user
        caregiver = Care_giver.objects.get(user=request.user)
        serializer = CaregiverSerializer(caregiver)

        profile_data = {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            'is_cg': True,
        }

        profile_data.update(serializer.data)

        return Response(profile_data, status=status.HTTP_200_OK)

    # except Care_giver.DoesNotExist:
    #     return Response({'detail': 'Caregiver not found.'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'd1': openapi.Schema(type=openapi.TYPE_STRING),
                'd2': openapi.Schema(type=openapi.TYPE_STRING),
                'd3': openapi.Schema(type=openapi.TYPE_STRING),
                'd4': openapi.Schema(type=openapi.TYPE_STRING),
                'd5': openapi.Schema(type=openapi.TYPE_STRING),
                'd6': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: "Code verified successfully",
            400: "Invalid code"
        }
    )
    def post(self, request):
        d1 = request.data.get('d1', '')
        d2 = request.data.get('d2', '')
        d3 = request.data.get('d3', '')
        d4 = request.data.get('d4', '')
        d5 = request.data.get('d5', '')
        d6 = request.data.get('d6', '')

        code_check = d1 + d2 + d3 + " " + d4 + d5 + d6
        print("check", code_check)

        # Assuming verify_code returns True/False or a message
        verification_result = verify_code(request, code_check)
        if verification_result:
            return Response({'detail': 'Code verified successfully.'}, status=status.HTTP_200_OK)
        return Response({'detail': 'Invalid code.'}, status=status.HTTP_400_BAD_REQUEST)


class CaregiverRecipientView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only logged-in users can access this

    @swagger_auto_schema(
        operation_description="Get recipients associated with a caregiver",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'recipients': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            ),
            404: openapi.Response(description="Caregiver not found")
        }
    )
    def get(self, request):
        try:
            caregiver = Care_giver.objects.get(user=request.user)
            recipients = caregiver.recipients.all()
        except Care_giver.DoesNotExist:
            return Response({"error": "Caregiver not found"}, status=404)

        serializer = CareRecipientSerializer(recipients, many=True)
        return Response({"recipients": serializer.data}, status=200)


def is_recipient(user):
    return user.groups.filter(name='RECIPIENT').exists()


def is_caregiver(user):
    return user.groups.filter(name='CAREGIVER').exists()


def verify_code(request, code_check):
    try:
        code = models.Codes.objects.get(code=code_check)
    except models.Codes.DoesNotExist:
        return {'success': False, 'message': "Code not found. Please try again."}

    if is_caregiver(request.user):
        caregiver = models.Care_giver.objects.get(user=request.user.id)
        recipient = models.Care_recipient.objects.get(user=code.user.id)
        caregiver.recipients.add(recipient)
    elif is_recipient(request.user):
        caregiver = models.Care_giver.objects.get(user=code.user.id)
        recipient = models.Care_recipient.objects.get(user=request.user.id)
        caregiver.recipients.add(recipient)
    else:
        return {'success': False, 'message': "User role not recognized."}

    return {'success': True, 'message': "Code verified successfully."}


class IndexView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    @swagger_auto_schema(
        operation_description="Get user role information",
        responses={
            200: openapi.Response(
                description="User role information retrieved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            )
        }
    )
    def get(self, request):
        is_cr = Care_recipient.objects.filter(user=request.user).exists()
        is_cg = Care_giver.objects.filter(user=request.user).exists()

        data = {
            'is_cr': is_cr,
            'is_cg': is_cg,
        }
        return Response(data)


class RecipientProfileView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    @swagger_auto_schema(
        operation_description="Get the profile information of the authenticated care recipient",
        responses={
            200: openapi.Response(
                description="Care recipient profile retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING, description="Username of the user"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email",
                                                description="Email of the user"),
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="First name of the user"),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING, description="Last name of the user"),
                        "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                    description="Indicates if the user is active"),
                        "date_joined": openapi.Schema(type=openapi.TYPE_STRING, format="date-time",
                                                      description="Date when the user joined"),
                        "is_cr": openapi.Schema(type=openapi.TYPE_BOOLEAN,
                                                description="Indicates if the user is a care recipient"),
                        "caregivers": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "user": openapi.Schema(type=openapi.TYPE_STRING,
                                                           description="Username of the caregiver"),
                                    "user_id": openapi.Schema(type=openapi.TYPE_INTEGER,
                                                              description="ID of the caregiver user"),
                                    "profile_picture": openapi.Schema(type=openapi.TYPE_STRING, format="url",
                                                                      description="URL to the caregiver's profile picture"),
                                }
                            ),
                            description="List of caregivers associated with the care recipient"
                        )
                    }
                )
            ),
            404: openapi.Response(description="Care recipient profile not found"),
        }
    )
    def get(self, request):
        user = request.user  # `request.user` will be set automatically by the JWTAuthentication

        try:
            care_recipient = Care_recipient.objects.get(user=user)
        except Care_recipient.DoesNotExist:
            raise Http404("Care recipient profile not found.")

        # Serialize the care_recipient object
        serializer = CareRecipientSerializer(care_recipient)

        # Profile data to return
        profile_data = {
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            'is_cr': True,
        }
        profile_data.update(serializer.data)
        return Response(profile_data, status=status.HTTP_200_OK)


class LoginUserView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format='password')
            }
        ),
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_type': openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=['recipient', 'caregiver', 'unknown']
                        ),
                        'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'username': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            401: "Invalid credentials"
        }
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_type': 'recipient' if is_recipient(user) else 'caregiver' if is_caregiver(user) else 'unknown',
                'user_id': user.id,
                'username': user.username,
            }
            return Response(data, status=status.HTTP_200_OK)

        return Response(
            {'error': _("Invalid username or password.")},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutUserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh_token'],
            properties={
                'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid token"
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response({'error': 'Refresh token is required.'},
                                status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': 'Successfully logged out.'},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {'error': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SignupUserView(APIView):
    @swagger_auto_schema(
        request_body=SignupSerializer,
        responses={
            201: openapi.Response(description="User created successfully!"),
            400: "Validation errors"
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Create the user
            return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecipientProfileCaregiverView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get caregivers associated with a recipient",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'caregivers': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            ),
            404: openapi.Response(description="Care recipient profile not found")
        }
    )
    def get(self, request):
        try:
            # Get the Care_recipient object associated with the logged-in user
            recipient = Care_recipient.objects.get(user=request.user)
        except Care_recipient.DoesNotExist:
            return Response({"error": "Care recipient profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve caregivers associated with this recipient
        caregivers = Care_giver.objects.filter(recipients=recipient)
        if not caregivers.exists():
            return Response({"message": "No caregivers associated with this profile."}, status=status.HTTP_200_OK)

        # Serialize the caregiver data
        caregivers_data = CaregiverSerializer(caregivers, many=True).data
        return Response({"caregivers": caregivers_data}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get user profile information",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user': openapi.Schema(type=openapi.TYPE_STRING),
                    'profile_url': openapi.Schema(type=openapi.TYPE_STRING),
                }
            ),
            400: openapi.Response(description="User role not recognized")
        }
    )
    def get(self, request):
        if is_recipient(request.user):
            user = 'recipient'
            profile_url = reverse('recipient_profile')
        elif is_caregiver(request.user):
            user = 'caregiver'
            profile_url = reverse('caregiver_profile')
        else:
            return Response({"error": "User role not recognized"}, status=status.HTTP_400_BAD_REQUEST)
        data = {"user": user, "profile_url": profile_url}

        return Response(data, status=status.HTTP_200_OK)
