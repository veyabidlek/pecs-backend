from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import forms, models
from django.contrib import messages
from django.contrib.auth.models import User, Group
from .application import play_sound, verification
from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext as _  # For translations

import datetime
from auth_token import utils
from django.core.serializers.json import DjangoJSONEncoder
import json
import random

from .models import Care_recipient, Care_giver, Codes, Board, Category, Image, Tab, Image_positions, History
from .serializers import CaregiverSerializer, VerifyCodeSerializer, PlaySoundSerializer, BoardSerializer, \
    HistorySerializer, SignupSerializer, ImageSerializer, CategorySerializer, TabSerializer, \
    ImagePositionSerializer, CareRecipientSerializer


class CaregiverProfileView(APIView):
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


# def caregiver_profile_view(request):
#     try:
#         caregiver = models.Care_giver.objects.get(user=request.user)
#         recipients = caregiver.recipients.all()
#     except models.Care_giver.DoesNotExist:
#         recipients = None
#
#     if request.method == 'POST':
#         d1 = str(request.POST.get('d1'))
#         d2 = str(request.POST.get('d2'))
#         d3 = str(request.POST.get('d3'))
#         d4 = str(request.POST.get('d4'))
#         d5 = str(request.POST.get('d5'))
#         d6 = str(request.POST.get('d6'))
#
#         code_check = d1 + d2 + d3 + " " + d4 + d5 + d6
#         print("check", code_check)
#         verify_code(request, code_check)
#     dict = {'caregiver': caregiver,
#             'is_cg': True,
#             'recipients': recipients,
#             }
#     return render(request, 'caregiver_profile_page.html', dict)

# def caregiver_profile_view(request):
#     def get(self, request):
#         data = {
#             'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user),
#         }
#         return JsonResponse(data)

# class RecipientProfileCaregiverView(APIView):
#     def get(self, request):
#         try:
#             # Fetch the recipient based on the logged-in user
#             recipient = Care_recipient.objects.get(user=request.user)
#             # Get caregivers associated with this recipient
#             caregivers = Care_giver.objects.filter(recipients=recipient)
#             # Serialize the caregiver data
#             serializer = CaregiverSerializer(caregivers, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#
#         except Care_recipient.DoesNotExist:
#             return Response({"error": "Recipient not found"}, status=status.HTTP_404_NOT_FOUND)


class GenerateCodeView(APIView):
    def post(self, request):
        Codes.objects.filter(user=request.user.id).delete()
        # return Response({"message": "Message"})
        # codes.delete()
        code = ' '.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
        now = datetime.datetime.now().strftime("%H:%M:%S")
        code_lib, created = Codes.objects.get_or_create(code=code, user=request.user, defaults={'time': now})
        return Response({"code": code_lib.code, "time": code_lib.time, "message": "Code generated successfully"},
                        status=status.HTTP_201_CREATED)


# def generate_code(request):
#     codes = models.Codes.objects.filter(user=request.user.id)
#     codes.delete()
#     code = ' '.join([str(random.randint(0, 999)).zfill(3) for _ in range(2)])
#     now = datetime.datetime.now().strftime("%H:%M:%S")
#     code_lib = models.Codes.objects.get_or_create(code=code, user=request.user, time=now)
#     return render(request, 'generate_code.html', {'code': code})


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

            # Perform role-based checks
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


class PlaySoundView(APIView):
    def get(self, request):
        serializer = PlaySoundSerializer(data=request.GET)

        if serializer.is_valid():
            input_data = serializer.validated_data.get('input_data')
            board_id = serializer.validated_data.get('board_id')

            # Fetch and serialize board instance
            try:
                board = Board.objects.get(id=board_id)
                board_serializer = BoardSerializer(board)
            except Board.DoesNotExist:
                return Response({'success': False, 'message': "Board not found."}, status=status.HTTP_404_NOT_FOUND)

            # Log history if user is authenticated
            user = request.user
            if user.is_authenticated:
                history_data = {
                    'text': input_data,
                    'date': datetime.date.today(),
                    'time': datetime.datetime.now().strftime("%H:%M:%S"),
                    'user': user.id,  # Send ID to link with user FK
                    'board': board.id  # Send ID to link with board FK
                }
                history_serializer = HistorySerializer(data=history_data)

                if history_serializer.is_valid():
                    history_serializer.save()
                else:
                    return Response(history_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Call playtext function to play sound
            play_sound.playtext(input_data)
            return Response({
                'success': True,
                'message': "Sound played successfully.",
                'board': board_serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# def call_play_sound(req):
#     today = datetime.date.today()
#     now = datetime.datetime.now().strftime("%H:%M:%S")
#     if req.method == 'GET':
#         # write_data.py write_csv()Call the method.
#         # Of the data sent by ajax"input_data"To get by specifying.
#         # voice = models.Board.objects.filter(name="PECS Board").values('voice_choice')
#         # voice = voice[0]['voice_choice']
#         text = req.GET.get("input_data")
#         board_id = req.GET.get("board_id")
#         board = models.Board.objects.get(id=board_id)
#         print(text)
#         user = req.user
#         if user is not None:
#             history = models.History(text=text, date=today, time=now, user=user, board=board)
#             history.save()
#         play_sound.playtext(text)
#         return HttpResponse()


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


# Create your views here.
# def index_view(request):
#     dict = {'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user), }
#     return render(request, 'index.html', dict)


class RecipientProfileView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request):
        is_cr = Care_recipient.objects.filter(user=request.user).exists()
        is_cg = Care_giver.objects.filter(user=request.user).exists()

        data = {
            'is_cr': is_cr,
            'is_cg': is_cg,
        }
        return Response(data)


# def recipient_profile_view(request):
#     recipient = models.Care_recipient.objects.get(user=request.user)
#     try:
#         caregivers = models.Care_giver.objects.filter(recipients=recipient)
#     except models.Care_giver.DoesNotExist:
#         caregivers = None
#     if request.method == 'POST':
#         d1 = str(request.POST.get('d1'))
#         d2 = str(request.POST.get('d2'))
#         d3 = str(request.POST.get('d3'))
#         d4 = str(request.POST.get('d4'))
#         d5 = str(request.POST.get('d5'))
#         d6 = str(request.POST.get('d6'))
#
#         code_check = d1 + d2 + d3 + " " + d4 + d5 + d6
#         print("check", code_check)
#         verify_code(request, code_check)
#
#     dict = {'recipient': recipient,
#             'is_cr': True,
#             'caregivers': caregivers,
#             }
#     return render(request, 'recipient_profile_page.html', dict)

# def recipient_profile_view(request):
#     dict = {'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user), }
#     return render(request, 'recipient_profile_page.html', dict)


class LoginUserView(APIView):
    permission_classes = [AllowAny]  # Allow any user to access this endpoint

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)

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


# def login_user_view(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
#
#         if user is not None:
#             login(request, user)
#             if is_recipient(user):
#                 return redirect('recipient_profile')
#             elif is_caregiver(user):
#                 return redirect('caregiver_profile')
#         else:
#             messages.success(request, ("Неправильный логин или пароль! Попробуйте снова."))
#     return render(request, 'login_page.html', {})
class LogoutUserView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        logout(request)  # Log out the user
        return Response({'message': 'Successfully logged out.'}, status=200)  # Success response


# def logout_user_view(request):
#     logout(request)
#     return redirect('home')


class SignupUserView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Create the user
            return Response({"message": "User created successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# def signup_user_view(request):
#     if request.method == 'POST':
#         role = request.POST.get('role')
#         form = forms.SignupForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             user.set_password(user.password)
#             user.save()
#             if role == 'cg_role':
#                 cg, cg_created = models.Care_giver.objects.get_or_create(user=user)
#                 my_group = Group.objects.get_or_create(name='CAREGIVER')
#                 my_group[0].user_set.add(user)
#             elif role == 'cr_role':
#                 cr, cr_created = models.Care_recipient.objects.get_or_create(user=user)
#                 my_group = Group.objects.get_or_create(name='RECIPIENT')
#                 my_group[0].user_set.add(user)
#             return redirect('login')
#         else:
#             messages.success(request, "Такое имя пользователя уже существует. Попробуйте снова.")
#     else:
#         form = forms.SignupForm()
#     dict = {'signupForm': form}
#     return render(request, 'signup_page.html', dict)

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


# def library_view(request):
#     folderForm = forms.FolderForm()
#     imageForm = forms.ImageForm()
#     public_categories = []
#     private_categories = []
#     categories = models.Category.objects.all().order_by('name')
#     for category in categories:
#         if not category.is_private():
#             public_categories.append(category)
#     if not request.user.is_staff:
#         private_categories = list(models.Category.objects.filter(creator=request.user.id).order_by('name'))
#     categories = public_categories + private_categories
#     images = {}
#     for category in categories:
#         images[category] = models.Image.objects.filter(category=category).values('image').distinct()[:1]
#     private_images = models.Image.objects.filter(creator=request.user.id).values('image', 'label').distinct()
#     dict = {'current_path': request.path,
#             'categories': categories,
#             'images': images,
#             'imageForm': imageForm,
#             'folderForm': folderForm,
#             'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user),
#             'private_imgs': private_images,
#             }
#     if request.method == 'POST':
#         imageForm = forms.ImageForm(request.POST, request.FILES)
#         folderForm = forms.FolderForm(request.POST)
#         if imageForm.is_valid():
#             image = imageForm.save(commit=False)
#             image.creator = request.user
#             image.category = models.Category.objects.get(id=request.POST.get('category'))
#             print(image.category)
#
#             if not image.creator.is_staff:
#                 image.public = False
#             image.save()
#
#         if folderForm.is_valid():
#             folder = folderForm.save(commit=False)
#             folder.creator = request.user
#             folder.save()
#         return HttpResponseRedirect('library')
#     return render(request, 'library.html', dict)


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


# def category_image(request, name, id):
#     addimageForm = forms.AddForm()
#     category = models.Category.objects.get(id=id)
#     images = models.Image.objects.filter(category=category).values('id', 'label', 'image').distinct()
#     dict = {'images': images,
#             'addimageForm': addimageForm,
#             'category': category,
#             'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user),
#             }
#     if request.method == 'POST':
#         addimageForm = forms.AddForm(request.POST)
#         if addimageForm.is_valid():
#             image_id = request.POST.get('image_id')
#             tab_id = request.POST.get('tab')
#             image = models.Image.objects.get(id=image_id)
#             tab = models.Tab.objects.get(id=tab_id)
#             pos = models.Image_positions.objects.get_or_create(tab=tab, image=image, position_x='0', position_y='0')
#         return HttpResponseRedirect(str(id))
#     return render(request, 'category_images.html', dict)


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


# def board_collection_view(request):
#     boards = models.Board.objects.filter(creator=request.user.id)
#     dict = {'boards': boards,
#             'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user),
#             }
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         board = models.Board.objects.get_or_create(name=name, creator=request.user)
#         tab = models.Tab.objects.get_or_create(board=board[0], straps_num=5, name='Главная')
#     return render(request, 'board_collection.html', dict)

class BoardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            board = Board.objects.get(id=id)
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

    def post(self, request, id):
        try:
            board = Board.objects.get(id=id)
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


# def board_view(request, id):
#     board = models.Board.objects.get(id=id)
#
#     public_categories = []
#     private_categories = []
#     categories = models.Category.objects.all().order_by('name')
#     for category in categories:
#         if not category.is_private():
#             public_categories.append(category)
#     if not request.user.is_staff:
#         private_categories = list(models.Category.objects.filter(creator=request.user.id).order_by('name'))
#     categories = public_categories + private_categories
#     c_images = {}
#     images = []
#     for category in categories:
#         c_images[category] = models.Image.objects.filter(category=category).values('image').distinct()[:1]
#         images += models.Image.objects.filter(category=category)
#
#     if request.method == 'POST':
#         name = request.POST.get('name')
#         straps_num = request.POST.get('straps')
#         color = request.POST.get('color')
#         # print("122COLOR ", color)
#         new_tab = models.Tab.objects.get_or_create(name=name, board=board, color=color, straps_num=straps_num)
#     tabs = models.Tab.objects.filter(board=id).order_by('id')
#     print(images)
#     t_i = []
#     for tab in tabs:
#         tabs_img = list(models.Image_positions.objects.filter(tab=tab.id).distinct())
#         t_i.append(tabs_img)
#
#     # if request.method == 'GET':
#     #     text = request.GET.get("input_data")
#     #     print("BOARD TEXT", text)
#
#     dict = {'tabs': tabs,
#             'is_cr': is_recipient(request.user),
#             'is_cg': is_caregiver(request.user),
#             'tabs_img': tabs_img,
#             't_imgs': t_i,
#             'current_path': request.path,
#             'categories': categories,
#             'c_images': c_images,
#             'images': images,
#             'board_id': id,
#             }
#     return render(request, 'board.html', dict)


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


# def board_category_view(request):
#     if request.method == 'GET':
#         id = request.GET.get("input_data")
#         category = models.Category.objects.get(id=id)
#         category_imgs = models.Image.objects.filter(category_id=id)
#
#         dict = {'category': category,
#                 'category_imgs': category_imgs, }
#     return render(request, 'board_category.html', dict)


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


# def recipient_profile_caregiver_view(request):
#     # code = generate_code(request)
#     recipient = models.Care_recipient.objects.get(user=request.user.id)
#     try:
#         caregivers = models.Care_giver.objects.filter(recipients=recipient)
#     except models.Care_giver.DoesNotExist:
#         caregivers = None
#     dict = {'caregivers': caregivers}
#     return render(request, 'recipient_profile_caregiver.html', dict)

# def recipient_profile_caregiver_view(request):
#     # code = generate_code(request)
#     recipient = models.Care_recipient.objects.get(user=request.user.id)
#     try:
#         caregivers = models.Care_giver.objects.filter(recipients=recipient)
#     except models.Care_giver.DoesNotExist:
#         caregivers = None
#     dict = {'caregivers': caregivers}
#     return render(request, 'recipient_profile_caregiver.html', dict)

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

        return Response({data}, status=status.HTTP_200_OK)


# def profile_view(request):
#     if is_recipient(request.user):
#         return redirect('recipient_profile')
#     elif is_caregiver(request.user):
#         return redirect('caregiver_profile')

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


# def caregiver_recipient_view(request):
#     # code = generate_code(request)
#     try:
#         caregiver = models.Care_giver.objects.get(user=request.user.id)
#         recipients = caregiver.recipients
#     except models.Care_giver.DoesNotExist:
#         recipients = None
#     dict = {
#         'recipients': recipients}
#     return render(request, 'caregiver_recipients.html', dict)


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

        # Generate word counts for each hour of the day
        for hour in range(0, 24):
            word_count = sum(
                len(d['text'].split()) for d in bar_data if d['time'].hour == hour
            )
            bar.append(word_count)

        # Return the word counts data in a JSON response
        return Response({'bar': bar}, status=200)


# def bar_chars(request):
#     if request.method == 'GET':
#         received_data = request.GET.get('bar_date')
#         bar_data = models.History.objects.filter(date=received_data, user=request.user).values('text', 'time')
#         print(received_data)
#
#         bar = []
#         for i in range(0, 24):
#             n = 0
#             if len(bar_data) != 0:
#                 for d in bar_data:
#                     if d['time'].hour == i:
#                         text = d['text'].split()
#                         n += len(text)
#             bar.append(n)
#     return render(request, 'progress_tracking.html', {'bar': bar})


class ProgressView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this view

    def get(self, request):
        # Get categories, histories, and boards for the current user
        categories = Category.objects.values('id', 'name')
        histories = list(History.objects.filter(user=request.user.id).values('text', 'date', 'time'))[::-1]
        boards = Board.objects.filter(creator=request.user)

        # Calculate representation of each board in user's history
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
                rep.append(count / len(boards_h) * 100)  # Calculate percentage representation
            else:
                rep.append(0)  # Avoid division by zero if there are no history entries

        # Prepare response data
        data = {
            'histories': histories,
            'is_recipient': is_recipient(request.user),
            'board_names': b,
            'board_representation': rep,
        }

        return Response(data, status=200)


# def progress(request):
#     categories = models.Category.objects.values('id', 'name')
#     histories = list(models.History.objects.filter(user=request.user.id).values('text', 'date', 'time'))[::-1]
#     boards = models.Board.objects.filter(creator=request.user)
#     print("B", boards)
#     boards_h = models.History.objects.filter(user=request.user).values('board', 'text')
#     print("BH", boards_h)
#     b = []
#     rep = []
#     for board in boards:
#         count = 0
#         b.append(board.name)
#         for bh in boards_h:
#             if board.id == bh['board']:
#                 count += 1
#         rep.append(count / len(boards_h) * 100)
#     print("rep", b)
#     # num_img = []
#     # used_img = []
#     # tab_idx = set()
#     # tab_dic = {}
#     # tabs = models.Tab.objects.values('images')
#     # val = []
#     # name = []
#     # for t in tabs:
#     #     tab_idx.add(t['images'])
#     # for j in tab_idx:
#     #     cat = models.Image.objects.filter(id=j).values('category')
#     #     tab_dic[j] = cat[0]['category']
#     # for i in categories:
#     #     image_num = len(models.Image.objects.filter(category = i['id']))
#     #     name.append(i['name'])
#     #     num_img.append(image_num)
#     #     used_img.append(len(list(filter(lambda k: float(tab_dic[k]) == i['id'], tab_dic))))
#     # for i in range (0, len(used_img)):
#     #     if num_img[i] != 0:
#     #         val.append((used_img[i], num_img[i], name[i], int(round(used_img[i]/num_img[i]*100, 0))))
#     #     else:
#     #         val.append((used_img[i], num_img[i], name[i], 0))
#     dict = {
#         # 'val': val,
#         # 'name': name,
#         'histories': histories,
#         'is_cr': is_recipient(request.user),
#         'rep': rep,
#         'boards': (b),
#     }
#     return render(request, 'progress_tracking.html', dict)


def is_recipient(user):
    return user.groups.filter(name='RECIPIENT').exists()


def is_caregiver(user):
    return user.groups.filter(name='CAREGIVER').exists()
