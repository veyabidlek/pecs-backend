from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import models
from .application import play_sound
from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext as _

from datetime import datetime
import random

from .models import Care_recipient, Care_giver, Codes, Board, Category, Image, Tab, Image_positions, History
from .serializers import CaregiverSerializer, VerifyCodeSerializer, PlaySoundSerializer, BoardSerializer, \
    HistorySerializer, SignupSerializer, ImageSerializer, CategorySerializer, TabSerializer, \
    ImagePositionSerializer, CareRecipientSerializer


class CaregiverProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            caregiver = Care_giver.objects.get(user=request.user)
            serializer = CaregiverSerializer(caregiver)
            data = {
                'is_cg': True,
                'caregiver': serializer.data,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Care_giver.DoesNotExist:
            return Response({'detail': 'Caregiver not found.'}, status=status.HTTP_404_NOT_FOUND)

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

    def get(self, request):
        care_recipient = Care_recipient.objects.get(user=request.user)
        serializer = CareRecipientSerializer(care_recipient)
        data = {
            'is_cr': True,
            'caregiver': serializer.data,
        }
        return Response(data, status=status.HTTP_200_OK)


class LoginUserView(APIView):
    permission_classes = [AllowAny]  # Allow any user to access this endpoint

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        #
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)  # Generate or get the user's token

            data = {
                'token': token.key,  # Return the token in the response
                'user_type': 'recipient' if is_recipient(user) else 'caregiver' if is_caregiver(user) else 'unknown'
            }
            return Response(data, status=200)  # Respond with 200 OK and user information
        else:
            return Response({'error': _("Неправильный логин или пароль! Попробуйте снова.")},
                            status=400)  # Bad request response


class LogoutUserView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        logout(request)  # Log out the user
        return Response({'message': 'Successfully logged out.'}, status=200)  # Success response


class SignupUserView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Create the user
            return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LibraryView(APIView):
    permission_classes = [IsAuthenticated]

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

    def post(self, request):
        image_form = ImageSerializer(data=request.data)
        if image_form.is_valid():
            image = image_form.save(creator=request.user)
            return Response({"message": "Image uploaded successfully"}, status=201)

        return Response(image_form.errors, status=400)


class CategoryImageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, name, id):
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


class BoardCollectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        boards = Board.objects.filter(creator=request.user)
        serializer = BoardSerializer(boards, many=True)

        response_data = {
            'boards': serializer.data,
            'is_cr': is_recipient(request.user),
            'is_cg': is_caregiver(request.user),
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        name = request.data.get('name')

        if not name:
            return Response({"error": "Board name is required."}, status=status.HTTP_400_BAD_REQUEST)

        board, created = Board.objects.get_or_create(name=name, creator=request.user)

        if created:
            Tab.objects.get_or_create(board=board, straps_num=5, name='Главная')
            return Response({"message": "Board and default tab created successfully."}, status=status.HTTP_201_CREATED)

        return Response({"message": "Board already exists."}, status=status.HTTP_200_OK)


class BoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

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
