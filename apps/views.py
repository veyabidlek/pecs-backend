import random
from datetime import datetime

from django.contrib.auth import authenticate
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
from .application import play_sound
from .models import Care_recipient, Care_giver, Codes, Board, Category, Image, Tab, Image_positions, History
from .serializers import CaregiverSerializer, VerifyCodeSerializer, PlaySoundSerializer, BoardSerializer, \
    HistorySerializer, SignupSerializer, ImageSerializer, CategorySerializer, TabSerializer, \
    ImagePositionSerializer, CareRecipientSerializer


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


class GenerateCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Generate a new verification code for the authenticated user",
        responses={
            201: openapi.Response(
                description="Code generated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_STRING),
                        'time': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        Codes.objects.filter(user=request.user).delete()

        code = ' '.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
        now = datetime.now().strftime("%H:%M:%S")

        code_lib, created = Codes.objects.get_or_create(code=code, user=request.user, defaults={'time': now})

        return Response({
            "code": code_lib.code,
            "time": code_lib.time,
            "message": "Code generated successfully"
        }, status=status.HTTP_201_CREATED)


class VerifyCodeView(APIView):
    @swagger_auto_schema(
        request_body=VerifyCodeSerializer,
        responses={
            200: openapi.Response(
                description="Code verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Invalid request data",
            404: "Code not found"
        }
    )
    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        if serializer.is_valid():
            code_check = serializer.validated_data.get('code_check')

            try:
                code = Codes.objects.get(code=code_check)
            except Codes.DoesNotExist:
                return Response({'success': False, 'message': "Code not found. Please try again."},
                                status=status.HTTP_404_NOT_FOUND)

            user = request.user
            if is_caregiver(user):
                caregiver = Care_giver.objects.get(user=user)
                recipient = Care_recipient.objects.get(user=code.user)
                caregiver.recipients.add(recipient)
            elif is_recipient(user):
                caregiver = Care_giver.objects.get(user=code.user)
                recipient = Care_recipient.objects.get(user=user)
                caregiver.recipients.add(recipient)
            else:
                return Response({'success': False, 'message': "User role not recognized."},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({'success': True, 'message': "Code verified successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlaySoundView(APIView):

    @swagger_auto_schema(
        query_serializer=PlaySoundSerializer(),
        responses={
            200: openapi.Response(
                description="Sound played successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'board': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: "Invalid request data",
            404: "Board not found"
        }
    )
    def get(self, request):
        serializer = PlaySoundSerializer(data=request.GET)

        if serializer.is_valid():
            input_data = serializer.validated_data.get('input_data')
            board_id = serializer.validated_data.get('board_id')

            try:
                board = Board.objects.get(id=board_id)
                board_serializer = BoardSerializer(board)
            except Board.DoesNotExist:
                return Response({'success': False, 'message': "Board not found."}, status=status.HTTP_404_NOT_FOUND)

            user = request.user
            if user.is_authenticated:
                history_data = {
                    'text': input_data,
                    'date': datetime.today(),
                    'time': datetime.now().strftime("%H:%M:%S"),
                    'user': user.id,
                    'board': board.id
                }
                history_serializer = HistorySerializer(data=history_data)

                if history_serializer.is_valid():
                    history_serializer.save()
                else:
                    return Response(history_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            play_sound.playtext(input_data)
            return Response({
                'success': True,
                'message': "Sound played successfully.",
                'board': board_serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        care_recipient = Care_recipient.objects.get(user=request.user)
        serializer = CareRecipientSerializer(care_recipient)

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


class LibraryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get library categories and images",
        responses={
            200: openapi.Response(
                description="Library data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'current_path': openapi.Schema(type=openapi.TYPE_STRING),
                        'categories': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                     items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'images': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'private_imgs': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                       items=openapi.Schema(type=openapi.TYPE_OBJECT))
                    }
                )
            )
        }
    )
    def get(self, request):
        categories = Category.objects.all().order_by('name')
        public_categories = [cat for cat in categories if not cat.is_private()]
        private_categories = []

        if not request.user.is_staff:
            private_categories = list(Category.objects.filter(creator=request.user).order_by('name'))

        categories = public_categories + private_categories
        images_data = {}

        for category in categories:
            images_data[category.name] = Image.objects.filter(category=category).values('image').distinct()[:1]

        private_images = Image.objects.filter(creator=request.user).values('image', 'label').distinct()

        response_data = {
            'current_path': request.path,
            'categories': CategorySerializer(categories, many=True).data,
            'images': images_data,
            'private_imgs': list(private_images),  # Convert to list if needed
        }

        return Response(response_data)

    @swagger_auto_schema(
        request_body=ImageSerializer,
        responses={
            201: "Image uploaded successfully",
            400: "Invalid image data"
        }
    )
    def post(self, request):
        image_form = ImageSerializer(data=request.data)
        if image_form.is_valid():
            image = image_form.save(creator=request.user)
            return Response({"message": "Image uploaded successfully"}, status=201)

        return Response(image_form.errors, status=400)


class BoardCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get all boards for the authenticated user",
        responses={
            200: openapi.Response(
                description="Boards retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'boards': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                 items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            )
        }
    )
    def get(self, request):
        boards = Board.objects.filter(creator=request.user)
        serializer = BoardSerializer(boards, many=True)

        response_data = {
            'boards': serializer.data,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            201: "Board and default tab created successfully",
            400: "Board name is required",
            200: "Board already exists"
        }
    )
    def post(self, request):
        name = request.data.get('name')

        if not name:
            return Response({"error": "Board name is required."}, status=status.HTTP_400_BAD_REQUEST)

        board, created = Board.objects.get_or_create(name=name, creator=request.user)

        if created:
            Tab.objects.get_or_create(board=board, straps_num=5, name='Главная')
            return Response({"message": "Board and default tab created successfully."}, status=status.HTTP_201_CREATED)

        return Response({"message": "Board already exists."}, status=status.HTTP_200_OK)


category_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'images': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                    'image': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        'category': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'name': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
        'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN),
    }
)


class CategoryImageView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get images for a specific category",
        responses={
            200: category_response,
            404: openapi.Response(description="Category not found")
        },
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="Category ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ]
    )
    def get(self, request, id):
        try:
            category = Category.objects.get(id=id)
            images = Image.objects.filter(category=category).values('id', 'label', 'image').distinct()

            response_data = {
                'images': list(images),  # Convert to list for JSON serialization
                'category': {
                    'id': category.id,
                    'name': category.name,
                },
                'is_cr': is_recipient(request.user),
                'is_cg': is_caregiver(request.user),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Category.DoesNotExist:
            return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Add an image to a tab",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['image_id', 'tab'],
            properties={
                'image_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'tab': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        responses={
            201: openapi.Response(description="Image added successfully"),
            404: openapi.Response(description="Image or Tab not found"),
            400: openapi.Response(description="Invalid input")
        }
    )
    def post(self, request):
        add_image_form = ImageSerializer(data=request.data)

        if add_image_form.is_valid():
            image_id = request.data.get('image_id')
            tab_id = request.data.get('tab')

            try:
                image = Image.objects.get(id=image_id)
                tab = Tab.objects.get(id=tab_id)
                pos, created = Image_positions.objects.get_or_create(tab=tab, image=image, position_x='0',
                                                                     position_y='0')

                return Response({"message": "Image added to tab successfully."}, status=status.HTTP_201_CREATED)
            except Image.DoesNotExist:
                return Response({'error': 'Image not found.'}, status=status.HTTP_404_NOT_FOUND)
            except Tab.DoesNotExist:
                return Response({'error': 'Tab not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(add_image_form.errors, status=status.HTTP_400_BAD_REQUEST)


class BoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get detailed information about a board",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'tabs': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'is_cr': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'is_cg': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'tabs_img': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'categories': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                 items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'c_images': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'images': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'board_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            ),
            404: openapi.Response(description="Board not found")
        },
        manual_parameters=[
            openapi.Parameter(
                'board_id',
                openapi.IN_PATH,
                description="Board ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ]
    )
    def get(self, request, board_id):
        try:
            board = Board.objects.get(id=board_id)
        except Board.DoesNotExist:
            return Response({"error": "Board not found."}, status=status.HTTP_404_NOT_FOUND)

        public_categories = Category.objects.filter(creator__is_staff=True).order_by('name')
        private_categories = Category.objects.filter(creator=request.user).order_by('name')
        categories = public_categories | private_categories  # Combine public and user's private categories

        # Collect unique images and map them by category
        c_images = {category: ImageSerializer(Image.objects.filter(category=category).distinct()[:1], many=True).data
                    for category in categories}
        images = Image.objects.filter(category__in=categories)

        # Retrieve tabs for the board and associated image positions
        tabs = Tab.objects.filter(board=board).order_by('id')
        tabs_data = []
        for tab in tabs:
            tabs_img = ImagePositionSerializer(Image_positions.objects.filter(tab=tab).distinct(), many=True).data
            tabs_data.append({'tab': TabSerializer(tab).data, 'images': tabs_img})

        response_data = {
            'tabs': TabSerializer(tabs, many=True).data,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
            'tabs_img': tabs_data,
            'categories': CategorySerializer(categories, many=True).data,
            'c_images': c_images,
            'images': ImageSerializer(images, many=True).data,
            'board_id': board.id,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_description="Create a new tab in a board",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['name', 'straps', 'color'],
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'straps': openapi.Schema(type=openapi.TYPE_INTEGER),
                'color': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            201: openapi.Response(description="Tab created successfully"),
            404: openapi.Response(description="Board not found"),
            400: openapi.Response(description="Missing required fields")
        }
    )
    def post(self, request, board_id):
        try:
            board = Board.objects.get(id=board_id)
        except Board.DoesNotExist:
            return Response({"error": "Board not found."}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name')
        straps_num = request.data.get('straps')
        color = request.data.get('color')

        if not all([name, straps_num, color]):
            return Response({"error": "Missing fields for new tab creation."}, status=status.HTTP_400_BAD_REQUEST)

        new_tab, created = Tab.objects.get_or_create(
            name=name,
            board=board,
            color=color,
            straps_num=straps_num
        )
        return Response({"message": "Tab created successfully.", "tab": TabSerializer(new_tab).data},
                        status=status.HTTP_201_CREATED)


class BoardCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get category and its images",
        manual_parameters=[
            openapi.Parameter(
                'input_data',
                openapi.IN_QUERY,
                description="Category ID",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'category': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'category_images': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                }
            ),
            404: openapi.Response(description="Category not found"),
            400: openapi.Response(description="Category ID is required")
        }
    )
    def get(self, request):
        category_id = request.query_params.get("input_data")

        # Validate that category ID is provided
        if not category_id:
            return Response({"error": "Category ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get all images related to the category
        category_images = Image.objects.filter(category_id=category_id)

        # Serialize the category and images
        category_data = CategorySerializer(category).data
        category_images_data = ImageSerializer(category_images, many=True).data

        response_data = {
            'category': category_data,
            'category_images': category_images_data
        }

        return Response(response_data, status=status.HTTP_200_OK)


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


class BarCharsView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can access this view

    @swagger_auto_schema(
        operation_description="Get word count data per hour for a specific date",
        manual_parameters=[
            openapi.Parameter(
                'bar_date',
                openapi.IN_QUERY,
                description="Date for bar chart data (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATE,
                required=True
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'bar': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_INTEGER),
                        description="Array of 24 integers representing word counts for each hour"
                    ),
                }
            ),
            400: openapi.Response(description="Invalid date format or missing date parameter")
        }
    )
    def get(self, request):
        # Retrieve and format the date from request parameters
        received_date = request.query_params.get('bar_date')
        if not received_date:
            return Response({"error": "Date parameter 'bar_date' is required"}, status=400)

        try:
            received_date = datetime.strptime(received_date, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Expected YYYY-MM-DD."}, status=400)

        # Query and filter data based on the date and user
        bar_data = History.objects.filter(date=received_date, user=request.user).values('text', 'time')
        bar = []

        for hour in range(0, 24):
            word_count = sum(
                len(d['text'].split()) for d in bar_data if d['time'].hour == hour
            )
            bar.append(word_count)

        return Response({'bar': bar}, status=200)


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view

    @swagger_auto_schema(
        operation_description="Get user progress statistics",
        responses={
            200: openapi.Response(
                description="Progress data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'histories': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                    items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'is_recipient': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'board_names': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                      items=openapi.Schema(type=openapi.TYPE_STRING)),
                        'board_representation': openapi.Schema(type=openapi.TYPE_ARRAY,
                                                               items=openapi.Schema(type=openapi.TYPE_NUMBER))
                    }
                )
            )
        }
    )
    def get(self, request):
        # categories = Category.objects.values('id', 'name')
        histories = list(History.objects.filter(user=request.user.id).values('text', 'date', 'time'))[::-1]
        boards = Board.objects.filter(creator=request.user)

        boards_h = History.objects.filter(user=request.user).values('board', 'text')
        b = []  # List of board names
        rep = []  # List of representation percentages for each board

        for board in boards:
            count = 0
            b.append(board.name)
            for bh in boards_h:
                if board.id == bh['board']:
                    count += 1
            if len(boards_h) > 0:
                rep.append(count / len(boards_h) * 100)
            else:
                rep.append(0)

        data = {
            'histories': histories,
            'is_recipient': is_recipient(request.user),
            'board_names': b,
            'board_representation': rep,
        }

        return Response(data, status=200)


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
